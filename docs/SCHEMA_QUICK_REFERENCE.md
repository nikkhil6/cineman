# Movie Data Schema - Quick Reference

## Basic Usage

### Creating a Movie

```python
from cineman.schemas import MovieRecommendation

# Minimal
movie = MovieRecommendation(title="Inception")

# Complete
movie = MovieRecommendation(
    title="Inception",
    year="2010",
    ratings={"imdb_rating": "8.8"},
    credits={"director": "Christopher Nolan"},
    poster_url="https://..."
)
```

### Parsing API Data

```python
from cineman.schemas import parse_movie_from_api

# From combined endpoint
movie = parse_movie_from_api(api_response, source="combined")

# From TMDB
movie = parse_movie_from_api(tmdb_data, source="tmdb")

# From OMDb
movie = parse_movie_from_api(omdb_data, source="omdb")
```

### Validating LLM Manifest

```python
from cineman.schemas import validate_llm_manifest

manifest_json = {
    "movies": [
        {"title": "Movie 1", "year": "2010", ...},
        {"title": "Movie 2", "year": "2011", ...}
    ]
}

manifest = validate_llm_manifest(manifest_json)
```

## Schema Structure

```
MovieRecommendation
├── title: str (required)
├── year: str (optional)
├── poster_url: str (optional)
├── ratings: MovieRatings
│   ├── imdb_rating: str
│   ├── rt_tomatometer: str
│   ├── rt_audience: str
│   ├── tmdb_rating: float
│   └── metacritic: str
├── identifiers: MovieIdentifiers
│   ├── imdb_id: str
│   ├── tmdb_id: int
│   └── omdb_id: str
├── credits: MovieCredits
│   ├── director: str
│   ├── writers: List[str]
│   ├── cast: List[str]
│   └── producers: List[str]
└── details: MovieDetails
    ├── plot: str
    ├── tagline: str
    ├── runtime: str
    ├── genres: List[str]
    ├── language: str
    ├── country: str
    ├── awards: str
    └── box_office: str
```

## Accessing Data

```python
# Nested access
movie.ratings.imdb_rating
movie.credits.director
movie.details.genres

# Convert to dict
movie.to_dict()

# Convert to legacy format
movie.to_legacy_format()
```

## Validation

```python
from pydantic import ValidationError

try:
    movie = MovieRecommendation(title="")  # Empty title
except ValidationError as e:
    print(e.errors())
```

## Common Patterns

### Create from Dict

```python
movie_dict = {"title": "Movie", "year": "2010"}
movie = MovieRecommendation(**movie_dict)
```

### Update Movie Data

```python
movie_dict = movie.to_dict()
movie_dict["year"] = "2011"
updated = MovieRecommendation(**movie_dict)
```

### Merge Multiple Sources

```python
from cineman.schemas import MovieRecommendation

movie = MovieRecommendation(
    title=tmdb_data.get("title"),
    year=tmdb_data.get("year"),
    ratings={"imdb_rating": omdb_data.get("imdbRating")},
    credits={"director": omdb_data.get("Director")}
)
```

## Validation Rules

- **Title**: Required, non-empty
- **Year**: Optional, must contain at least one digit
- **TMDB Rating**: 0-10 range
- **Vote Counts**: Non-negative integers
- **Nested Objects**: Auto-converted from dicts

## Files

- **Schema Definition**: `cineman/schemas.py`
- **Tests**: `tests/test_schemas.py`
- **Full Guide**: `docs/SCHEMA_GUIDE.md`
- **Demo**: `examples/schema_demo.py`
- **API Integration**: `cineman/routes/api.py`

## Testing

```bash
# Run all schema tests
python -m pytest tests/test_schemas.py -v

# Run demo
PYTHONPATH=. python examples/schema_demo.py
```

## API Response Format

```json
{
  "query": "Inception",
  "tmdb": {...},
  "omdb": {...},
  "rating": "8.8",
  "rating_source": "OMDb/IMDb",
  "schema": {
    "title": "Inception",
    "year": "2010",
    "ratings": {
      "imdb_rating": "8.8",
      "tmdb_rating": 8.2
    },
    "credits": {
      "director": "Christopher Nolan"
    },
    ...
  }
}
```

## Future Extensions

To add a new field:

1. Add to schema class:
```python
streaming_services: Optional[List[str]] = Field(default_factory=list)
```

2. Update example in `model_config`

3. Add tests

4. Update docs
