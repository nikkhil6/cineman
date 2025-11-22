import requests
import os
from typing import Dict, Any
from langchain.tools import tool
from cineman.metrics import track_external_api_call

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


@track_external_api_call('tmdb')
def get_movie_poster_core(title: str) -> Dict[str, Any]:
    """
    Core TMDb lookup. Searches TMDb for `title` and returns a dict with keys:
      - status: "success" | "not_found" | "error"
      - poster_url: full URL or empty string
      - year: release year (YYYY) or empty
      - title: matched title from TMDb
      - tmdb_id: TMDb movie id
      - vote_average: TMDb vote_average (float) when available
      - vote_count: TMDb vote_count (int) when available

    This function is intended to be called programmatically by server routes.
    """
    if not TMDB_API_KEY:
        return {"status": "error", "error": "TMDb API Key not configured."}

    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}

    try:
        r = requests.get(search_url, params=params, timeout=6)
        r.raise_for_status()
        search_response = r.json()

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
    except Exception as e:
        return {"status": "error", "error": str(e)}


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