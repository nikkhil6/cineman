import os
import logging
from typing import Dict, Any
from langchain.tools import tool
from cineman.api_client import MovieDataClient, AuthError, NotFoundError, TransientError, QuotaError, APIError

logger = logging.getLogger(__name__)

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


def get_movie_poster_core(title: str) -> Dict[str, Any]:
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

    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}

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
        year = (first_result.get("release_date") or "")[:4]
        vote_average = first_result.get("vote_average")
        vote_count = first_result.get("vote_count")

        poster_url = f"{IMAGE_BASE_URL}{poster_path}" if poster_path else ""

        return {
            "status": "success",
            "poster_url": poster_url,
            "year": year,
            "title": matched_title,
            "tmdb_id": tmdb_id,
            "vote_average": vote_average,
            "vote_count": vote_count,
        }
    except AuthError as e:
        logger.error(f"TMDB authentication error: {e.message}")
        return {
            "status": "auth_error",
            "error": e.message,
            "error_type": "auth"
        }
    except QuotaError as e:
        logger.warning(f"TMDB quota exceeded: {e.message}")
        return {
            "status": "quota_error",
            "error": e.message,
            "error_type": "quota"
        }
    except NotFoundError as e:
        # This shouldn't happen at the HTTP level for search endpoint,
        # but handle it anyway
        return {"status": "not_found", "poster_url": "", "title": title}
    except TransientError as e:
        logger.error(f"TMDB transient error after retries: {e.message}")
        return {
            "status": "error",
            "error": e.message,
            "error_type": "transient"
        }
    except APIError as e:
        logger.error(f"TMDB API error: {e.message}")
        return {
            "status": "error",
            "error": e.message,
            "error_type": e.error_type.value
        }
    except Exception as e:
        logger.error(f"TMDB unexpected error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": "unknown"
        }


@tool
def get_movie_poster(title: str) -> Dict[str, Any]:
    """
    LangChain tool: Get a movie poster and basic TMDb metadata.

    Args:
      title (str): Movie title to search for (e.g., "Inception").

    Returns:
      dict: Same structure as get_movie_poster_core result.
    """
    return get_movie_poster_core(title)