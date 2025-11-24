"""
Demo script showing how to use the movie data schema.

This script demonstrates various use cases for the CineMan movie data schema.
"""

from cineman.schemas import (
    MovieRecommendation,
    MovieRatings,
    MovieIdentifiers,
    MovieCredits,
    MovieDetails,
    parse_movie_from_api,
    validate_llm_manifest
)
from pydantic import ValidationError


def demo_basic_movie():
    """Create a basic movie with minimal required data."""
    print("\n" + "="*60)
    print("1. Creating a basic movie (minimal data)")
    print("="*60)
    
    movie = MovieRecommendation(title="Inception")
    
    print(f"Title: {movie.title}")
    print(f"Year: {movie.year}")
    print(f"Has ratings object: {movie.ratings is not None}")
    print(f"IMDB Rating: {movie.ratings.imdb_rating}")
    
    # Convert to dictionary
    print("\nAs dictionary (excluding None):")
    print(movie.to_dict())


def demo_complete_movie():
    """Create a movie with complete data."""
    print("\n" + "="*60)
    print("2. Creating a complete movie (full data)")
    print("="*60)
    
    movie = MovieRecommendation(
        title="Inception",
        year="2010",
        ratings=MovieRatings(
            imdb_rating="8.8",
            rt_tomatometer="87%",
            rt_audience="91%",
            tmdb_rating=8.2,
            tmdb_vote_count=35420
        ),
        identifiers=MovieIdentifiers(
            imdb_id="tt1375666",
            tmdb_id=27205
        ),
        credits=MovieCredits(
            director="Christopher Nolan",
            writers=["Christopher Nolan"],
            cast=["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Ellen Page"]
        ),
        details=MovieDetails(
            plot="A thief who steals corporate secrets through dream-sharing technology...",
            tagline="Your mind is the scene of the crime",
            runtime="148 min",
            genres=["Action", "Sci-Fi", "Thriller"],
            awards="Won 4 Oscars. 157 wins & 220 nominations total"
        ),
        poster_url="https://image.tmdb.org/t/p/w500/example.jpg",
        anchor_id="m1",
        anchor_text="Masterpiece #1: Inception (2010)"
    )
    
    print(f"Title: {movie.title} ({movie.year})")
    print(f"Director: {movie.credits.director}")
    print(f"IMDB Rating: {movie.ratings.imdb_rating}")
    print(f"RT Score: {movie.ratings.rt_tomatometer}")
    print(f"Runtime: {movie.details.runtime}")
    print(f"Genres: {', '.join(movie.details.genres)}")
    print(f"Cast: {', '.join(movie.credits.cast[:2])}...")
    print(f"Plot: {movie.details.plot[:100]}...")


def demo_dict_creation():
    """Create a movie from dictionary (simulating API response)."""
    print("\n" + "="*60)
    print("3. Creating movie from dictionary (auto-conversion)")
    print("="*60)
    
    movie_dict = {
        "title": "The Matrix",
        "year": "1999",
        "ratings": {
            "imdb_rating": "8.7",
            "rt_tomatometer": "88%"
        },
        "credits": {
            "director": "The Wachowskis"
        },
        "details": {
            "genres": ["Action", "Sci-Fi"]
        }
    }
    
    # Pydantic automatically converts nested dicts to schema objects
    movie = MovieRecommendation(**movie_dict)
    
    print(f"Title: {movie.title}")
    print(f"Director: {movie.credits.director}")
    print(f"Genres: {movie.details.genres}")
    print(f"Ratings is MovieRatings object: {isinstance(movie.ratings, MovieRatings)}")


def demo_validation():
    """Show validation in action."""
    print("\n" + "="*60)
    print("4. Schema validation (catching errors)")
    print("="*60)
    
    # Valid movie
    try:
        valid = MovieRecommendation(title="Valid Movie", year="2010")
        print(f"✓ Valid movie created: {valid.title}")
    except ValidationError as e:
        print(f"✗ Validation error: {e}")
    
    # Invalid: empty title
    try:
        invalid = MovieRecommendation(title="")
        print(f"✓ Created: {invalid.title}")
    except ValidationError as e:
        print(f"✗ Empty title rejected: {e.errors()[0]['msg']}")
    
    # Invalid: bad year format
    try:
        invalid = MovieRecommendation(title="Test", year="Unknown")
        print(f"✓ Created: {invalid.title}")
    except ValidationError as e:
        print(f"✗ Invalid year rejected: {e.errors()[0]['msg']}")
    
    # Invalid: TMDB rating out of range
    try:
        invalid = MovieRecommendation(
            title="Test",
            ratings={"tmdb_rating": 15.0}  # Should be 0-10
        )
        print(f"✓ Created: {invalid.title}")
    except ValidationError as e:
        print(f"✗ Invalid rating rejected: {e.errors()[0]['msg']}")


