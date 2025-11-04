import requests
import os
from langchain.tools import tool

# Get API Key and Base URL from environment
TMDB_API_KEY = os.getenv("TMDB_API_KEY") 
TMDB_BASE_URL = "https://api.themoviedb.org/3"
# Base URL for fetching high-resolution images
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500" 

# --- 1. CORE PYTHON FUNCTION (CALLABLE DIRECTLY) ---
def get_movie_poster_core(title: str) -> str:
    """
    Core function that executes the API call.
    This can be called directly for local testing.
    """
    if not TMDB_API_KEY:
        return '{"error": "TMDb API Key not configured."}'

    # 1. Search for the movie title to get its ID
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}
    
    try:
        search_response = requests.get(search_url, params=params, timeout=5).json()
        
        # Check if results exist and grab the top one
        if not search_response.get("results") or len(search_response["results"]) == 0:
            return '{"status": "Movie not found on TMDb.", "poster_url": ""}'
            
        first_result = search_response["results"][0]
        poster_path = first_result.get("poster_path")

        if poster_path:
            # 2. Construct the full poster URL and extract the year
            poster_url = f"{IMAGE_BASE_URL}{poster_path}"
            year = first_result.get("release_date", "")[:4]

            return f'{{"status": "success", "poster_url": "{poster_url}", "year": "{year}"}}'
        else:
            return '{"status": "Poster not available.", "poster_url": ""}'

    except Exception as e:
        return f'{{"status": "API connection failed.", "error": "{str(e)}"}}'

# --- 2. LANGCHAIN TOOL WRAPPER (NOT CALLABLE DIRECTLY) ---
@tool
def get_movie_poster(title: str) -> str:
    """
    Searches The Movie Database (TMDb) for a movie title and returns its poster URL 
    and release year. Use this to find the visual asset for a recommendation.
    
    Args:
        title (str): The movie title provided by the LLM (e.g., 'Inception').
        
    Returns:
        str: A JSON string containing the poster URL, year, and status.
    """
    # Calls the core, testable function
    return get_movie_poster_core(title)