"""
Data schemas for CineMan movie data.

This module defines Pydantic models for movie data validation and serialization.
These schemas ensure data consistency across API responses, LLM outputs, and frontend display.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone


class MovieRatings(BaseModel):
    """
    Movie ratings from various sources.
    """
    imdb_rating: Optional[str] = Field(None, description="IMDB rating (e.g., '8.8', 'N/A')")
    imdb_votes: Optional[str] = Field(None, description="Number of IMDB votes (e.g., '2.3M')")
    rt_tomatometer: Optional[str] = Field(None, description="Rotten Tomatoes critics score (e.g., '87%', 'N/A')")
    rt_audience: Optional[str] = Field(None, description="Rotten Tomatoes audience score (e.g., '91%', 'N/A')")
    tmdb_rating: Optional[float] = Field(None, description="TMDB vote average (0-10)", ge=0, le=10)
    tmdb_vote_count: Optional[int] = Field(None, description="TMDB vote count", ge=0)
    metacritic: Optional[str] = Field(None, description="Metacritic score (e.g., '74/100', 'N/A')")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "imdb_rating": "8.8",
                "imdb_votes": "2.3M",
                "rt_tomatometer": "87%",
                "rt_audience": "91%",
                "tmdb_rating": 8.2,
                "tmdb_vote_count": 35420,
                "metacritic": "74/100"
            }
        }
    )


class MovieIdentifiers(BaseModel):
    """
    External identifiers for the movie across different databases.
    """
    imdb_id: Optional[str] = Field(None, description="IMDB ID (e.g., 'tt1375666')")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID", ge=0)
    omdb_id: Optional[str] = Field(None, description="OMDB ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "imdb_id": "tt1375666",
                "tmdb_id": 27205,
                "omdb_id": "tt1375666"
            }
        }
    )


class MovieDetails(BaseModel):
    """
    Detailed information about a movie.
    """
    plot: Optional[str] = Field(None, description="Short plot summary")
    tagline: Optional[str] = Field(None, description="Movie tagline")
    runtime: Optional[str] = Field(None, description="Runtime (e.g., '148 min')")
    genres: Optional[List[str]] = Field(default_factory=list, description="List of genres")
    language: Optional[str] = Field(None, description="Primary language")
    country: Optional[str] = Field(None, description="Country of origin")
    awards: Optional[str] = Field(None, description="Awards and nominations")
    box_office: Optional[str] = Field(None, description="Box office earnings")
    production: Optional[str] = Field(None, description="Production company")
    website: Optional[str] = Field(None, description="Official website URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plot": "A thief who steals corporate secrets through dream-sharing technology...",
                "tagline": "Your mind is the scene of the crime",
                "runtime": "148 min",
                "genres": ["Action", "Sci-Fi", "Thriller"],
                "language": "English",
                "country": "USA, UK",
                "awards": "Won 4 Oscars. 157 wins & 220 nominations total",
                "box_office": "$836,836,967",
                "production": "Warner Bros. Pictures",
                "website": "https://www.inceptionmovie.com"
            }
        }
    )


class MovieCredits(BaseModel):
    """
    Cast and crew information.
    """
    director: Optional[str] = Field(None, description="Director name(s)")
    writers: Optional[List[str]] = Field(default_factory=list, description="List of writers")
    cast: Optional[List[str]] = Field(default_factory=list, description="List of main cast members")
    producers: Optional[List[str]] = Field(default_factory=list, description="List of producers")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "director": "Christopher Nolan",
                "writers": ["Christopher Nolan"],
                "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Ellen Page"],
                "producers": ["Emma Thomas", "Christopher Nolan"]
            }
        }
    )


class MovieRecommendation(BaseModel):
    """
    Complete movie recommendation schema with all metadata.
    
    This is the comprehensive schema for movie data used throughout the application.
    It combines data from multiple sources (TMDB, OMDb, LLM) and provides validation.
    """
    # Basic information (required)
    title: str = Field(..., description="Movie title", min_length=1)
    year: Optional[str] = Field(None, description="Release year (e.g., '2010')")
    
    # Ratings (aggregated)
    ratings: Optional[MovieRatings] = Field(default_factory=MovieRatings, description="Movie ratings")
    
    # Identifiers
    identifiers: Optional[MovieIdentifiers] = Field(default_factory=MovieIdentifiers, description="External IDs")
    
    # Credits
    credits: Optional[MovieCredits] = Field(default_factory=MovieCredits, description="Cast and crew")
    
    # Details
    details: Optional[MovieDetails] = Field(default_factory=MovieDetails, description="Detailed information")
    
    # Media
    poster_url: Optional[str] = Field(None, description="Poster image URL")
    backdrop_url: Optional[str] = Field(None, description="Backdrop image URL")
    
    # LLM-specific fields (for recommendation context)
    anchor_text: Optional[str] = Field(None, description="Anchor text from LLM response")
    anchor_id: Optional[str] = Field(None, description="Anchor ID (e.g., 'm1', 'm2', 'm3')")
    quick_pitch: Optional[str] = Field(None, description="Quick pitch from LLM")
    why_matches: Optional[str] = Field(None, description="Why it matches user's request")
    award_highlight: Optional[str] = Field(None, description="Award and prestige highlights")
    
    # Metadata
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    
    # Additional data
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('year')
    @classmethod
    def validate_year(cls, v):
        """Validate year format (optional, flexible)."""
        if v and v != 'N/A':
            # Allow various year formats: "2010", "2010-2012", "2010-"
            if not any(c.isdigit() for c in v):
                raise ValueError('Year must contain at least one digit')
        return v

    @field_validator('ratings', mode='before')
    @classmethod
    def ensure_ratings(cls, v):
        """Ensure ratings is always a MovieRatings object."""
        if v is None:
            return MovieRatings()
        if isinstance(v, dict):
            return MovieRatings(**v)
        return v

    @field_validator('identifiers', mode='before')
    @classmethod
    def ensure_identifiers(cls, v):
        """Ensure identifiers is always a MovieIdentifiers object."""
        if v is None:
            return MovieIdentifiers()
        if isinstance(v, dict):
            return MovieIdentifiers(**v)
        return v

    @field_validator('credits', mode='before')
    @classmethod
    def ensure_credits(cls, v):
        """Ensure credits is always a MovieCredits object."""
        if v is None:
            return MovieCredits()
        if isinstance(v, dict):
            return MovieCredits(**v)
        return v

    @field_validator('details', mode='before')
    @classmethod
    def ensure_details(cls, v):
        """Ensure details is always a MovieDetails object."""
        if v is None:
            return MovieDetails()
        if isinstance(v, dict):
            return MovieDetails(**v)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Inception",
                "year": "2010",
                "ratings": {
                    "imdb_rating": "8.8",
                    "rt_tomatometer": "87%",
                    "rt_audience": "91%",
                    "tmdb_rating": 8.2
                },
                "identifiers": {
                    "imdb_id": "tt1375666",
                    "tmdb_id": 27205
                },
                "credits": {
                    "director": "Christopher Nolan",
                    "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"]
                },
                "details": {
                    "plot": "A thief who steals corporate secrets...",
                    "runtime": "148 min",
                    "genres": ["Action", "Sci-Fi", "Thriller"]
                },
                "poster_url": "https://image.tmdb.org/t/p/w500/...",
                "anchor_text": "Masterpiece #1: Inception (2010)",
                "anchor_id": "m1"
            }
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary, excluding None values for cleaner output.
        """
        return self.model_dump(exclude_none=True)

    def to_legacy_format(self) -> Dict[str, Any]:
        """
        Convert to legacy format used by the current LLM manifest.
        This ensures backward compatibility with existing frontend code.
        """
        return {
            "title": self.title,
            "year": self.year,
            "imdb_rating": self.ratings.imdb_rating if self.ratings else None,
            "rt_tomatometer": self.ratings.rt_tomatometer if self.ratings else None,
            "rt_audience": self.ratings.rt_audience if self.ratings else None,
            "imdb_id": self.identifiers.imdb_id if self.identifiers else None,
            "anchor_text": self.anchor_text,
            "anchor_id": self.anchor_id,
        }


