import os
import time
import logging
from typing import Dict, Any, Optional
from langchain.tools import tool
from cineman.api_client import MovieDataClient, AuthError, NotFoundError, TransientError, QuotaError, APIError
from cineman.cache import get_cache

logger = logging.getLogger(__name__)

# Configuration via env
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
BASE_URL = "https://www.omdbapi.com/"
OMDB_ENABLED = os.getenv("OMDB_ENABLED", "1") != "0"    # set OMDB_ENABLED=0 to disable OMDb calls

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
        logger.debug(f"OMDb cache hit for '{title}'")
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
            # Cache successful result
            cache.set(title, result, year=year, source="omdb")
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