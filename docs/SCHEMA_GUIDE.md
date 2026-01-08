# CineMan Movie Data Schema Guide

## Overview

CineMan uses a comprehensive, validated data schema for all movie information. This ensures consistency, type safety, and extensibility across the application.

## Why Use a Schema?

1. **Data Validation**: Automatically validate movie data from multiple sources (TMDB, OMDb, LLM)
2. **Type Safety**: Catch errors early with strong typing
3. **Consistency**: Uniform structure across API endpoints and frontend
4. **Documentation**: Self-documenting code with clear field descriptions
5. **Extensibility**: Easy to add new fields without breaking existing code
6. **Future-Proofing**: Built with long-term usage and feature additions in mind
7. **Structured-Direct Efficiency**: Enables the backend to pre-populate all movie data, eliminating fragile frontend scraping and redundant API calls.

## Schema Structure

### Core Schemas

#### `MovieRecommendation`
The main schema representing a complete movie with all metadata.

**Key Features:**
- Required: `title`
- Optional: All other fields with sensible defaults
- Nested structures for ratings, identifiers, credits, and details
- Validation for data integrity (e.g., year format, rating ranges)
- Backward compatibility with legacy format

**Example:**
```python
from cineman.schemas import MovieRecommendation

movie = MovieRecommendation(
    title="Inception",
    year="2010",
    ratings={
        "imdb_rating": "8.8",
        "rt_tomatometer": "87%"
    },
    identifiers={
        "imdb_id": "tt1375666",
        "tmdb_id": 27205
    },
    credits={
        "director": "Christopher Nolan"
    },
    poster_url="https://example.com/poster.jpg"
)
```

### Nested Schemas

#### `MovieRatings`
Aggregates ratings from multiple sources:
- IMDB ratings and vote counts
- Rotten Tomatoes (critics and audience)
- TMDB ratings
- Metacritic scores

#### `MovieIdentifiers`
External database identifiers:
- `imdb_id`: IMDB identifier (e.g., "tt1375666")
- `tmdb_id`: TMDB identifier
- `omdb_id`: OMDb identifier

#### `MovieCredits`
Cast and crew information:
- `director`: Director name(s)
- `writers`: List of writers
- `cast`: List of main cast members
- `producers`: List of producers

#### `MovieDetails`
Detailed movie information:
- `plot`: Short plot summary
- `tagline`: Movie tagline
- `runtime`: Runtime (e.g., "148 min")
- `genres`: List of genres
- `language`: Primary language
- `country`: Country of origin
- `awards`: Awards and nominations
- `box_office`: Box office earnings
- `production`: Production company
- `website`: Official website URL

## Usage Examples

### 1. Creating a Movie from API Data

```python
from cineman.schemas import parse_movie_from_api

# Parse from combined API endpoint
api_response = {
    "query": "Inception",
    "tmdb": {"title": "Inception", "year": "2010", "poster_url": "..."},
    "omdb": {"Director": "Christopher Nolan", "IMDb_Rating": "8.8"}
}

movie = parse_movie_from_api(api_response, source="combined")
print(movie.title)  # "Inception"
print(movie.credits.director)  # "Christopher Nolan"
```

### 2. Validating LLM Manifest

```python
from cineman.schemas import validate_llm_manifest

# LLM response with movie manifest
manifest_json = {
    "movies": [
        {
            "title": "Inception",
            "year": "2010",
            "imdb_rating": "8.8",
            "anchor_id": "m1"
        },
        # ... more movies
    ]
}

manifest = validate_llm_manifest(manifest_json)
print(len(manifest.movies))  # 3 (or however many movies)
```

### 3. Converting to Legacy Format

For backward compatibility with existing frontend code:

```python
movie = MovieRecommendation(title="Inception", year="2010")
legacy_format = movie.to_legacy_format()
# Returns: {"title": "Inception", "year": "2010", "imdb_rating": None, ...}
```

### 4. Accessing Nested Data

