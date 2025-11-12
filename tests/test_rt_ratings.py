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
    
    def test_movie_ratings_rt_na(self):
        """Test MovieRatings with N/A RT ratings."""
        ratings = MovieRatings(
            imdb_rating="7.5",
            rt_tomatometer="N/A"
        )
        
        assert ratings.imdb_rating == "7.5"
        assert ratings.rt_tomatometer == "N/A"
        assert ratings.rt_audience is None
    
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
    
    def test_movie_recommendation_with_all_ratings(self):
        """Test MovieRecommendation with complete ratings."""
        movie = MovieRecommendation(
            title="Inception",
            year="2010",
            ratings=MovieRatings(
                imdb_rating="8.8",
                rt_tomatometer="87%",
                rt_audience="91%",
                tmdb_rating=8.2,
                tmdb_vote_count=35420
            )
        )
        
        assert movie.title == "Inception"
        assert movie.ratings.imdb_rating == "8.8"
        assert movie.ratings.rt_tomatometer == "87%"
        assert movie.ratings.rt_audience == "91%"
        assert movie.ratings.tmdb_rating == 8.2
        assert movie.ratings.tmdb_vote_count == 35420
    
    def test_movie_to_dict_includes_rt(self):
        """Test that to_dict() includes RT ratings."""
        movie = MovieRecommendation(
            title="Test Movie",
            year="2020",
            ratings=MovieRatings(
                imdb_rating="8.0",
                rt_tomatometer="85%"
            )
        )
        
        movie_dict = movie.to_dict()
        
        assert "ratings" in movie_dict
        assert movie_dict["ratings"]["imdb_rating"] == "8.0"
        assert movie_dict["ratings"]["rt_tomatometer"] == "85%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
