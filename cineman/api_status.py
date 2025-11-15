"""
API Status Checker Module

Provides health check functions for external APIs used by Cineman:
- Google Gemini AI
- TMDB (The Movie Database)
- OMDB (Open Movie Database)
"""

import os
import time
import requests
from typing import Dict, Any


def check_gemini_status() -> Dict[str, Any]:
    """
    Check if Gemini API is accessible and configured.
    
    Returns:
        dict: Status information with keys 'status', 'message', and 'response_time'
    """
    start_time = time.time()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "message": "API key not configured",
            "response_time": 0
        }
    
    try:
        # Test with Gemini API - check if key is valid
        # Using the generativelanguage API endpoint for a simple check
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url, timeout=5)
        response_time = int((time.time() - start_time) * 1000)  # ms
        
        if response.status_code == 200:
            return {
                "status": "operational",
                "message": "API is operational",
                "response_time": response_time
            }
        elif response.status_code == 403:
            return {
                "status": "error",
                "message": "Invalid API key",
                "response_time": response_time
            }
        else:
            return {
                "status": "degraded",
                "message": f"Unexpected response: {response.status_code}",
                "response_time": response_time
            }
    except requests.Timeout:
        return {
            "status": "degraded",
            "message": "Request timeout",
            "response_time": 5000
        }
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "message": "Connection failed",
            "response_time": response_time
        }


def check_tmdb_status() -> Dict[str, Any]:
    """
    Check if TMDB API is accessible and configured.
    
    Returns:
        dict: Status information with keys 'status', 'message', and 'response_time'
    """
    start_time = time.time()
    
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "message": "API key not configured",
            "response_time": 0
        }
    
    try:
        # Test with a simple configuration endpoint
        url = f"https://api.themoviedb.org/3/configuration?api_key={api_key}"
        response = requests.get(url, timeout=5)
        response_time = int((time.time() - start_time) * 1000)  # ms
        
        if response.status_code == 200:
            return {
                "status": "operational",
                "message": "API is operational",
                "response_time": response_time
            }
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Invalid API key",
                "response_time": response_time
            }
        else:
            return {
                "status": "degraded",
                "message": f"Unexpected response: {response.status_code}",
                "response_time": response_time
            }
    except requests.Timeout:
        return {
            "status": "degraded",
            "message": "Request timeout",
            "response_time": 5000
        }
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "message": "Connection failed",
            "response_time": response_time
        }


def check_omdb_status() -> Dict[str, Any]:
    """
    Check if OMDB API is accessible and configured.
    
    Returns:
        dict: Status information with keys 'status', 'message', and 'response_time'
    """
    start_time = time.time()
    
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "message": "API key not configured",
            "response_time": 0
        }
    
    try:
        # Test with a simple movie query
        url = f"https://www.omdbapi.com/?apikey={api_key}&t=Inception&plot=short"
        response = requests.get(url, timeout=5)
        response_time = int((time.time() - start_time) * 1000)  # ms
        
        if response.status_code == 200:
            data = response.json()
            if data.get("Response") == "True":
                return {
                    "status": "operational",
                    "message": "API is operational",
                    "response_time": response_time
                }
            elif "Error" in data and "Invalid API key" in data["Error"]:
                return {
                    "status": "error",
                    "message": "Invalid API key",
                    "response_time": response_time
                }
            else:
                return {
                    "status": "degraded",
                    "message": data.get("Error", "Unknown error"),
                    "response_time": response_time
                }
        else:
            return {
                "status": "degraded",
                "message": f"Unexpected response: {response.status_code}",
                "response_time": response_time
            }
    except requests.Timeout:
        return {
            "status": "degraded",
            "message": "Request timeout",
            "response_time": 5000
        }
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "message": "Connection failed",
            "response_time": response_time
        }


def check_all_apis() -> Dict[str, Dict[str, Any]]:
    """
    Check status of all external APIs.
    
    Returns:
        dict: Dictionary with status for each API service
    """
    return {
        "gemini": check_gemini_status(),
        "tmdb": check_tmdb_status(),
        "omdb": check_omdb_status()
    }
