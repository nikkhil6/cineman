"""
Watchmode API Client for Streaming Availability Data.

This module provides functionality to fetch streaming availability information
for movies using the Watchmode API with TMDB as a fallback source.

Key Features:
- Watchmode API integration for streaming platform data
- TMDB Watch Providers as backup source (free, no additional cost)
- Rate limiting (1000 requests/month for Watchmode)
- Caching to minimize API calls
- Graceful degradation when services are unavailable

Usage:
    >>> from cineman.tools.watchmode import get_streaming_sources
    >>> sources = get_streaming_sources("Inception", tmdb_id=27205)
    >>> print(sources['platforms'])
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cineman.api_client import (
    MovieDataClient, AuthError, NotFoundError, 
    TransientError, QuotaError, APIError
)
from cineman.cache import get_cache
from cineman.metrics import track_external_api_call

# Configure logging
logger = logging.getLogger(__name__)

# Try to import structured logging (optional)
try:
    from cineman.logging_config import get_logger
    logger = get_logger(__name__)
    _structured_logging_available = True
except ImportError:
    _structured_logging_available = False

# Configuration
WATCHMODE_API_KEY = os.getenv("WATCHMODE_API_KEY")
WATCHMODE_BASE_URL = "https://api.watchmode.com/v1"
WATCHMODE_ENABLED = os.getenv("WATCHMODE_ENABLED", "1") != "0"

# Monthly rate limit tracking (1000 requests/month)
WATCHMODE_MONTHLY_LIMIT = int(os.getenv("WATCHMODE_MONTHLY_LIMIT", "1000"))

# TMDB configuration (for fallback)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

# Shared client instances
_watchmode_client: Optional[MovieDataClient] = None
_tmdb_watch_client: Optional[MovieDataClient] = None

# In-memory rate limit tracking (reset monthly)
# For production, consider using a persistent store
_watchmode_usage = {
    "count": 0,
    "reset_date": None
}

# Popular streaming platform icons/logos mapping
STREAMING_PLATFORM_ICONS = {
    # Subscription services
    "netflix": {"name": "Netflix", "icon": "🔴", "color": "#E50914"},
    "amazon_prime": {"name": "Amazon Prime", "icon": "📦", "color": "#00A8E1"},
    "prime": {"name": "Amazon Prime", "icon": "📦", "color": "#00A8E1"},
    "disney_plus": {"name": "Disney+", "icon": "🏰", "color": "#113CCF"},
    "disney+": {"name": "Disney+", "icon": "🏰", "color": "#113CCF"},
    "hulu": {"name": "Hulu", "icon": "🟢", "color": "#1CE783"},
    "hbo_max": {"name": "Max", "icon": "🟣", "color": "#B385FF"},
    "max": {"name": "Max", "icon": "🟣", "color": "#B385FF"},
    "apple_tv_plus": {"name": "Apple TV+", "icon": "🍎", "color": "#000000"},
    "apple_tv": {"name": "Apple TV+", "icon": "🍎", "color": "#000000"},
    "peacock": {"name": "Peacock", "icon": "🦚", "color": "#000000"},
    "paramount_plus": {"name": "Paramount+", "icon": "⛰️", "color": "#0064FF"},
    "paramount+": {"name": "Paramount+", "icon": "⛰️", "color": "#0064FF"},
    "showtime": {"name": "Showtime", "icon": "📺", "color": "#FF0000"},
    "starz": {"name": "Starz", "icon": "⭐", "color": "#000000"},
    "crunchyroll": {"name": "Crunchyroll", "icon": "🍥", "color": "#F47521"},
    "mubi": {"name": "MUBI", "icon": "🎬", "color": "#2B2B2B"},
    "criterion_channel": {"name": "Criterion Channel", "icon": "🎞️", "color": "#000000"},
    # Rental/Purchase
    "youtube": {"name": "YouTube", "icon": "▶️", "color": "#FF0000"},
    "google_play": {"name": "Google Play", "icon": "▶️", "color": "#4285F4"},
    "vudu": {"name": "Vudu", "icon": "🎥", "color": "#3399FF"},
    "itunes": {"name": "iTunes", "icon": "🍎", "color": "#FB5BC5"},
    # Free services
    "tubi": {"name": "Tubi", "icon": "📺", "color": "#FA382F"},
    "pluto_tv": {"name": "Pluto TV", "icon": "📡", "color": "#000000"},
    "kanopy": {"name": "Kanopy", "icon": "📚", "color": "#5B5B5B"},
    "hoopla": {"name": "Hoopla", "icon": "📖", "color": "#EB1C2C"},
}


def _get_watchmode_client() -> MovieDataClient:
    """Get or create the shared Watchmode client instance."""
    global _watchmode_client
    if _watchmode_client is None:
        # Longer timeout for Watchmode as it may be slower
        _watchmode_client = MovieDataClient(timeout=5.0)
    return _watchmode_client


def _get_tmdb_watch_client() -> MovieDataClient:
    """Get or create the shared TMDB watch providers client instance."""
    global _tmdb_watch_client
    if _tmdb_watch_client is None:
        _tmdb_watch_client = MovieDataClient()
    return _tmdb_watch_client


def _check_watchmode_rate_limit() -> bool:
    """
    Check if we're within the Watchmode monthly rate limit.
    
    Returns:
        True if we can make a request, False if limit exceeded.
    """
    global _watchmode_usage
    
    now = datetime.now(tz=None)  # Using naive datetime for simplicity
    
    # Reset counter at the start of each month
    if _watchmode_usage["reset_date"] is None or now >= _watchmode_usage["reset_date"]:
        _watchmode_usage["count"] = 0
        # Set next reset to first day of next month
        next_month = now.replace(day=1) + timedelta(days=32)
        _watchmode_usage["reset_date"] = next_month.replace(day=1, hour=0, minute=0, second=0)
    
    return _watchmode_usage["count"] < WATCHMODE_MONTHLY_LIMIT


def _increment_watchmode_usage() -> None:
    """Increment the Watchmode API usage counter."""
    global _watchmode_usage
    _watchmode_usage["count"] += 1
    if _structured_logging_available:
        logger.info(
            "watchmode_usage_incremented",
            count=_watchmode_usage["count"],
            limit=WATCHMODE_MONTHLY_LIMIT
        )


def _normalize_platform_name(name: str) -> str:
    """
    Normalize platform name for consistent matching.
    
    Args:
        name: Raw platform name from API
        
    Returns:
        Normalized platform name (lowercase, underscores)
    """
    return (
        name.lower()
        .replace(" ", "_")
        .replace("+", "_plus")
        .replace("-", "_")
    )


def _get_platform_info(platform_name: str, logo_url: str = None) -> Dict[str, Any]:
    """
    Get platform display info including icon and color.
    
    Args:
        platform_name: Name of the streaming platform
        logo_url: URL to platform logo (if available)
        
    Returns:
        Dict with platform display info
    """
    normalized = _normalize_platform_name(platform_name)
    
    # Check for known platforms
    for key, info in STREAMING_PLATFORM_ICONS.items():
        if key in normalized or normalized in key:
            return {
                "name": info["name"],
                "icon": info["icon"],
                "color": info["color"],
                "logo_url": logo_url
            }
    
    # Default for unknown platforms
    return {
        "name": platform_name,
        "icon": "📺",
        "color": "#666666",
        "logo_url": logo_url
    }


@track_external_api_call('watchmode')
def _fetch_watchmode_sources(tmdb_id: int, title: str = None) -> Dict[str, Any]:
    """
    Fetch streaming sources from Watchmode API.
    
    Args:
        tmdb_id: TMDB movie ID
        title: Movie title (for logging/error messages)
        
    Returns:
        Dict with streaming source information
    """
    if not WATCHMODE_API_KEY:
        return {
            "status": "error",
            "error": "Watchmode API Key not configured",
            "error_type": "auth"
        }
    
    if not WATCHMODE_ENABLED:
        return {
            "status": "disabled",
            "error": "Watchmode API disabled via WATCHMODE_ENABLED=0"
        }
    
    if not _check_watchmode_rate_limit():
        if _structured_logging_available:
            logger.warning("watchmode_rate_limit_exceeded", title=title, tmdb_id=tmdb_id)
        return {
            "status": "quota_error",
            "error": "Monthly Watchmode API limit reached"
        }
    
    client = _get_watchmode_client()
    
    try:
        # Step 1: Search for the title using TMDB ID
        search_url = f"{WATCHMODE_BASE_URL}/search/"
        search_params = {
            "apiKey": WATCHMODE_API_KEY,
            "search_field": "tmdb_movie_id",
            "search_value": str(tmdb_id)
        }
        
        search_response = client.get(
            search_url,
            params=search_params,
            api_name="Watchmode"
        )
        _increment_watchmode_usage()
        
        search_data = search_response.json()
        
        if not search_data.get("title_results") or len(search_data["title_results"]) == 0:
            return {
                "status": "not_found",
                "error": f"Title not found in Watchmode for TMDB ID {tmdb_id}"
            }
        
        # Get the Watchmode title ID
        watchmode_id = search_data["title_results"][0].get("id")
        if not watchmode_id:
            return {
                "status": "not_found", 
                "error": "No Watchmode ID returned"
            }
        
        # Step 2: Get streaming sources for this title
        sources_url = f"{WATCHMODE_BASE_URL}/title/{watchmode_id}/sources/"
        sources_params = {
            "apiKey": WATCHMODE_API_KEY
        }
        
        sources_response = client.get(
            sources_url,
            params=sources_params,
            api_name="Watchmode"
        )
        _increment_watchmode_usage()
        
        sources_data = sources_response.json()
        
        # Process and categorize sources
        platforms = {
            "subscription": [],  # Netflix, Prime, etc.
            "rent": [],          # Rental options
            "buy": [],           # Purchase options
            "free": [],          # Free with ads
            "all": []            # All platforms combined
        }
        
        seen_platforms = set()
        
        for source in sources_data:
            platform_name = source.get("name", "Unknown")
            source_type = source.get("type", "").lower()
            
            # Skip duplicates
            platform_key = f"{platform_name}_{source_type}"
            if platform_key in seen_platforms:
                continue
            seen_platforms.add(platform_key)
            
            platform_info = _get_platform_info(platform_name)
            
            platform_entry = {
                "name": platform_info["name"],
                "icon": platform_info["icon"],
                "color": platform_info["color"],
                "logo_url": platform_info.get("logo_url"),
                "web_url": source.get("web_url"),
                "type": source_type,
                "price": source.get("price"),
                "format": source.get("format"),
                "region": source.get("region", "US")
            }
            
            # Categorize by type
            if source_type in ("sub", "subscription"):
                platforms["subscription"].append(platform_entry)
            elif source_type == "rent":
                platforms["rent"].append(platform_entry)
            elif source_type == "buy":
                platforms["buy"].append(platform_entry)
            elif source_type in ("free", "ads"):
                platforms["free"].append(platform_entry)
            
            platforms["all"].append(platform_entry)
        
        return {
            "status": "success",
            "source": "watchmode",
            "platforms": platforms,
            "watchmode_id": watchmode_id,
            "attribution": "Data provided by Watchmode"
        }
        
    except AuthError as e:
        if _structured_logging_available:
            logger.error("watchmode_auth_error", title=title, error=e.message)
        return {"status": "auth_error", "error": e.message}
    except QuotaError as e:
        if _structured_logging_available:
            logger.warning("watchmode_quota_exceeded", title=title, error=e.message)
        return {"status": "quota_error", "error": e.message}
    except NotFoundError as e:
        return {"status": "not_found", "error": e.message}
    except TransientError as e:
        if _structured_logging_available:
            logger.error("watchmode_transient_error", title=title, error=e.message)
        return {"status": "error", "error": e.message, "error_type": "transient"}
    except APIError as e:
        if _structured_logging_available:
            logger.error("watchmode_api_error", title=title, error=e.message)
        return {"status": "error", "error": e.message}
    except Exception as e:
        if _structured_logging_available:
            logger.error("watchmode_unexpected_error", title=title, error=str(e))
        return {"status": "error", "error": str(e)}


@track_external_api_call('tmdb_watch_providers')
def _fetch_tmdb_watch_providers(tmdb_id: int, title: str = None, region: str = "US") -> Dict[str, Any]:
    """
    Fetch watch providers from TMDB API (free backup source).
    
    Args:
        tmdb_id: TMDB movie ID
        title: Movie title (for logging)
        region: ISO 3166-1 country code (default: US)
        
    Returns:
        Dict with streaming provider information
    """
    if not TMDB_API_KEY:
        return {
            "status": "error",
            "error": "TMDB API Key not configured",
            "error_type": "auth"
        }
    
    client = _get_tmdb_watch_client()
    
    try:
        # TMDB Watch Providers endpoint
        watch_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/watch/providers"
        params = {"api_key": TMDB_API_KEY}
        
        response = client.get(watch_url, params=params, api_name="TMDB Watch Providers")
        data = response.json()
        
        results = data.get("results", {})
        region_data = results.get(region, {})
        
        if not region_data:
            # Try common fallback regions
            for fallback_region in ["US", "GB", "CA", "AU"]:
                if fallback_region in results:
                    region_data = results[fallback_region]
                    region = fallback_region
                    break
        
        if not region_data:
            return {
                "status": "not_found",
                "error": f"No watch providers available for region {region}"
            }
        
        # Process providers
        platforms = {
            "subscription": [],
            "rent": [],
            "buy": [],
            "free": [],
            "all": []
        }
        
        # TMDB provides 'flatrate' (subscription), 'rent', 'buy', 'free', 'ads'
        provider_mappings = {
            "flatrate": "subscription",
            "rent": "rent",
            "buy": "buy",
            "free": "free",
            "ads": "free"
        }
        
        seen_providers = set()
        
        for tmdb_type, our_type in provider_mappings.items():
            for provider in region_data.get(tmdb_type, []):
                provider_name = provider.get("provider_name", "Unknown")
                provider_id = provider.get("provider_id")
                
                # Skip duplicates
                if provider_id in seen_providers:
                    continue
                seen_providers.add(provider_id)
                
                logo_path = provider.get("logo_path")
                logo_url = f"{TMDB_IMAGE_BASE_URL}{logo_path}" if logo_path else None
                
                platform_info = _get_platform_info(provider_name, logo_url)
                
                platform_entry = {
                    "name": platform_info["name"],
                    "icon": platform_info["icon"],
                    "color": platform_info["color"],
                    "logo_url": logo_url,
                    "type": our_type,
                    "region": region,
                    "provider_id": provider_id
                }
                
                platforms[our_type].append(platform_entry)
                platforms["all"].append(platform_entry)
        
        # Get the link to TMDB's watch page (required for attribution)
        tmdb_link = region_data.get("link", f"https://www.themoviedb.org/movie/{tmdb_id}/watch")
        
        return {
            "status": "success",
            "source": "tmdb",
            "platforms": platforms,
            "tmdb_link": tmdb_link,
            "region": region,
            "attribution": "Streaming data provided by JustWatch via TMDB"
        }
        
    except AuthError as e:
        if _structured_logging_available:
            logger.error("tmdb_watch_auth_error", title=title, error=e.message)
        return {"status": "auth_error", "error": e.message}
    except NotFoundError as e:
        return {"status": "not_found", "error": e.message}
    except TransientError as e:
        if _structured_logging_available:
            logger.error("tmdb_watch_transient_error", title=title, error=e.message)
        return {"status": "error", "error": e.message, "error_type": "transient"}
    except APIError as e:
        if _structured_logging_available:
            logger.error("tmdb_watch_api_error", title=title, error=e.message)
        return {"status": "error", "error": e.message}
    except Exception as e:
        if _structured_logging_available:
            logger.error("tmdb_watch_unexpected_error", title=title, error=str(e))
        return {"status": "error", "error": str(e)}


def get_streaming_sources(
    title: str,
    tmdb_id: int = None,
    year: str = None,
    region: str = "US",
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Get streaming availability for a movie.
    
    Uses Watchmode API as primary source and falls back to TMDB if:
    - Watchmode API key not configured
    - Watchmode rate limit exceeded
    - Watchmode returns an error
    
    Args:
        title: Movie title
        tmdb_id: TMDB movie ID (required for Watchmode, optional for TMDB)
        year: Release year (optional, for better matching)
        region: ISO 3166-1 country code for regional availability
        use_cache: Whether to use cached results
        
    Returns:
        Dict containing:
        - status: "success", "not_found", "error", etc.
        - source: "watchmode" or "tmdb"
        - platforms: Dict with categorized streaming platforms
        - attribution: Required attribution text
    """
    # Check cache first
    if use_cache:
        cache = get_cache()
        cache_key = f"{title}:{tmdb_id}:{region}"
        cached = cache.get(cache_key, year=year, source="streaming")
        if cached:
            if _structured_logging_available:
                logger.info("streaming_cache_hit", title=title, tmdb_id=tmdb_id)
            return cached
    
    result = None
    
    # Try Watchmode first if configured and within limits
    if WATCHMODE_API_KEY and WATCHMODE_ENABLED and tmdb_id and _check_watchmode_rate_limit():
        result = _fetch_watchmode_sources(tmdb_id, title)
        
        if result.get("status") == "success":
            # Cache successful result
            if use_cache:
                cache.set(cache_key, result, year=year, source="streaming", ttl=3600)  # 1 hour TTL
            return result
    
    # Fallback to TMDB
    if tmdb_id:
        if _structured_logging_available:
            logger.info(
                "streaming_fallback_to_tmdb",
                title=title,
                tmdb_id=tmdb_id,
                reason=result.get("error", "Watchmode not available") if result else "Watchmode not configured"
            )
        
        result = _fetch_tmdb_watch_providers(tmdb_id, title, region)
        
        if result.get("status") == "success" and use_cache:
            cache.set(cache_key, result, year=year, source="streaming", ttl=3600)
        
        return result
    
    # No TMDB ID available
    return {
        "status": "error",
        "error": "TMDB ID required for streaming lookup",
        "platforms": {"subscription": [], "rent": [], "buy": [], "free": [], "all": []}
    }


def get_watchmode_usage_stats() -> Dict[str, Any]:
    """
    Get current Watchmode API usage statistics.
    
    Returns:
        Dict with usage stats including count, limit, and reset date
    """
    return {
        "count": _watchmode_usage["count"],
        "limit": WATCHMODE_MONTHLY_LIMIT,
        "remaining": max(0, WATCHMODE_MONTHLY_LIMIT - _watchmode_usage["count"]),
        "reset_date": _watchmode_usage["reset_date"].isoformat() if _watchmode_usage["reset_date"] else None,
        "enabled": WATCHMODE_ENABLED and bool(WATCHMODE_API_KEY)
    }
