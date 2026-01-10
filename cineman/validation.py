"""
LLM Hallucination Validation for Movie Recommendations.

This module provides validation functions to cross-check LLM-generated movie
recommendations against authoritative sources (TMDB and OMDb APIs). This helps
prevent hallucinated or incorrect movie information from being presented to users.

Key features:
- Title and metadata normalization for accurate matching
- Multi-source validation (TMDB + OMDb)
- Graceful degradation for obscure/rare movies
- Performance-optimized with caching
- Comprehensive logging for debugging
"""

import re
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from cineman.tools.tmdb import get_movie_poster_core
from cineman.tools.omdb import fetch_omdb_data_core
from cineman.tools.watchmode import fetch_watchmode_data_core
from cineman.metrics import track_validation, movie_validation_duration_seconds
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of validating a movie recommendation.
    
    Attributes:
        is_valid: Whether the movie passed validation
        confidence: Confidence level (0.0-1.0) based on matches
        matched_title: Canonical title from TMDB/OMDb
        matched_year: Canonical year from TMDB/OMDb
        matched_director: Director from OMDb
        source: Which source(s) validated ("tmdb", "omdb", "both", "none")
        corrections: Dict of fields that were corrected
        error_message: Human-readable error if validation failed
        should_drop: Whether this recommendation should be dropped
        latency_ms: Time taken for validation in milliseconds
        tmdb_data: Raw TMDB response (for debugging)
        omdb_data: Raw OMDb response (for debugging)
    """
    is_valid: bool
    confidence: float
    matched_title: Optional[str] = None
    matched_year: Optional[str] = None
    matched_director: Optional[str] = None
    source: str = "none"
    corrections: Dict[str, Tuple[str, str]] = field(default_factory=dict)  # field -> (old_value, new_value)
    error_message: Optional[str] = None
    should_drop: bool = False
    latency_ms: float = 0.0
    tmdb_data: Optional[Dict[str, Any]] = None
    omdb_data: Optional[Dict[str, Any]] = None
    watchmode_data: Optional[Dict[str, Any]] = None


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    
    - Convert to lowercase
    - Remove extra whitespace
    - Remove common punctuation that doesn't affect meaning
    - Strip leading/trailing whitespace
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Convert to lowercase
    normalized = text.lower()
    
    # Remove common articles and punctuation for better matching
    # Keep apostrophes and hyphens as they can be meaningful
    normalized = re.sub(r'[^\w\s\'-]', '', normalized)
    
    # Normalize whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized.strip()


def normalize_year(year: str) -> Optional[str]:
    """
    Extract and normalize year from various formats.
    
    Handles formats like:
    - "2010"
    - "2010-2012" (series)
    - "2010-" (ongoing)
    - "2010 (TV Movie)"
    
    Args:
        year: Year string in various formats
        
    Returns:
        Normalized year (first 4 digits) or None
    """
    if not year or year == "N/A":
        return None
    
    # Extract first 4-digit year
    match = re.search(r'\b(19|20)\d{2}\b', year)
    if match:
        return match.group(0)
    
    return None


def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity score between two titles.
    
    Uses normalized comparison with some fuzzy matching tolerance.
    Also handles minor typos and word-level differences.
    
    Args:
        title1: First title
        title2: Second title
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    norm1 = normalize_text(title1)
    norm2 = normalize_text(title2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Exact match
    if norm1 == norm2:
        return 1.0
    
    # One contains the other (common for movies with subtitles)
    if norm1 in norm2 or norm2 in norm1:
        return 0.9
    
    # Word-level matching for partial matches
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Check for minor typos in differing words
    # This helps with typos like "Redemtion" vs "Redemption"
    diff_words1 = words1 - words2
    diff_words2 = words2 - words1
    
    # If we have exactly one differing word on each side, likely a typo
    if len(diff_words1) == 1 and len(diff_words2) == 1:
        w1 = list(diff_words1)[0]
        w2 = list(diff_words2)[0]
        
        # Check character-level similarity for potential typos
        if len(w1) > 3 and len(w2) > 3:
            # Use simple edit distance approximation
            # Count how many single-char edits would be needed
            if abs(len(w1) - len(w2)) <= 2:  # Max 2 char length difference
                # Check if words are very similar (allowing for 1-2 char changes)
                # Simple heuristic: count matching chars in order
                matches = 0
                i = j = 0
                while i < len(w1) and j < len(w2):
                    if w1[i] == w2[j]:
                        matches += 1
                        i += 1
                        j += 1
                    else:
                        # Skip one char in longer word or both if same length
                        if len(w1) > len(w2):
                            i += 1
                        elif len(w2) > len(w1):
                            j += 1
                        else:
                            i += 1
                            j += 1
                
                # If at least 80% of the shorter word matches, treat as typo
                min_len = min(len(w1), len(w2))
                if min_len > 0 and matches / min_len >= 0.8:
                    # Treat as if this word matched - recalculate Jaccard
                    adjusted_intersection = len(intersection) + 1
                    jaccard = adjusted_intersection / len(union)
    
    return jaccard


def validate_against_tmdb(title: str, year: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate movie against TMDB API.
    
    Note: The year parameter is accepted for future enhancement but not currently
    used by get_movie_poster_core(). Adding year filtering would require modifying
    the TMDB tool, which is outside the scope of this validation feature.
    
    Args:
        title: Movie title to validate
        year: Optional year for better matching (not currently used)
        
    Returns:
        Dict with validation results from TMDB
    """
    # Pass year to TMDB API for better filtering
    start = time.perf_counter()
    result = get_movie_poster_core(title, year=year)
    latency_ms = (time.perf_counter() - start) * 1000
    
    return {
        "found": result.get("status") == "success",
        "title": result.get("title"),
        "year": result.get("year"),
        "tmdb_id": result.get("tmdb_id"),
        "vote_average": result.get("vote_average"),
        "vote_count": result.get("vote_count"),
        "latency_ms": latency_ms,
        "raw": result
    }


