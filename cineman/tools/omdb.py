import os
import time
import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from langchain.tools import tool

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


def fetch_omdb_data_core(title: str) -> Dict[str, Any]:
    """
    Fetch OMDb data for `title` and return a structured dict.
    Possible status values:
      - success
      - not_found
      - forbidden
      - disabled (OMDb disabled via env)
      - error

    Returned dict includes 'raw' (OMDb JSON) when available, and 'attempts' / 'elapsed' for diagnostics.
    """
    title = (title or "").strip()
    if not title:
        return {"status": "error", "error": "Missing title parameter."}

    if not OMDB_ENABLED:
        return {"status": "disabled", "error": "OMDb calls disabled via OMDB_ENABLED=0"}

    if not OMDB_API_KEY:
        return {"status": "error", "error": "OMDb API Key not configured."}

    cache_key = f"omdb:{title.lower()}"
    cached = _get_from_cache(cache_key)
    if cached:
        # mark as coming from cache for clarity
        cached_copy = dict(cached)
        cached_copy["_cached"] = True
        return cached_copy

    params = {"apikey": OMDB_API_KEY, "t": title, "plot": "short", "r": "json"}
    session = _make_session()

    start = time.time()
    attempts = 0
    try:
        attempts += 1
        resp = session.get(BASE_URL, params=params, timeout=OMDB_TIMEOUT)
        elapsed = time.time() - start

        # If OMDb returns 403 or other statuses, we handle them explicitly
        if resp.status_code == 403:
            result = {
                "status": "forbidden",
                "error": f"403 Forbidden from OMDb: {resp.text[:200]}",
                "attempts": attempts,
                "elapsed": elapsed,
            }
            _set_cache(cache_key, result)
            return result

        # If a 4xx/5xx occurred, include status in error
        if resp.status_code >= 400:
            result = {
                "status": "error",
                "error": f"HTTP {resp.status_code} from OMDb: {resp.text[:200]}",
                "attempts": attempts,
                "elapsed": elapsed,
            }
            _set_cache(cache_key, result)
            return result

        # Parse JSON
        data = resp.json()
        if data.get("Response") == "True":
            # Extract Rotten Tomatoes ratings from Ratings array
            rt_tomatometer = None
            rt_audience = None
            ratings_array = data.get("Ratings", [])
            for rating in ratings_array:
                source = rating.get("Source", "")
                value = rating.get("Value", "")
                if "Rotten Tomatoes" in source:
                    rt_tomatometer = value
                # OMDb doesn't typically provide audience score separately,
                # but we keep the field for potential future use
            
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

    except requests.exceptions.RequestException as re:
        elapsed = time.time() - start
        # Connection reset / connection abort typically raises a RequestException subclass
        err_text = str(re)
        result = {
            "status": "error",
            "error": f"Request error: {err_text}",
            "attempts": attempts,
            "elapsed": elapsed,
        }
        # cache errors to avoid hammering OMDb repeatedly for transient state
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        elapsed = time.time() - start
        result = {"status": "error", "error": str(e), "attempts": attempts, "elapsed": elapsed}
        _set_cache(cache_key, result)
        return result


@tool
def get_movie_facts(title: str) -> Dict[str, Any]:
    """
    LangChain tool: fetch OMDb facts (IMDb rating, director, poster).
    Returns same dict as fetch_omdb_data_core.
    """
    return fetch_omdb_data_core(title)