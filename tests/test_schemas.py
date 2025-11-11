"""
Tests for movie data schemas.
"""

import pytest
from pydantic import ValidationError
from cineman.schemas import (
    MovieRatings,
    MovieIdentifiers,
    MovieDetails,
    MovieCredits,
    MovieRecommendation,
    MovieManifest,
    parse_movie_from_api,
    validate_llm_manifest,
)


class TestMovieRatings:
    """Test MovieRatings schema."""

    def test_valid_ratings(self):
        """Test creating ratings with valid data."""
        ratings = MovieRatings(
            imdb_rating="8.8", rt_tomatometer="87%", rt_audience="91%", tmdb_rating=8.2
        )
        assert ratings.imdb_rating == "8.8"
        assert ratings.rt_tomatometer == "87%"
        assert ratings.tmdb_rating == 8.2

    def test_empty_ratings(self):
        """Test creating empty ratings object."""
        ratings = MovieRatings()
        assert ratings.imdb_rating is None
        assert ratings.rt_tomatometer is None

    def test_na_values(self):
        """Test ratings with N/A values."""
        ratings = MovieRatings(imdb_rating="N/A", rt_tomatometer="N/A")
        assert ratings.imdb_rating == "N/A"
        assert ratings.rt_tomatometer == "N/A"

    def test_invalid_tmdb_rating(self):
        """Test validation of TMDB rating range."""
        with pytest.raises(ValidationError):
            MovieRatings(tmdb_rating=11.0)  # Should be 0-10

        with pytest.raises(ValidationError):
            MovieRatings(tmdb_rating=-1.0)  # Should be 0-10


class TestMovieIdentifiers:
    """Test MovieIdentifiers schema."""

    def test_valid_identifiers(self):
        """Test creating identifiers with valid data."""
        ids = MovieIdentifiers(imdb_id="tt1375666", tmdb_id=27205)
        assert ids.imdb_id == "tt1375666"
        assert ids.tmdb_id == 27205

    def test_empty_identifiers(self):
        """Test creating empty identifiers."""
        ids = MovieIdentifiers()
        assert ids.imdb_id is None
        assert ids.tmdb_id is None


