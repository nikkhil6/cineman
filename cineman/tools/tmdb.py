import os
import logging
from typing import Dict, Any
from langchain.tools import tool
from cineman.metrics import track_external_api_call
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

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Shared client instance for connection pooling
_tmdb_client = None


def _get_tmdb_client() -> MovieDataClient:
    """Get or create the shared TMDB client instance."""
    global _tmdb_client
    if _tmdb_client is None:
        _tmdb_client = MovieDataClient()
    return _tmdb_client

@track_external_api_call('tmdb')
def get_movie_poster_core(title: str, year: str = None) -> Dict[str, Any]:
    """
    Core TMDb lookup. Searches TMDb for `title` and returns a dict with keys:
      - status: "success" | "not_found" | "error" | "auth_error" | "quota_error"
      - poster_url: full URL or empty string
      - year: release year (YYYY) or empty
      - title: matched title from TMDb
      - tmdb_id: TMDb movie id
      - vote_average: TMDb vote_average (float) when available
      - vote_count: TMDb vote_count (int) when available
      - error: error message (when status is not "success")
      - error_type: classified error type (when status is not "success")

    This function is intended to be called programmatically by server routes.
    """
    if not TMDB_API_KEY:
        return {
            "status": "error",
            "error": "TMDb API Key not configured.",
            "error_type": "auth"
        }

    # Check cache first
    cache = get_cache()
    cached_result = cache.get(title, year=year, source="tmdb")
    if cached_result is not None:
        if _structured_logging_available:
            logger.info("tmdb_cache_hit", title=title, year=year)
        else:
            logger.debug(f"TMDB cache hit for '{title}'")
        return cached_result

    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}
    if year:
        params["primary_release_year"] = year

    client = _get_tmdb_client()

    try:
        response = client.get(
            search_url,
            params=params,
            api_name="TMDB"
        )
        search_response = response.json()

        results = search_response.get("results") or []
        if len(results) == 0:
            return {"status": "not_found", "poster_url": "", "title": title}

        first_result = results[0]
        poster_path = first_result.get("poster_path")
        tmdb_id = first_result.get("id")
        matched_title = first_result.get("title")
        result_year = (first_result.get("release_date") or "")[:4]
        vote_average = first_result.get("vote_average")
        vote_count = first_result.get("vote_count")

        poster_url = f"{IMAGE_BASE_URL}{poster_path}" if poster_path else ""

        result = {
            "status": "success",
            "poster_url": poster_url,
            "year": result_year,
            "title": matched_title,
            "tmdb_id": tmdb_id,
            "vote_average": vote_average,
            "vote_count": vote_count,
        }
        
        # Cache successful result
        # Note: We use the input year (if provided) for cache key consistency.
        # This ensures lookups with the same year always hit the same cache entry.
        cache.set(title, result, year=year, source="tmdb")
        
        if _structured_logging_available:
            logger.info("tmdb_movie_found", title=matched_title, year=result_year, tmdb_id=tmdb_id)
        else:
            logger.debug(f"TMDB result cached for '{title}'")
        
        return result
    except AuthError as e:
        if _structured_logging_available:
            logger.error("tmdb_auth_error", title=title, error=e.message)
        else:
            logger.error(f"TMDB authentication error: {e.message}")
        result = {
            "status": "auth_error",
            "error": e.message,
            "error_type": "auth"
        }
        # Cache auth errors with shorter TTL (5 minutes)
        cache.set(title, result, year=year, source="tmdb", ttl=300)
        return result
    except QuotaError as e:
        if _structured_logging_available:
            logger.warning("tmdb_quota_exceeded", title=title, error=e.message)
        else:
            logger.warning(f"TMDB quota exceeded: {e.message}")
        result = {
            "status": "quota_error",
            "error": e.message,
            "error_type": "quota"
        }
        # Cache quota errors with shorter TTL (5 minutes)
        cache.set(title, result, year=year, source="tmdb", ttl=300)
        return result
    except NotFoundError as e:
        # This shouldn't happen at the HTTP level for search endpoint,
        # but handle it anyway
        result = {"status": "not_found", "poster_url": "", "title": title}
        # Cache not_found with medium TTL (1 hour)
        cache.set(title, result, year=year, source="tmdb", ttl=3600)
        return result
    except TransientError as e:
        if _structured_logging_available:
            logger.error("tmdb_transient_error", title=title, error=e.message)
        else:
            logger.error(f"TMDB transient error after retries: {e.message}")
        result = {
            "status": "error",
            "error": e.message,
            "error_type": "transient"
        }
        # Don't cache transient errors (may be temporary)
        return result
    except APIError as e:
        if _structured_logging_available:
            logger.error("tmdb_api_error", title=title, error=e.message, error_type=e.error_type.value)
        else:
            logger.error(f"TMDB API error: {e.message}")
        result = {
            "status": "error",
            "error": e.message,
            "error_type": e.error_type.value
        }
        # Cache API errors with shorter TTL (5 minutes)
        cache.set(title, result, year=year, source="tmdb", ttl=300)
        return result
    except Exception as e:
        if _structured_logging_available:
            logger.error("tmdb_unexpected_error", title=title, error=str(e))
        else:
            logger.error(f"TMDB unexpected error: {str(e)}")
        result = {
            "status": "error",
            "error": str(e),
            "error_type": "unknown"
        }
        # Don't cache unknown errors
        return result


@tool
def get_movie_poster(title: str, year: str = None) -> Dict[str, Any]:
    """
    LangChain tool: Get a movie poster and basic TMDb metadata.

    Args:
      title (str): Movie title to search for (e.g., "Inception").
      year (str): Optional release year for better matching (e.g., "2010").

    Returns:
      dict: Same structure as get_movie_poster_core result.
    """
    return get_movie_poster_core(title, year)