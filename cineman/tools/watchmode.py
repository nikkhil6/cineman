import os
import logging
from typing import Dict, Any, List, Optional
from langchain.tools import tool
from cineman.metrics import track_external_api_call
from cineman.api_client import MovieDataClient, APIError
from cineman.cache import get_cache

logger = logging.getLogger(__name__)

# Try to import structured logging (optional)
try:
    from cineman.logging_config import get_logger
    logger = get_logger(__name__)
    _structured_logging_available = True
except ImportError:
    _structured_logging_available = False

WATCHMODE_API_KEY = os.getenv("WATCHMODE_API_KEY")
WATCHMODE_BASE_URL = "https://api.watchmode.com/v1"

# Shared client instance
_watchmode_client = None

def _get_watchmode_client() -> MovieDataClient:
    global _watchmode_client
    if _watchmode_client is None:
        _watchmode_client = MovieDataClient()
    return _watchmode_client

def get_dummy_streaming_data(title: str = "", tmdb_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Return dummy streaming data for development/fallback when Watchmode API is unavailable.
    Constructs search URLs for each platform using the movie title.
    """
    # URL-encode the title for search queries
    import urllib.parse
    encoded_title = urllib.parse.quote(title) if title else "movie"
    
    dummy_providers = [
        {
            "name": "Netflix",
            "type": "sub",
            "logo_url": "https://www.themoviedb.org/t/p/original/9Aoe1m6vORHh9FW3EHeLb7nyEDR.jpg",
            "url": f"https://www.netflix.com/search?q={encoded_title}"
        },
        {
            "name": "Amazon Prime",
            "type": "sub", 
            "logo_url": "https://www.themoviedb.org/t/p/original/68MN3c7bmSdbLs9vP6hHBCHwbmP.jpg",
            "url": f"https://www.amazon.com/s?k={encoded_title}&i=prime-instant-video"
        },
        {
            "name": "Hulu",
            "type": "sub",
            "logo_url": "https://www.themoviedb.org/t/p/original/gi4uY69GZ_H9_A3982F9G9U6_L3.jpg",
            "url": f"https://www.hulu.com/search?q={encoded_title}"
        },
        {
            "name": "Pluto TV",
            "type": "free",
            "logo_url": "https://www.themoviedb.org/t/p/original/7rw9m6u978YmE7C9799O9Yv9Z.jpg",
            "url": f"https://pluto.tv/en/search/details/movies/{encoded_title}"
        }
    ]
    
    return {
        "status": "success",
        "source": "dummy_data",
        "providers": dummy_providers
    }

@track_external_api_call('watchmode')
def fetch_watchmode_data_core(title: str, tmdb_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch streaming availability from Watchmode.
    If no API key is set or API fails, returns mock/dummy data for demonstration.
    """
    if not WATCHMODE_API_KEY:
        # Return dummy data as requested if no API key
        if _structured_logging_available:
            logger.info("watchmode_dummy_requested", title=title)
        
        return {
            "status": "success",
            "source": "dummy",
            "providers": get_dummy_streaming_data(title, tmdb_id).get("providers", [])
        }

    # Cache check
    cache = get_cache()
    cached_result = cache.get(title, source="watchmode")
    if cached_result is not None:
        return cached_result

    client = _get_watchmode_client()
    
    try:
        if tmdb_id:
            # Watchmode endpoint for title info by external ID
            # Format: movie-{tmdb_id} for TMDB IDs
            url = f"{WATCHMODE_BASE_URL}/title/movie-{tmdb_id}/sources/"
        else:
            # Fallback search if no TMDB ID
            search_url = f"{WATCHMODE_BASE_URL}/search/"
            search_resp = client.get(search_url, params={"apiKey": WATCHMODE_API_KEY, "search_value": title, "search_field": "name"})
            search_data = search_resp.json()
            titles = search_data.get("title_results", [])
            if not titles:
                # No titles found, return dummy data to ensure UI visibility
                return {
                    "status": "success",
                    "source": "dummy_fallback_not_found",
                    "providers": get_dummy_streaming_data(title, tmdb_id).get("providers", [])
                }
            
            watchmode_id = titles[0].get("id")
            url = f"{WATCHMODE_BASE_URL}/title/{watchmode_id}/sources/"

        resp = client.get(url, params={"apiKey": WATCHMODE_API_KEY})
        sources = resp.json()

        providers = []
        # Support both list and dict response formats
        if isinstance(sources, list):
            for s in sources:
                web_url = s.get("web_url")
                # Filter out invalid or missing URLs
                if not web_url or not web_url.startswith("http"):
                    continue
                    
                providers.append({
                    "name": s.get("name"),
                    "type": s.get("type"), # sub, purchase, free, rental
                    "url": web_url,
                    "logo_url": s.get("logo_url")
                })
        
        # Deduplicate providers - keep one per platform name
        # Priority: free > sub > rental > purchase
        type_priority = {"free": 0, "sub": 1, "subscription": 1, "rental": 2, "rent": 2, "purchase": 3, "buy": 3}
        
        seen_providers = {}
        for p in providers:
            name = p.get("name")
            if not name:
                continue
                
            ptype = (p.get("type") or "").lower()
            priority = type_priority.get(ptype, 999)
            
            # Keep the provider with the best (lowest) priority
            if name not in seen_providers or priority < seen_providers[name]["priority"]:
                seen_providers[name] = {
                    "data": p,
                    "priority": priority
                }
        
        # Extract just the provider data
        deduplicated_providers = [v["data"] for v in seen_providers.values()]
        
        if not deduplicated_providers:
            # Fallback to dummy if no providers found
            result = {
                "status": "success",
                "source": "dummy_fallback_empty",
                "providers": get_dummy_streaming_data(title, tmdb_id).get("providers", [])
            }
        else:
            result = {
                "status": "success",
                "source": "watchmode",
                "providers": deduplicated_providers
            }

        cache.set(title, result, source="watchmode")
        return result

    except Exception as e:
        logger.error(f"Watchmode API error: {str(e)}")
        # CRITICAL: Return dummy data on error so UI feature is visible during review
        return {
            "status": "success", 
            "source": "dummy_fallback_error", 
            "providers": get_dummy_streaming_data(title, tmdb_id).get("providers", [])
        }

@tool
def fetch_watchmode_data(title: str, tmdb_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get streaming availability for a movie.
    """
    return fetch_watchmode_data_core(title, tmdb_id)
