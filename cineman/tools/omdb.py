import os
import time
import logging
from typing import Dict, Any, Optional
from langchain.tools import tool
from cineman.metrics import track_external_api_call, track_cache_operation
from cineman.api_client import MovieDataClient, AuthError, NotFoundError, TransientError, QuotaError, APIError
from cineman.cache import get_cache

# Use standard logger - structured logging is handled via get_logger() if available
logger = logging.getLogger(__name__)

# Try to import structured logging (optional)
try:
    from cineman.logging_config import get_logger
    logger = get_logger(__name__)
    _structured_logging_available = True
except ImportError:
    _structured_logging_available = False

# Configuration via env
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
BASE_URL = "https://www.omdbapi.com/"
OMDB_ENABLED = os.getenv("OMDB_ENABLED", "1") != "0"    # set OMDB_ENABLED=0 to disable OMDb calls
OMDB_TIMEOUT = float(os.getenv("OMDB_TIMEOUT", "8"))   # seconds
OMDB_RETRIES = int(os.getenv("OMDB_RETRIES", "2"))     # retry count (on idempotent errors)
OMDB_BACKOFF = float(os.getenv("OMDB_BACKOFF", "0.8")) # backoff factor for urllib3 Retry

# Simple in-memory TTL cache (process-lifetime). Optional: replace with redis/filecache later.
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = int(os.getenv("OMDB_CACHE_TTL", "300"))  # seconds


def _make_session(retries: int = OMDB_RETRIES, backoff: float = OMDB_BACKOFF) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get_from_cache(key: str) -> Optional[Dict[str, Any]]:
    entry = _CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry.get("_ts", 0) > _CACHE_TTL:
        try:
            del _CACHE[key]
        except KeyError:
            pass
        return None
    return entry.get("value")


def _set_cache(key: str, value: Dict[str, Any]) -> None:
    _CACHE[key] = {"_ts": time.time(), "value": value}


@track_external_api_call('omdb')
def fetch_omdb_data_core(title: str) -> Dict[str, Any]:

# Shared client instance for connection pooling
_omdb_client = None


def _get_omdb_client() -> MovieDataClient:
    """Get or create the shared OMDb client instance."""
    global _omdb_client
    if _omdb_client is None:
        _omdb_client = MovieDataClient()
    return _omdb_client


def _clear_cache(key: Optional[str] = None) -> None:
    """
    Clear cache entries. Used primarily for testing.
    Provided for backward compatibility with existing tests.
    
    Args:
        key: Specific cache key to clear, or None to clear all cache
    """
    cache = get_cache()
    if key is None:
        cache.clear(source="omdb")
    else:
        # Extract title from old-style key format "omdb:title"
        # The original implementation used lowercase titles, so we maintain that
        if key.startswith("omdb:"):
            title = key[5:]  # Remove "omdb:" prefix (already lowercase)
            cache.evict(title, source="omdb")


