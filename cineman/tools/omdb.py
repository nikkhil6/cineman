import os
import time
import logging
from typing import Dict, Any, Optional
from langchain.tools import tool
from cineman.api_client import MovieDataClient, AuthError, NotFoundError, TransientError, QuotaError, APIError

logger = logging.getLogger(__name__)

# Configuration via env
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
BASE_URL = "https://www.omdbapi.com/"
OMDB_ENABLED = os.getenv("OMDB_ENABLED", "1") != "0"    # set OMDB_ENABLED=0 to disable OMDb calls

# Simple in-memory TTL cache (process-lifetime). Optional: replace with redis/filecache later.
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = int(os.getenv("OMDB_CACHE_TTL", "300"))  # seconds

# Shared client instance for connection pooling
_omdb_client = None


def _get_omdb_client() -> MovieDataClient:
    """Get or create the shared OMDb client instance."""
    global _omdb_client
    if _omdb_client is None:
        _omdb_client = MovieDataClient()
    return _omdb_client


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


def _clear_cache(key: Optional[str] = None) -> None:
    """
    Clear cache entries. Used primarily for testing.
    
    Args:
        key: Specific cache key to clear, or None to clear all cache
    """
    if key is None:
        _CACHE.clear()
    elif key in _CACHE:
        del _CACHE[key]


def fetch_omdb_data_core(title: str) -> Dict[str, Any]:
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

    cache_key = f"omdb:{title.lower()}"
    cached = _get_from_cache(cache_key)
    if cached:
        # mark as coming from cache for clarity
        cached_copy = dict(cached)
        cached_copy["_cached"] = True
        return cached_copy

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
            _set_cache(cache_key, result)
            return result
        else:
            result = {
                "status": "not_found",
                "error": data.get("Error"),
                "raw": data,
                "attempts": attempts,
                "elapsed": elapsed,
            }
            _set_cache(cache_key, result)
            return result

    except AuthError as e:
        elapsed = time.time() - start
        logger.error(f"OMDb authentication error: {e.message}")
        result = {
            "status": "forbidden",
            "error": e.message,
            "error_type": "auth",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        _set_cache(cache_key, result)
        return result
    except QuotaError as e:
        elapsed = time.time() - start
        logger.warning(f"OMDb quota exceeded: {e.message}")
        result = {
            "status": "quota_error",
            "error": e.message,
            "error_type": "quota",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        _set_cache(cache_key, result)
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
        _set_cache(cache_key, result)
        return result
    except TransientError as e:
        elapsed = time.time() - start
        logger.error(f"OMDb transient error after retries: {e.message}")
        result = {
            "status": "error",
            "error": e.message,
            "error_type": "transient",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        _set_cache(cache_key, result)
        return result
    except APIError as e:
        elapsed = time.time() - start
        logger.error(f"OMDb API error: {e.message}")
        result = {
            "status": "error",
            "error": e.message,
            "error_type": e.error_type.value,
            "attempts": attempts,
            "elapsed": elapsed,
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"OMDb unexpected error: {str(e)}")
        result = {
            "status": "error",
            "error": str(e),
            "error_type": "unknown",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        _set_cache(cache_key, result)
        return result


@tool
def get_movie_facts(title: str) -> Dict[str, Any]:
    """
    LangChain tool: fetch OMDb facts (IMDb rating, director, poster).
    Returns same dict as fetch_omdb_data_core.
    """
    return fetch_omdb_data_core(title)