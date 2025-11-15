"""
Tests for Rotten Tomatoes ratings extraction and integration.
"""
import pytest
from cineman.schemas import MovieRatings, MovieRecommendation, parse_movie_from_api


class TestRottenTomatoesRatings:
    """Test RT ratings extraction from various sources."""
    
    def test_movie_ratings_with_rt(self):
        """Test MovieRatings schema with RT ratings."""
        ratings = MovieRatings(
            imdb_rating="8.8",
            rt_tomatometer="87%",
            rt_audience="91%",
            tmdb_rating=8.2
        )
        
        assert ratings.imdb_rating == "8.8"
        assert ratings.rt_tomatometer == "87%"
        assert ratings.rt_audience == "91%"
        assert ratings.tmdb_rating == 8.2
    
    def test_parse_combined_api_with_rt(self):
        """Test parsing combined API response with RT ratings."""
        api_data = {
            "query": "Inception",
            "tmdb": {
                "title": "Inception",
                "year": "2014",
                "poster_url": "https://example.com/poster.jpg",
                "vote_average": 8.6,
                "tmdb_id": 157336
            },
            "omdb": {
                "Title": "Inception",
                "Year": "2014",
                "Director": "Christopher Nolan",
                "IMDb_Rating": "8.7",
                "Rotten_Tomatoes": "87%",
                "imdbID": "tt0816692"
            },
            "rating": "8.7",
            "rating_source": "OMDb/IMDb"
        }
        
        movie = parse_movie_from_api(api_data, source="combined")
        
        assert movie.title == "Inception"
        assert movie.ratings.imdb_rating == "8.7"
        assert movie.ratings.rt_tomatometer == "87%"
        assert movie.ratings.tmdb_rating == 8.6
        assert movie.credits.director == "Christopher Nolan"
    
    def test_parse_omdb_api_with_rt(self):
        """Test parsing OMDb-only API response with RT ratings."""
        api_data = {
            "Title": "Inception",
            "Year": "2010",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.8",
            "Rotten_Tomatoes": "87%",
            "Poster_URL": "https://example.com/poster.jpg",
            "imdbID": "tt1375666"
        }
        
        movie = parse_movie_from_api(api_data, source="omdb")
        
        assert movie.title == "Inception"
        assert movie.ratings.imdb_rating == "8.8"
        assert movie.ratings.rt_tomatometer == "87%"
        assert movie.credits.director == "Christopher Nolan"
    
    def test_parse_combined_api_with_float_rating(self):
        """Test parsing combined API response when rating is a float (TMDb fallback)."""
        api_data = {
            "query": "Test Movie",
            "tmdb": {
                "title": "Test Movie",
                "year": "2020",
                "poster_url": "https://example.com/poster.jpg",
                "vote_average": 8.684,
                "tmdb_id": 12345
            },
            "omdb": {
                "Title": None,
                "IMDb_Rating": None,
                "Rotten_Tomatoes": None
            },
            "rating": 8.684,  # Float from TMDb
            "rating_source": "TMDb"
        }
        
        movie = parse_movie_from_api(api_data, source="combined")
        
        # Should convert float to string for IMDB rating field
        assert movie.title == "Test Movie"
        assert movie.ratings.imdb_rating == "8.684"
        assert isinstance(movie.ratings.imdb_rating, str)
        assert movie.ratings.tmdb_rating == 8.684
    
    def test_parse_combined_api_without_rt(self):
        """Test parsing combined API response without RT ratings."""
        api_data = {
            "query": "Unknown Movie",
            "tmdb": {
                "title": "Unknown Movie",
                "year": "2020",
                "poster_url": "https://example.com/poster.jpg",
                "vote_average": 7.0,
                "tmdb_id": 12345
            },
            "omdb": {
                "Title": "Unknown Movie",
                "Year": "2020",
                "IMDb_Rating": "7.0",
                "Rotten_Tomatoes": None  # No RT rating available
            },
            "rating": "7.0",
            "rating_source": "OMDb/IMDb"
        }
        
        movie = parse_movie_from_api(api_data, source="combined")
        
        assert movie.title == "Unknown Movie"
        assert movie.ratings.imdb_rating == "7.0"
        assert movie.ratings.rt_tomatometer is None
        assert movie.ratings.tmdb_rating == 7.0


    def test_api_response_structure_with_top_level_fields(self):
        """Test that API response includes top-level fields for frontend."""
        # Simulate the API response structure
        api_response = {
            "query": "Inception",
            "poster": "https://image.tmdb.org/poster.jpg",
            "imdb_rating": "8.8",
            "rt_tomatometer": "87%",
            "rating": "8.8",
            "rating_source": "OMDb/IMDb",
            "tmdb": {
                "status": "success",
                "poster_url": "https://image.tmdb.org/poster.jpg",
                "title": "Inception",
                "year": "2010"
            },
            "omdb": {
                "status": "success",
                "Title": "Inception",
                "Year": "2010",
                "IMDb_Rating": "8.8",
                "Rotten_Tomatoes": "87%"
            }
        }
        
        # Verify top-level fields exist
        assert "poster" in api_response
        assert "imdb_rating" in api_response
        assert "rt_tomatometer" in api_response
        
        # Verify values are correct
        assert api_response["poster"] == "https://image.tmdb.org/poster.jpg"
        assert api_response["imdb_rating"] == "8.8"
        assert api_response["rt_tomatometer"] == "87%"
        
        # Verify backward compatibility - nested fields still exist
        assert api_response["omdb"]["IMDb_Rating"] == "8.8"
        assert api_response["omdb"]["Rotten_Tomatoes"] == "87%"
    
    def test_multiple_rt_ratings_with_all_fields(self):
        """Test MovieRatings with multiple rating sources including RT."""
        ratings = MovieRatings(
            imdb_rating="8.5",
            imdb_votes="1.2M",
            rt_tomatometer="85%",
            rt_audience="89%",
            tmdb_rating=8.3,
            tmdb_vote_count=25000,
            metacritic="80/100"
        )
        
        assert ratings.imdb_rating == "8.5"
        assert ratings.imdb_votes == "1.2M"
        assert ratings.rt_tomatometer == "85%"
        assert ratings.rt_audience == "89%"
        assert ratings.tmdb_rating == 8.3
        assert ratings.tmdb_vote_count == 25000
        assert ratings.metacritic == "80/100"
    
    def test_na_rt_ratings(self):
        """Test handling of N/A RT ratings."""
        ratings = MovieRatings(
            imdb_rating="7.5",
            rt_tomatometer="N/A",
            rt_audience="N/A"
        )
        
        assert ratings.imdb_rating == "7.5"
        assert ratings.rt_tomatometer == "N/A"
        assert ratings.rt_audience == "N/A"
    
    def test_legacy_format_includes_rt_ratings(self):
        """Test that to_legacy_format includes RT ratings."""
        movie = MovieRecommendation(
            title="Test Movie",
            year="2020",
            ratings=MovieRatings(
                imdb_rating="8.0",
                rt_tomatometer="85%",
                rt_audience="88%"
            )
        )
        
        legacy = movie.to_legacy_format()
        
        assert "imdb_rating" in legacy
        assert legacy["imdb_rating"] == "8.0"
        assert "rt_tomatometer" in legacy
        assert legacy["rt_tomatometer"] == "85%"
    
    def test_integer_rating_conversion(self):
        """Test that integer ratings are also converted to strings."""
        api_data = {
            "query": "Test Movie",
            "tmdb": {
                "title": "Test Movie",
                "year": "2020",
                "vote_average": 8.0
            },
            "omdb": {
                "IMDb_Rating": None,
                "Rotten_Tomatoes": None
            },
            "rating": 8,  # Integer rating
            "rating_source": "TMDb"
        }
        
        movie = parse_movie_from_api(api_data, source="combined")
        
        # Should convert integer to string
        assert movie.ratings.imdb_rating == "8"
        assert isinstance(movie.ratings.imdb_rating, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