class MovieManifest(BaseModel):
    """
    Schema for the LLM response manifest containing multiple movie recommendations.
    """
    movies: List[MovieRecommendation] = Field(..., description="List of movie recommendations", min_length=1, max_length=10)
    
    @field_validator('movies')
    @classmethod
    def validate_movie_count(cls, v):
        """Validate that we have the expected number of movies (typically 3)."""
        if len(v) == 0:
            raise ValueError('Manifest must contain at least one movie')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "movies": [
                    {
                        "title": "Inception",
                        "year": "2010",
                        "imdb_rating": "8.8",
                        "anchor_id": "m1"
                    },
                    {
                        "title": "The Matrix",
                        "year": "1999",
                        "imdb_rating": "8.7",
                        "anchor_id": "m2"
                    },
                    {
                        "title": "Primer",
                        "year": "2004",
                        "imdb_rating": "6.9",
                        "anchor_id": "m3"
                    }
                ]
            }
        }
    )

    def to_legacy_format(self) -> Dict[str, Any]:
        """
        Convert to legacy format for backward compatibility.
        """
        return {
            "movies": [movie.to_legacy_format() for movie in self.movies]
        }


def parse_movie_from_api(api_data: Dict[str, Any], source: str = "combined") -> MovieRecommendation:
    """
    Parse movie data from API responses (TMDB, OMDb, or combined endpoint).
    
    Args:
        api_data: Raw API response data
        source: Source of the data ("tmdb", "omdb", or "combined")
    
    Returns:
        MovieRecommendation: Parsed and validated movie data
    """
    movie_data = {
        "title": "",
        "year": None,
        "ratings": MovieRatings(),
        "identifiers": MovieIdentifiers(),
        "credits": MovieCredits(),
        "details": MovieDetails(),
        "poster_url": None,
    }

    if source == "combined":
        # Parse combined API response
        tmdb = api_data.get("tmdb", {})
        omdb = api_data.get("omdb", {})
        
        movie_data["title"] = tmdb.get("title") or omdb.get("Title") or api_data.get("query", "")
        movie_data["year"] = tmdb.get("year") or omdb.get("Year")
        
        # Ratings
        # Convert rating to string if it's a float (TMDb fallback case)
        imdb_rating_value = omdb.get("IMDb_Rating") or api_data.get("rating")
        if isinstance(imdb_rating_value, (int, float)):
            imdb_rating_value = str(imdb_rating_value)
        
        movie_data["ratings"] = MovieRatings(
            imdb_rating=imdb_rating_value,
            rt_tomatometer=omdb.get("Rotten_Tomatoes"),
            tmdb_rating=tmdb.get("vote_average"),
            tmdb_vote_count=tmdb.get("vote_count")
        )
        
        # Identifiers
        movie_data["identifiers"] = MovieIdentifiers(
            tmdb_id=tmdb.get("tmdb_id"),
            imdb_id=omdb.get("imdbID")
        )
        
        # Credits
        movie_data["credits"] = MovieCredits(
            director=omdb.get("Director")
        )
        
        # Poster
        movie_data["poster_url"] = tmdb.get("poster_url") or omdb.get("Poster_URL")
        
    elif source == "tmdb":
        # Parse TMDB-only response
        movie_data["title"] = api_data.get("title", "")
        movie_data["year"] = api_data.get("year")
        movie_data["poster_url"] = api_data.get("poster_url")
        movie_data["ratings"] = MovieRatings(
            tmdb_rating=api_data.get("vote_average"),
            tmdb_vote_count=api_data.get("vote_count")
        )
        movie_data["identifiers"] = MovieIdentifiers(
            tmdb_id=api_data.get("tmdb_id")
        )
        
    elif source == "omdb":
        # Parse OMDb-only response
        movie_data["title"] = api_data.get("Title", "")
        movie_data["year"] = api_data.get("Year")
        movie_data["poster_url"] = api_data.get("Poster_URL") or api_data.get("Poster")
        movie_data["ratings"] = MovieRatings(
            imdb_rating=api_data.get("IMDb_Rating") or api_data.get("imdbRating"),
            rt_tomatometer=api_data.get("Rotten_Tomatoes")
        )
        movie_data["identifiers"] = MovieIdentifiers(
            imdb_id=api_data.get("imdbID")
        )
        movie_data["credits"] = MovieCredits(
            director=api_data.get("Director")
        )

    return MovieRecommendation(**movie_data)


def validate_llm_manifest(manifest_json: Dict[str, Any]) -> MovieManifest:
    """
    Validate and parse LLM manifest JSON.
    
    Args:
        manifest_json: Raw JSON from LLM response
    
    Returns:
        MovieManifest: Validated manifest
    
    Raises:
        ValueError: If manifest is invalid
    """
    try:
        # Parse movies from legacy format
        movies = []
        for movie_data in manifest_json.get("movies", []):
            movie = MovieRecommendation(
                title=movie_data.get("title", ""),
                year=movie_data.get("year"),
                ratings=MovieRatings(
                    imdb_rating=movie_data.get("imdb_rating"),
                    rt_tomatometer=movie_data.get("rt_tomatometer"),
                    rt_audience=movie_data.get("rt_audience")
                ),
                identifiers=MovieIdentifiers(
                    imdb_id=movie_data.get("imdb_id")
                ),
                anchor_text=movie_data.get("anchor_text"),
                anchor_id=movie_data.get("anchor_id")
            )
            movies.append(movie)
        
        return MovieManifest(movies=movies)
    except Exception as e:
        raise ValueError(f"Invalid LLM manifest: {str(e)}")