class TestMovieCredits:
    """Test MovieCredits schema."""

    def test_valid_credits(self):
        """Test creating credits with valid data."""
        credits = MovieCredits(
            director="Christopher Nolan",
            writers=["Christopher Nolan"],
            cast=["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
        )
        assert credits.director == "Christopher Nolan"
        assert len(credits.cast) == 2

    def test_empty_credits(self):
        """Test creating empty credits."""
        credits = MovieCredits()
        assert credits.director is None
        assert credits.writers == []
        assert credits.cast == []


class TestMovieDetails:
    """Test MovieDetails schema."""

    def test_valid_details(self):
        """Test creating details with valid data."""
        details = MovieDetails(
            plot="A thief who steals corporate secrets...",
            runtime="148 min",
            genres=["Action", "Sci-Fi", "Thriller"],
        )
        assert "thief" in details.plot
        assert details.runtime == "148 min"
        assert len(details.genres) == 3

    def test_empty_details(self):
        """Test creating empty details."""
        details = MovieDetails()
        assert details.plot is None
        assert details.genres == []


class TestMovieRecommendation:
    """Test MovieRecommendation schema."""

    def test_minimal_movie(self):
        """Test creating movie with minimal required data."""
        movie = MovieRecommendation(title="Inception")
        assert movie.title == "Inception"
        assert movie.year is None
        assert isinstance(movie.ratings, MovieRatings)

    def test_complete_movie(self):
        """Test creating movie with complete data."""
        movie = MovieRecommendation(
            title="Inception",
            year="2010",
            ratings=MovieRatings(imdb_rating="8.8", rt_tomatometer="87%"),
            identifiers=MovieIdentifiers(imdb_id="tt1375666", tmdb_id=27205),
            credits=MovieCredits(
                director="Christopher Nolan", cast=["Leonardo DiCaprio"]
            ),
            details=MovieDetails(
                plot="A thief who steals...",
                runtime="148 min",
                genres=["Action", "Sci-Fi"],
            ),
            poster_url="https://example.com/poster.jpg",
            anchor_id="m1",
        )

        assert movie.title == "Inception"
        assert movie.year == "2010"
        assert movie.ratings.imdb_rating == "8.8"
        assert movie.identifiers.imdb_id == "tt1375666"
        assert movie.credits.director == "Christopher Nolan"
        assert len(movie.details.genres) == 2
        assert movie.anchor_id == "m1"

    def test_empty_title_fails(self):
        """Test that empty title fails validation."""
        with pytest.raises(ValidationError):
            MovieRecommendation(title="")

    def test_year_validation(self):
        """Test year validation."""
        # Valid years
        movie1 = MovieRecommendation(title="Test", year="2010")
        assert movie1.year == "2010"

        movie2 = MovieRecommendation(title="Test", year="2010-2012")
        assert movie2.year == "2010-2012"

        movie3 = MovieRecommendation(title="Test", year="N/A")
        assert movie3.year == "N/A"

        # Invalid year (no digits)
        with pytest.raises(ValidationError):
            MovieRecommendation(title="Test", year="Unknown")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        movie = MovieRecommendation(
            title="Inception", year="2010", ratings=MovieRatings(imdb_rating="8.8")
        )
        movie_dict = movie.to_dict()

        assert movie_dict["title"] == "Inception"
        assert movie_dict["year"] == "2010"
        assert "ratings" in movie_dict
        assert "created_at" not in movie_dict or movie_dict["created_at"] is not None

    def test_to_legacy_format(self):
        """Test conversion to legacy format."""
        movie = MovieRecommendation(
            title="Inception",
            year="2010",
            ratings=MovieRatings(imdb_rating="8.8", rt_tomatometer="87%"),
            identifiers=MovieIdentifiers(imdb_id="tt1375666"),
            anchor_text="Masterpiece #1: Inception (2010)",
            anchor_id="m1",
        )
        legacy = movie.to_legacy_format()

        assert legacy["title"] == "Inception"
        assert legacy["year"] == "2010"
        assert legacy["imdb_rating"] == "8.8"
        assert legacy["rt_tomatometer"] == "87%"
        assert legacy["imdb_id"] == "tt1375666"
        assert legacy["anchor_id"] == "m1"

    def test_nested_objects_from_dict(self):
        """Test creating movie from dict with nested objects."""
        movie = MovieRecommendation(
            title="Inception",
            ratings={"imdb_rating": "8.8"},
            identifiers={"imdb_id": "tt1375666"},
            credits={"director": "Christopher Nolan"},
            details={"plot": "A thief..."},
        )

        assert isinstance(movie.ratings, MovieRatings)
        assert isinstance(movie.identifiers, MovieIdentifiers)
        assert isinstance(movie.credits, MovieCredits)
        assert isinstance(movie.details, MovieDetails)
        assert movie.ratings.imdb_rating == "8.8"


class TestMovieManifest:
    """Test MovieManifest schema."""

    def test_valid_manifest(self):
        """Test creating manifest with valid movies."""
        manifest = MovieManifest(
            movies=[
                MovieRecommendation(title="Inception", anchor_id="m1"),
                MovieRecommendation(title="The Matrix", anchor_id="m2"),
                MovieRecommendation(title="Primer", anchor_id="m3"),
            ]
        )

        assert len(manifest.movies) == 3
        assert manifest.movies[0].title == "Inception"

    def test_empty_manifest_fails(self):
        """Test that empty manifest fails validation."""
        with pytest.raises(ValidationError):
            MovieManifest(movies=[])

    def test_to_legacy_format(self):
        """Test conversion to legacy format."""
        manifest = MovieManifest(
            movies=[
                MovieRecommendation(
                    title="Inception",
                    year="2010",
                    ratings=MovieRatings(imdb_rating="8.8"),
                    anchor_id="m1",
                ),
                MovieRecommendation(
                    title="The Matrix",
                    year="1999",
                    ratings=MovieRatings(imdb_rating="8.7"),
                    anchor_id="m2",
                ),
            ]
        )

        legacy = manifest.to_legacy_format()
        assert "movies" in legacy
        assert len(legacy["movies"]) == 2
        assert legacy["movies"][0]["title"] == "Inception"
        assert legacy["movies"][0]["anchor_id"] == "m1"


class TestParseMovieFromAPI:
    """Test parse_movie_from_api function."""

    def test_parse_combined_api(self):
        """Test parsing combined API response."""
        api_data = {
            "query": "Inception",
            "tmdb": {
                "title": "Inception",
                "year": "2010",
                "poster_url": "https://example.com/poster.jpg",
                "vote_average": 8.2,
                "tmdb_id": 27205,
            },
            "omdb": {
                "Title": "Inception",
                "Year": "2010",
                "Director": "Christopher Nolan",
                "IMDb_Rating": "8.8",
                "imdbID": "tt1375666",
            },
            "rating": "8.8",
            "rating_source": "OMDb/IMDb",
        }

        movie = parse_movie_from_api(api_data, source="combined")

        assert movie.title == "Inception"
        assert movie.year == "2010"
        assert movie.ratings.imdb_rating == "8.8"
        assert movie.ratings.tmdb_rating == 8.2
        assert movie.identifiers.tmdb_id == 27205
        assert movie.identifiers.imdb_id == "tt1375666"
        assert movie.credits.director == "Christopher Nolan"
        assert movie.poster_url == "https://example.com/poster.jpg"

    def test_parse_tmdb_api(self):
        """Test parsing TMDB API response."""
        api_data = {
            "title": "Inception",
            "year": "2010",
            "poster_url": "https://example.com/poster.jpg",
            "vote_average": 8.2,
            "tmdb_id": 27205,
        }

        movie = parse_movie_from_api(api_data, source="tmdb")

        assert movie.title == "Inception"
        assert movie.year == "2010"
        assert movie.ratings.tmdb_rating == 8.2
        assert movie.identifiers.tmdb_id == 27205

    def test_parse_omdb_api(self):
        """Test parsing OMDb API response."""
        api_data = {
            "Title": "Inception",
            "Year": "2010",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.8",
            "imdbID": "tt1375666",
            "Poster": "https://example.com/poster.jpg",
        }

        movie = parse_movie_from_api(api_data, source="omdb")

        assert movie.title == "Inception"
        assert movie.year == "2010"
        assert movie.ratings.imdb_rating == "8.8"
        assert movie.identifiers.imdb_id == "tt1375666"
        assert movie.credits.director == "Christopher Nolan"


class TestValidateLLMManifest:
    """Test validate_llm_manifest function."""

    def test_valid_llm_manifest(self):
        """Test validating valid LLM manifest."""
        manifest_json = {
            "movies": [
                {
                    "title": "Inception",
                    "year": "2010",
                    "imdb_rating": "8.8",
                    "rt_tomatometer": "87%",
                    "rt_audience": "91%",
                    "imdb_id": "tt1375666",
                    "anchor_text": "Masterpiece #1: Inception (2010)",
                    "anchor_id": "m1",
                },
                {
                    "title": "The Matrix",
                    "year": "1999",
                    "imdb_rating": "8.7",
                    "anchor_id": "m2",
                },
                {
                    "title": "Primer",
                    "year": "2004",
                    "imdb_rating": "6.9",
                    "anchor_id": "m3",
                },
            ]
        }

        manifest = validate_llm_manifest(manifest_json)

        assert len(manifest.movies) == 3
        assert manifest.movies[0].title == "Inception"
        assert manifest.movies[0].ratings.imdb_rating == "8.8"
        assert manifest.movies[0].anchor_id == "m1"

    def test_invalid_llm_manifest(self):
        """Test validating invalid LLM manifest."""
        manifest_json = {"movies": []}  # Empty movies list

        with pytest.raises(ValueError):
            validate_llm_manifest(manifest_json)

    def test_missing_movies_key(self):
        """Test validating manifest without movies key."""
        manifest_json = {}

        with pytest.raises(ValueError):
            validate_llm_manifest(manifest_json)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