def fetch_omdb_data_core(title: str, year: str = None) -> Dict[str, Any]:
    """
    Fetch OMDb data for `title` and return a structured dict.
    Possible status values:
      - success
      - not_found
      - forbidden (auth_error)
      - disabled (OMDb disabled via env)
      - error
      - quota_error

    Returned dict includes 'raw' (OMDb JSON) when available, and 'attempts' / 'elapsed' for diagnostics.
    """
    title = (title or "").strip()
    if not title:
        return {"status": "error", "error": "Missing title parameter."}

    if not OMDB_ENABLED:
        return {"status": "disabled", "error": "OMDb calls disabled via OMDB_ENABLED=0"}

    if not OMDB_API_KEY:
        return {
            "status": "error",
            "error": "OMDb API Key not configured.",
            "error_type": "auth"
        }

    # Check cache first
    cache = get_cache()
    cached = cache.get(title, year=year, source="omdb")
    if cached:
        # mark as coming from cache for clarity
        cached_copy = dict(cached)
        cached_copy["_cached"] = True
        track_cache_operation('omdb', hit=True)
        if _structured_logging_available:
            logger.info("omdb_cache_hit", title=title, year=year)
        else:
            logger.debug(f"OMDb cache hit for '{title}'")
        return cached_copy
    
    # Cache miss
    track_cache_operation('omdb', hit=False)

    params = {"apikey": OMDB_API_KEY, "t": title, "plot": "short", "r": "json"}
    client = _get_omdb_client()

    start = time.time()
    # Note: MovieDataClient tracks attempts internally, but we maintain backward 
    # compatibility by reporting attempts in the response. On success, we report 1.
    # On error, attempts is set in the exception handlers.
    attempts = 1
    try:
        response = client.get(
            BASE_URL,
            params=params,
            api_name="OMDb"
        )
        elapsed = time.time() - start

        # Parse JSON
        data = response.json()
        if data.get("Response") == "True":
            # Extract Rotten Tomatoes ratings from Ratings array
            rt_tomatometer = None
            ratings_array = data.get("Ratings", [])
            for rating in ratings_array:
                source = rating.get("Source", "")
                value = rating.get("Value", "")
                if "Rotten Tomatoes" in source:
                    rt_tomatometer = value
                    break
            
            result = {
                "status": "success",
                "Title": data.get("Title"),
                "Year": data.get("Year"),
                "Director": data.get("Director"),
                "IMDb_Rating": data.get("imdbRating"),
                "Rotten_Tomatoes": rt_tomatometer,
                "Poster_URL": data.get("Poster"),
                "raw": data,
                "attempts": attempts,
                "elapsed": elapsed,
            }
            # Cache successful result
            cache.set(title, result, year=year, source="omdb")
            if _structured_logging_available:
                logger.info("omdb_movie_found", title=data.get("Title"), year=data.get("Year"))
            else:
                logger.debug(f"OMDb result cached for '{title}'")
            return result
        else:
            result = {
                "status": "not_found",
                "error": data.get("Error"),
                "raw": data,
                "attempts": attempts,
                "elapsed": elapsed,
            }
            # Cache not_found with medium TTL (1 hour)
            cache.set(title, result, year=year, source="omdb", ttl=3600)
            return result

    except AuthError as e:
        elapsed = time.time() - start
        if _structured_logging_available:
            logger.error("omdb_auth_error", title=title, error=e.message)
        else:
            logger.error(f"OMDb authentication error: {e.message}")
        result = {
            "status": "forbidden",
            "error": e.message,
            "error_type": "auth",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        # Cache auth errors with shorter TTL (5 minutes)
        cache.set(title, result, year=year, source="omdb", ttl=300)
        return result
    except QuotaError as e:
        elapsed = time.time() - start
        if _structured_logging_available:
            logger.warning("omdb_quota_exceeded", title=title, error=e.message)
        else:
            logger.warning(f"OMDb quota exceeded: {e.message}")
        result = {
            "status": "quota_error",
            "error": e.message,
            "error_type": "quota",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        # Cache quota errors with shorter TTL (5 minutes)
        cache.set(title, result, year=year, source="omdb", ttl=300)
        return result
    except NotFoundError as e:
        elapsed = time.time() - start
        # This shouldn't happen at the HTTP level for OMDb, but handle it anyway
        result = {
            "status": "not_found",
            "error": e.message,
            "attempts": attempts,
            "elapsed": elapsed,
        }
        # Cache not_found with medium TTL (1 hour)
        cache.set(title, result, year=year, source="omdb", ttl=3600)
        return result
    except TransientError as e:
        elapsed = time.time() - start
        if _structured_logging_available:
            logger.error("omdb_transient_error", title=title, error=e.message)
        else:
            logger.error(f"OMDb transient error after retries: {e.message}")
        result = {
            "status": "error",
            "error": e.message,
            "error_type": "transient",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        # Don't cache transient errors (may be temporary)
        return result
    except APIError as e:
        elapsed = time.time() - start
        if _structured_logging_available:
            logger.error("omdb_api_error", title=title, error=e.message, error_type=e.error_type.value)
        else:
            logger.error(f"OMDb API error: {e.message}")
        result = {
            "status": "error",
            "error": e.message,
            "error_type": e.error_type.value,
            "attempts": attempts,
            "elapsed": elapsed,
        }
        # Cache API errors with shorter TTL (5 minutes)
        cache.set(title, result, year=year, source="omdb", ttl=300)
        return result
    except Exception as e:
        elapsed = time.time() - start
        if _structured_logging_available:
            logger.error("omdb_unexpected_error", title=title, error=str(e))
        else:
            logger.error(f"OMDb unexpected error: {str(e)}")
        result = {
            "status": "error",
            "error": str(e),
            "error_type": "unknown",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        # Don't cache unknown errors
        return result


@tool
def get_movie_facts(title: str, year: str = None) -> Dict[str, Any]:
    """
    LangChain tool: fetch OMDb facts (IMDb rating, director, poster).
    Returns same dict as fetch_omdb_data_core.
    
    Args:
        title (str): Movie title to search for (e.g., "Inception").
        year (str): Optional release year for better matching (e.g., "2010").
    """
    return fetch_omdb_data_core(title, year)