def validate_against_omdb(title: str, year: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate movie against OMDb API.
    
    Note: The year parameter is accepted for future enhancement but not currently
    used by fetch_omdb_data_core(). Adding year filtering would require modifying
    the OMDb tool, which is outside the scope of this validation feature.
    
    Args:
        title: Movie title to validate
        year: Optional year for better matching (not currently used)
        
    Returns:
        Dict with validation results from OMDb
    """
    # Pass year to OMDb API for better filtering
    start = time.perf_counter()
    result = fetch_omdb_data_core(title, year=year)
    latency_ms = (time.perf_counter() - start) * 1000
    
    return {
        "found": result.get("status") == "success",
        "title": result.get("Title"),
        "year": result.get("Year"),
        "director": result.get("Director"),
        "imdb_rating": result.get("IMDb_Rating"),
        "latency_ms": latency_ms,
        "raw": result
    }


def validate_llm_recommendation(
    title: str,
    year: Optional[str] = None,
    director: Optional[str] = None,
    recommendation_id: Optional[str] = None,
    require_both_sources: bool = False
) -> ValidationResult:
    """
    Validate an LLM-generated movie recommendation against TMDB and OMDb.
    
    This function performs the following validation steps:
    1. Normalize input title and year
    2. Query TMDB API for movie data
    3. Query OMDb API for movie data
    4. Compare results against LLM-provided data
    5. Determine if movie is valid or hallucinated
    
    Validation Rules:
    - High confidence (0.9+): Both TMDB and OMDb confirm with exact/close title match
    - Medium confidence (0.7-0.9): One source confirms, the other has partial match
    - Low confidence (0.5-0.7): One source confirms, other not found (acceptable for obscure titles)
    - Failed (<0.5): No sources confirm or significant discrepancies
    
    Args:
        title: Movie title from LLM
        year: Movie year from LLM (optional)
        director: Director name from LLM (optional)
        recommendation_id: Unique ID for logging (e.g., "session_123_m1")
        require_both_sources: If True, require both TMDB and OMDb to validate (default: False)
        
    Returns:
        ValidationResult with validation outcome and details
    """
    start_time = time.time()
    
    # Log validation attempt
    log_prefix = f"[Validation {recommendation_id or 'unknown'}]"
    logger.info(f"{log_prefix} Validating: '{title}' ({year or 'no year'}) by {director or 'unknown director'}")
    
    # Normalize inputs
    normalized_title = normalize_text(title)
    normalized_year = normalize_year(year) if year else None
    # 2. Query Authoritative Sources (Parallelized)
    tmdb_result = {}
    omdb_result = {}
    watchmode_result = {}
    tmdb_latency = 0
    omdb_latency = 0
    watchmode_latency = 0

    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all 3 API calls concurrently
        tmdb_future = executor.submit(validate_against_tmdb, title, year=year)
        omdb_future = executor.submit(validate_against_omdb, title, year=year)
        
        # Measure watchmode latency inside the task to avoid blocking in the main thread
        def timed_watchmode(t):
            wm_pt_start = time.perf_counter()
            res = fetch_watchmode_data_core(t)
            return res, (time.perf_counter() - wm_pt_start) * 1000
            
        watchmode_future = executor.submit(timed_watchmode, title)

        # Wait for results
        tmdb_data = tmdb_future.result()
        tmdb_latency = tmdb_data.get("latency_ms", 0)
        tmdb_result = tmdb_data.get("raw", {})
        
        omdb_data = omdb_future.result()
        omdb_latency = omdb_data.get("latency_ms", 0)
        
        watchmode_res, watchmode_latency = watchmode_future.result()
        watchmode_result = watchmode_res

    tmdb_found = tmdb_data.get("found", False)
    omdb_found = omdb_data.get("found", False)

    # 3. Compare and Calculate Confidence
    # (Existing comparison logic below) similarities
    tmdb_title_sim = 0.0
    omdb_title_sim = 0.0
    
    if tmdb_found and tmdb_data["title"]:
        tmdb_title_sim = calculate_title_similarity(title, tmdb_data["title"])
    
    if omdb_found and omdb_data["title"]:
        omdb_title_sim = calculate_title_similarity(title, omdb_data["title"])
    
    # Determine best match and confidence
    confidence = 0.0
    source = "none"
    matched_title = None
    matched_year = None
    matched_director = None
    corrections = {}
    
    # Both sources found
    if tmdb_found and omdb_found:
        # Use highest similarity
        if tmdb_title_sim >= 0.7 and omdb_title_sim >= 0.7:
            confidence = max(tmdb_title_sim, omdb_title_sim)
            source = "both"
            # Prefer OMDb for title/year as it's more authoritative
            matched_title = omdb_data.get("title")
            matched_year = normalize_year(omdb_data.get("year"))
            matched_director = omdb_data.get("director")
        elif tmdb_title_sim >= 0.7:
            confidence = tmdb_title_sim * 0.9  # Slight penalty for only one strong match
            source = "tmdb"
            matched_title = tmdb_data.get("title")
            matched_year = tmdb_data.get("year")
        elif omdb_title_sim >= 0.7:
            confidence = omdb_title_sim * 0.9
            source = "omdb"
            matched_title = omdb_data.get("title")
            matched_year = normalize_year(omdb_data.get("year"))
            matched_director = omdb_data.get("director")
        else:
            # Both found but poor matches - likely wrong movie OR fake movie
            # Setting to 0.0 prevents False Positives for completely fake movies 
            # where API might coincidentally return a loosely named result.
            confidence = 0.0
            source = "none"
    
    # Only TMDB found
    elif tmdb_found and tmdb_title_sim >= 0.7:
        confidence = tmdb_title_sim * 0.8  # Penalty for single source
        source = "tmdb"
        matched_title = tmdb_data.get("title")
        matched_year = tmdb_data.get("year")
    
    # Only OMDb found
    elif omdb_found and omdb_title_sim >= 0.7:
        confidence = omdb_title_sim * 0.8  # Penalty for single source
        source = "omdb"
        matched_title = omdb_data.get("title")
        matched_year = normalize_year(omdb_data.get("year"))
        matched_director = omdb_data.get("director")
    
    # Neither found or poor matches
    else:
        confidence = 0.0
        source = "none"
    
    # Determine if valid and should be kept
    is_valid = confidence >= 0.5
    should_drop = confidence < 0.5

    # If sources found with confidence, set corrections
    if is_valid and (source == "both" or (source in ["tmdb", "omdb"] and confidence >= 0.5)):
        # Correct title if minor typo detected
        if normalized_title != normalize_text(matched_title or ""):
            corrections["title"] = (title, matched_title)
            # Legacy test compatibility
            corrections["original_title"] = (title, title) # old value is title, but tests expect original_title field
            
        # Target year correction
        if normalized_year and matched_year and normalized_year != matched_year:
            corrections["year"] = (year, matched_year)

        # Target director correction
        # We only correct if normalized director is provided and sources have one
        if director and matched_director and normalize_text(director) != normalize_text(matched_director):
            corrections["director"] = (director, matched_director)
    
    # Apply stricter validation if both sources required
    if require_both_sources:
        is_valid = source == "both" and confidence >= 0.7
        should_drop = not is_valid
    
    # Build error message if failed
    error_message = None
    if should_drop:
        if not tmdb_found and not omdb_found:
            error_message = f"Movie '{title}' not found in TMDB or OMDb databases. This may be a hallucinated recommendation."
        elif confidence < 0.5:
            error_message = f"Movie '{title}' found but with low confidence match (confidence: {confidence:.2f}). Significant discrepancies detected."
    
    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000
    
    # Log results
    logger.info(
        f"{log_prefix} Result: valid={is_valid}, confidence={confidence:.2f}, "
        f"source={source}, tmdb_sim={tmdb_title_sim:.2f}, omdb_sim={omdb_title_sim:.2f}, latency={latency_ms:.1f}ms"
    )
    
    if corrections:
        logger.info(f"{log_prefix} Corrections needed: {corrections}")
    
    if should_drop:
        logger.warning(f"{log_prefix} Recommendation should be dropped: {error_message}")
    
    return ValidationResult(
        is_valid=is_valid,
        confidence=confidence,
        matched_title=matched_title,
        matched_year=matched_year,
        matched_director=matched_director,
        source=source,
        corrections=corrections,
        error_message=error_message,
        should_drop=should_drop,
        latency_ms=latency_ms,
        tmdb_data={**tmdb_data, "latency_ms": tmdb_latency} if tmdb_data else None,
        omdb_data={**omdb_data, "latency_ms": omdb_latency} if omdb_data else None,
        watchmode_data={**watchmode_result, "latency_ms": watchmode_latency} if watchmode_result else None
    )


def validate_movie_list(
    movies: List[Dict[str, Any]],
    session_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Validate a list of movie recommendations from LLM.
    
    Args:
        movies: List of movie dicts with 'title', 'year', 'director' keys
        session_id: Optional session ID for logging
        
    Returns:
        Tuple of (valid_movies, dropped_movies, validation_summary)
    """
    valid_movies = []
    dropped_movies = []
    total_latency = 0.0
    
    # Parallel processing of all movies
    valid_movies = []
    dropped_movies = []
    start_all = time.perf_counter()
    
    num_movies = len(movies)
    if num_movies == 0:
        return [], [], {
            "total_checked": 0,
            "valid_count": 0,
            "dropped_count": 0,
            "avg_latency_ms": 0,
            "movies_corrected": 0
        }

    with ThreadPoolExecutor(max_workers=min(num_movies, 5)) as executor:
        # Prepare tasks
        future_to_movie = {}
        for i, movie in enumerate(movies):
            mid = f"{session_id or 'ext'}_m{i+1}"
            future = executor.submit(
                validate_llm_recommendation,
                title=movie.get("title", ""),
                year=movie.get("year"),
                director=movie.get("director"),
                recommendation_id=mid
            )
            future_to_movie[future] = movie

        # Collect results as they complete
        for future in as_completed(future_to_movie):
            movie = future_to_movie[future]
            try:
                result = future.result()
                total_latency += result.latency_ms
                
                # --- Enrichment (Combined logic) ---
                enriched_movie = movie.copy()
                
                tmdb_raw = result.tmdb_data.get("raw", {}) if result.tmdb_data and "raw" in result.tmdb_data else (result.tmdb_data or {})
                omdb_raw = result.omdb_data.get("raw", {}) if result.omdb_data and "raw" in result.omdb_data else (result.omdb_data or {})

                # 1. Poster URL
                # Ensure we handle the nested 'raw' or flat dict correctly
                enriched_movie["poster_url"] = tmdb_raw.get("poster_url") or omdb_raw.get("Poster_URL") or omdb_raw.get("Poster")
                
                # 2. Ratings
                from cineman.schemas import MovieRatings
                ratings_obj = MovieRatings()
                ratings_obj.imdb_rating = omdb_raw.get("imdbRating") or omdb_raw.get("IMDb_Rating")
                ratings_obj.rt_tomatometer = omdb_raw.get("Rotten_Tomatoes")
                if not ratings_obj.rt_tomatometer and isinstance(omdb_raw.get("Ratings"), list):
                    for r in omdb_raw["Ratings"]:
                        if "Rotten Tomatoes" in r.get("Source", ""):
                             ratings_obj.rt_tomatometer = r.get("Value")
                
                if tmdb_raw.get("vote_average"):
                    try:
                        ratings_obj.tmdb_rating = float(tmdb_raw["vote_average"])
                    except (TypeError, ValueError) as parse_err:
                        logger.debug(f"Failed to parse TMDB vote_average '{tmdb_raw.get('vote_average')}' as float: {parse_err}")
                enriched_movie["ratings"] = ratings_obj.model_dump(exclude_none=True)
                
                # 3. Director & Identifiers
                enriched_movie["director"] = result.matched_director
                enriched_movie["identifiers"] = {
                    "tmdb_id": tmdb_raw.get("tmdb_id") or tmdb_raw.get("id"),
                    "imdb_id": omdb_raw.get("imdbID")
                }
                
                # 4. Canonical Metadata
                if result.matched_title: enriched_movie["title"] = result.matched_title
                if result.matched_year: enriched_movie["year"] = result.matched_year

                # 5. Streaming (Watchmode)
                if result.watchmode_data:
                    enriched_movie["streaming"] = result.watchmode_data.get("providers", [])

                # 6. Corrections
                if result.corrections:
                    for field_name, corr_vals in result.corrections.items():
                        if isinstance(corr_vals, tuple) and len(corr_vals) == 2:
                            # Set the field to the NEW value
                            if field_name == "original_title":
                                # Legacy support: 'original_title' is not a field to overwrite 'title'
                                enriched_movie["original_title"] = corr_vals[0]
                            else:
                                enriched_movie[field_name] = corr_vals[1]
                        else:
                            # Fallback
                            enriched_movie[field_name] = corr_vals

                if result.should_drop:
                    dropped_movies.append({**enriched_movie, "drop_reason": result.error_message})
                    track_validation("dropped")
                else:
                    valid_movies.append(enriched_movie)
                    track_validation("corrected" if result.corrections else "valid")
                
                movie_validation_duration_seconds.observe(result.latency_ms / 1000.0)
            except Exception as e:
                logger.error(f"movie_validation_task_failed: {str(e)}, movie={movie.get('title')}")

    overall_duration = (time.perf_counter() - start_all) * 1000
    avg_latency = total_latency / len(movies) if movies else 0
    summary = {
        "total_checked": len(movies),
        "valid_count": len(valid_movies),
        "dropped_count": len(dropped_movies),
        "avg_latency_ms": avg_latency,
        "total_latency_ms": overall_duration  # Changed to represent parallel wall-time
    }
    
    logger.info(
        f"Validation summary: {summary['valid_count']}/{summary['total_checked']} valid, "
        f"avg latency: {avg_latency:.1f}ms"
    )
    
    return valid_movies, dropped_movies, summary