def demo_api_parsing():
    """Parse movie data from API response."""
    print("\n" + "="*60)
    print("5. Parsing API response (combined TMDB + OMDb)")
    print("="*60)
    
    api_response = {
        "query": "Interstellar",
        "tmdb": {
            "title": "Interstellar",
            "year": "2014",
            "poster_url": "https://example.com/poster.jpg",
            "vote_average": 8.6,
            "tmdb_id": 157336
        },
        "omdb": {
            "Title": "Interstellar",
            "Year": "2014",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.7",
            "imdbID": "tt0816692"
        },
        "rating": "8.7",
        "rating_source": "OMDb/IMDb"
    }
    
    movie = parse_movie_from_api(api_response, source="combined")
    
    print(f"Title: {movie.title}")
    print(f"Year: {movie.year}")
    print(f"IMDB Rating: {movie.ratings.imdb_rating}")
    print(f"TMDB Rating: {movie.ratings.tmdb_rating}")
    print(f"Director: {movie.credits.director}")
    print(f"IMDB ID: {movie.identifiers.imdb_id}")
    print(f"TMDB ID: {movie.identifiers.tmdb_id}")


def demo_llm_manifest():
    """Validate LLM manifest with multiple movies."""
    print("\n" + "="*60)
    print("6. Validating LLM manifest (multiple movies)")
    print("="*60)
    
    llm_manifest = {
        "movies": [
            {
                "title": "Inception",
                "year": "2010",
                "imdb_rating": "8.8",
                "rt_tomatometer": "87%",
                "anchor_id": "m1",
                "anchor_text": "Masterpiece #1: Inception (2010)"
            },
            {
                "title": "The Matrix",
                "year": "1999",
                "imdb_rating": "8.7",
                "anchor_id": "m2",
                "anchor_text": "Masterpiece #2: The Matrix (1999)"
            },
            {
                "title": "Primer",
                "year": "2004",
                "imdb_rating": "6.9",
                "anchor_id": "m3",
                "anchor_text": "Hidden Gem #3: Primer (2004)"
            }
        ]
    }
    
    manifest = validate_llm_manifest(llm_manifest)
    
    print(f"Valid manifest with {len(manifest.movies)} movies:")
    for i, movie in enumerate(manifest.movies, 1):
        print(f"  {i}. {movie.title} ({movie.year}) - {movie.ratings.imdb_rating}")


def demo_legacy_format():
    """Convert to legacy format for backward compatibility."""
    print("\n" + "="*60)
    print("7. Converting to legacy format (backward compatibility)")
    print("="*60)
    
    movie = MovieRecommendation(
        title="Inception",
        year="2010",
        ratings=MovieRatings(
            imdb_rating="8.8",
            rt_tomatometer="87%"
        ),
        identifiers=MovieIdentifiers(imdb_id="tt1375666"),
        anchor_id="m1"
    )
    
    print("Modern schema format:")
    print(f"  movie.title = {movie.title}")
    print(f"  movie.ratings.imdb_rating = {movie.ratings.imdb_rating}")
    print(f"  movie.identifiers.imdb_id = {movie.identifiers.imdb_id}")
    
    print("\nLegacy format (for existing frontend):")
    legacy = movie.to_legacy_format()
    for key, value in legacy.items():
        if value is not None:
            print(f"  {key} = {value}")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("CineMan Movie Data Schema Demo")
    print("="*60)
    
    demo_basic_movie()
    demo_complete_movie()
    demo_dict_creation()
    demo_validation()
    demo_api_parsing()
    demo_llm_manifest()
    demo_legacy_format()
    
    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60)
    print("\nFor more information, see docs/SCHEMA_GUIDE.md")


if __name__ == "__main__":
    main()