```python
movie = MovieRecommendation(
    title="Inception",
    ratings={"imdb_rating": "8.8", "tmdb_rating": 8.2},
    details={"genres": ["Action", "Sci-Fi"]}
)

# Access nested data safely
print(movie.ratings.imdb_rating)  # "8.8"
print(movie.details.genres)  # ["Action", "Sci-Fi"]
```

## API Integration

### GET `/api/movie`

Now returns both legacy format and validated schema:

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
    ...
  }
}
```

## Validation Features

### Built-in Validators

1. **Title Validation**: Title cannot be empty
2. **Year Validation**: Year must contain at least one digit (allows "2010", "2010-2012", "N/A")
3. **Rating Ranges**: TMDB ratings must be 0-10
4. **Vote Counts**: Must be non-negative
5. **Auto-conversion**: Dict inputs automatically converted to nested schema objects

### Error Handling

```python
from pydantic import ValidationError

try:
    movie = MovieRecommendation(title="")  # Empty title
except ValidationError as e:
    print(e.errors())
    # [{'loc': ('title',), 'msg': 'String should have at least 1 character', ...}]
```

## Extending the Schema

### Adding New Fields

To add a new field:

1. Add to the appropriate schema class:
```python
class MovieDetails(BaseModel):
    # ... existing fields ...
    streaming_services: Optional[List[str]] = Field(
        default_factory=list,
        description="Available streaming services"
    )
```

2. Update the example in `model_config`:
```python
model_config = ConfigDict(
    json_schema_extra={
        "example": {
            # ... existing fields ...
            "streaming_services": ["Netflix", "Amazon Prime"]
        }
    }
)
```

3. Add tests in `tests/test_schemas.py`

### Creating Custom Validators

```python
from pydantic import field_validator

class MovieRecommendation(BaseModel):
    # ... fields ...
    
    @field_validator('runtime')
    @classmethod
    def validate_runtime(cls, v):
        """Validate runtime format."""
        if v and not ('min' in v or 'hr' in v):
            raise ValueError('Runtime must include time unit (min or hr)')
        return v
```

## Best Practices

1. **Always use schemas for API responses**: Ensures consistent data structure
2. **Validate LLM outputs**: Use `validate_llm_manifest()` to catch malformed responses
3. **Use `to_legacy_format()` for backward compatibility**: When updating existing code
4. **Handle validation errors gracefully**: Use try-except blocks
5. **Use type hints**: IDEs will provide better autocomplete
6. **Document new fields**: Add descriptions to all new fields

## Migration Guide

### For Existing Code

If you have code that works with raw dictionaries:

**Before:**
```python
movie_data = {"title": "Inception", "year": "2010"}
title = movie_data.get("title")
```

**After:**
```python
from cineman.schemas import MovieRecommendation

movie = MovieRecommendation(title="Inception", year="2010")
title = movie.title  # Type-safe, validated
```

### For API Clients

Frontend code can continue using the legacy format (fields at top level of response), or upgrade to use the `schema` field for validated, structured data:

```javascript
// Legacy approach (still works)
const title = response.tmdb.title;

// New approach (recommended)
const title = response.schema.title;
const director = response.schema.credits.director;
```

## Testing

All schemas have comprehensive tests in `tests/test_schemas.py`:

```bash
python -m pytest tests/test_schemas.py -v
```

## Future Enhancements

Planned schema additions:
- [x] Streaming availability data (Integrated via Watchmode)
- [ ] User reviews and ratings
- [ ] Similar movies/recommendations
- [ ] Trailer URLs
- [ ] Episode data for TV shows
- [ ] Behind-the-scenes content
- [ ] Social features (shared watchlists)

## References

- **Pydantic Documentation**: https://docs.pydantic.dev/
- **Schema Definition**: `cineman/schemas.py`
- **Schema Tests**: `tests/test_schemas.py`
- **API Integration**: `cineman/routes/api.py`
