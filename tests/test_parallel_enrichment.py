
import pytest
import time
from unittest.mock import patch, MagicMock
from cineman.validation import validate_movie_list

def test_backend_enrichment_parallelization():
    """
    Test that movie data is enriched on the backend and 
    API calls for different movies happen in parallel.
    """
    
    mock_tmdb_data = {
        "status": "success",
        "title": "Inception",
        "year": "2010",
        "tmdb_id": 27205,
        "poster_url": "https://image.tmdb.org/t/p/w500/inception.jpg",
        "vote_average": 8.3
    }
    
    mock_omdb_data = {
        "status": "success",
        "Title": "Inception",
        "Year": "2010",
        "Director": "Christopher Nolan",
        "imdbRating": "8.8"
    }
    
    mock_watchmode_data = {
        "providers": [{"name": "Netflix", "url": "https://netflix.com"}]
    }

    # Updated mocks to match the internal structure expected by validation.py wrappers
    mock_tmdb_wrapper = {
        "found": True,
        "title": "Inception",
        "year": "2010",
        "tmdb_id": 27205,
        "vote_average": 8.3,
        "raw": mock_tmdb_data
    }
    
    mock_omdb_wrapper = {
        "found": True,
        "title": "Inception",
        "year": "2010",
        "director": "Christopher Nolan",
        "raw": mock_omdb_data
    }

    # Use a slow side effect to verify parallel execution
    def slow_tmdb(*args, **kwargs):
        time.sleep(0.1)
        return mock_tmdb_wrapper

    with patch('cineman.validation.validate_against_tmdb', side_effect=slow_tmdb), \
         patch('cineman.validation.validate_against_omdb', return_value=mock_omdb_wrapper), \
         patch('cineman.validation.fetch_watchmode_data_core', return_value=mock_watchmode_data):
        
        movies = [
            {"title": "Inception", "year": "2010"},
            {"title": "Inception 2", "year": "2010"},
            {"title": "Inception 3", "year": "2010"}
        ]
        
        start_time = time.perf_counter()
        valid, dropped, summary = validate_movie_list(movies, session_id="perf_test")
        duration = time.perf_counter() - start_time
        
        # 1. Verify Parallelization
        # Duration should be closer to 0.1s than 0.3s
        assert duration < 0.25, f"Execution took too long ({duration:.2f}s), parallelization might be broken"
        
        # 2. Verify Enrichment
        assert len(valid) == 3
        for movie in valid:
            assert "poster_url" in movie
            assert "ratings" in movie
            assert "streaming" in movie
            assert movie["poster_url"] == mock_tmdb_data["poster_url"]
            assert movie["ratings"]["imdb_rating"] == mock_omdb_data["imdbRating"]
            assert movie["streaming"][0]["name"] == "Netflix"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
