import requests
import os
from langchain.tools import tool # <--- Keep the tool import here

OMDB_API_KEY = os.getenv("OMDB_API_KEY") 
BASE_URL = "http://www.omdbapi.com/"

# --- 1. CORE PYTHON FUNCTION (STILL CALLABLE) ---
def fetch_omdb_data_core(title: str) -> str:
    """
    Core function that executes the API call. 
    This can be called directly for local testing.
    """
    if not OMDB_API_KEY:
        return '{"error": "OMDb API Key not configured."}'

    params = {"apikey": OMDB_API_KEY, "t": title, "plot": "full"}
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=5).json()

        if response.get("Response") == "True":
            facts = {
                "Title": response.get("Title"),
                "Year": response.get("Year"),
                "Director": response.get("Director"),
                "IMDb_Rating": response.get("imdbRating"),
                "Poster_URL": response.get("Poster")
            }
            return str(facts)
        else:
            return f'{{"error": "Movie not found or OMDb error: {response.get("Error")}"}}'
    
    except Exception as e:
        return f'{{"error": "API connection failed.", "details": "{str(e)}"}}'

# --- 2. LANGCHAIN TOOL WRAPPER (NOT CALLABLE DIRECTLY) ---
@tool
def get_movie_facts(title: str) -> str:
    """
    Fetches objective data (ratings, director, and poster URL) for a movie 
    from the Open Movie Database (OMDb) API. Use this to verify facts and visuals.
    
    Args:
        title (str): The exact title of the movie to search for (e.g., 'Inception').
        
    Returns:
        str: A JSON string containing the facts and the Poster URL.
    """
    # Calls the core, testable function
    return fetch_omdb_data_core(title)