"""
Utility functions for CineMan application.
"""

import json
from typing import Dict, Any, Optional
from cineman.schemas import MovieManifest, validate_llm_manifest
from pydantic import ValidationError


def extract_and_validate_manifest(llm_response: str) -> Optional[MovieManifest]:
    """
    Extract and validate the JSON manifest from an LLM response.
    
    Args:
        llm_response: The full text response from the LLM
        
    Returns:
        MovieManifest if valid, None otherwise
    """
    if not llm_response or not isinstance(llm_response, str):
        return None
    
    # Try to find JSON manifest at the end of the response
    # Look for the last occurrence of two newlines followed by {
    two_newline_idx = llm_response.rfind('\n\n{')
    start_idx = -1
    
    if two_newline_idx != -1:
        start_idx = two_newline_idx + 2
    else:
        # Fallback: look for the last {
        start_idx = llm_response.rfind('{')
    
    if start_idx == -1:
        return None
    
    # Extract the potential JSON
    possible_json = llm_response[start_idx:].strip()
    
    try:
        # Parse JSON
        manifest_json = json.loads(possible_json)
        
        # Validate against schema
        manifest = validate_llm_manifest(manifest_json)
        
        return manifest
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        # If validation fails, return None (caller can handle gracefully)
        print(f"Manifest extraction/validation failed: {e}")
        return None


def format_movie_for_display(movie_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format movie data for frontend display.
    
    Args:
        movie_data: Raw movie data from various sources
        
    Returns:
        Formatted movie data with consistent structure
    """
    return {
        "title": movie_data.get("title") or movie_data.get("Title", "Unknown"),
        "year": movie_data.get("year") or movie_data.get("Year"),
        "poster": movie_data.get("poster_url") or movie_data.get("Poster_URL"),
        "director": movie_data.get("director") or movie_data.get("Director"),
        "rating": movie_data.get("rating") or movie_data.get("imdb_rating") or movie_data.get("IMDb_Rating"),
        "plot": movie_data.get("plot") or movie_data.get("Plot"),
    }


def merge_movie_data(tmdb_data: Dict[str, Any], omdb_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge data from TMDB and OMDb sources, preferring more complete data.
    
    Args:
        tmdb_data: Data from TMDB API
        omdb_data: Data from OMDb API
        
    Returns:
        Merged movie data dictionary
    """
    merged = {}
    
    # Title (prefer TMDB)
    merged["title"] = tmdb_data.get("title") or omdb_data.get("Title", "")
    
    # Year (prefer whichever is present)
    merged["year"] = tmdb_data.get("year") or omdb_data.get("Year")
    
    # Poster (prefer TMDB for better quality)
    merged["poster_url"] = tmdb_data.get("poster_url") or omdb_data.get("Poster_URL")
    
    # Rating (prefer IMDb from OMDb, fallback to TMDB)
    if omdb_data.get("IMDb_Rating"):
        merged["imdb_rating"] = omdb_data.get("IMDb_Rating")
    elif tmdb_data.get("vote_average"):
        merged["tmdb_rating"] = tmdb_data.get("vote_average")
    
    # Director (only from OMDb)
    if omdb_data.get("Director"):
        merged["director"] = omdb_data.get("Director")
    
    # IDs
    if tmdb_data.get("tmdb_id"):
        merged["tmdb_id"] = tmdb_data.get("tmdb_id")
    if omdb_data.get("imdbID"):
        merged["imdb_id"] = omdb_data.get("imdbID")
    
    return merged
