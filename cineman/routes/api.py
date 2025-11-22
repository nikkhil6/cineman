from flask import Blueprint, request, jsonify, session, Response
from cineman.tools.tmdb import get_movie_poster_core
from cineman.tools.omdb import fetch_omdb_data_core
from cineman.models import db, MovieInteraction
from cineman.schemas import parse_movie_from_api, MovieRecommendation
from cineman.api_status import check_all_apis
from cineman.rate_limiter import get_gemini_rate_limiter
from cineman.metrics import get_metrics, update_rate_limit_metrics
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
import uuid
import time

bp = Blueprint("api", __name__)


def get_or_create_session_id():
    """Get or create a session ID for the current user."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


@bp.route("/movie/poster", methods=["GET"])
def movie_poster():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"status": "error", "error": "Missing title parameter."}), 400

    result = get_movie_poster_core(title)
    return jsonify(result)


@bp.route("/movie/facts", methods=["GET"])
def movie_facts():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"status": "error", "error": "Missing title parameter."}), 400

    result = fetch_omdb_data_core(title)
    return jsonify(result)


@bp.route("/movie", methods=["GET"])
def movie_combined():
    """
    GET /api/movie?title=Inception
    Combines TMDb poster lookup and OMDb facts into one payload.
    Prefers OMDb IMDb rating if available; falls back to TMDb vote_average.
    
    Returns data conforming to MovieRecommendation schema (with legacy format support).
    """
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"status": "error", "error": "Missing title parameter."}), 400

    tmdb = get_movie_poster_core(title)
    omdb = fetch_omdb_data_core(title)

    # Determine preferred rating
    rating = None
    rating_source = None
    note = None

    if omdb.get("status") == "success" and omdb.get("IMDb_Rating"):
        rating = omdb.get("IMDb_Rating")
        rating_source = "OMDb/IMDb"
    else:
        # If OMDb blocked or errored, note the status but don't expose error details
        if omdb.get("status") in ("forbidden", "error"):
            note = "OMDb service unavailable"
        # Try TMDb vote_average fallback
        if tmdb.get("status") == "success" and tmdb.get("vote_average") is not None:
            rating = tmdb.get("vote_average")
            rating_source = "TMDb"
        else:
            rating = None
            rating_source = None

    # Remove detailed error messages from external API responses before returning
    # Only include safe, non-sensitive fields
    tmdb_safe = {
        "status": tmdb.get("status"),
        "poster_url": tmdb.get("poster_url"),
        "title": tmdb.get("title"),
        "year": tmdb.get("year"),
        "vote_average": tmdb.get("vote_average"),
        "tmdb_id": tmdb.get("tmdb_id")
    }
    
    omdb_safe = {
        "status": omdb.get("status"),
        "Title": omdb.get("Title"),
        "Year": omdb.get("Year"),
        "Director": omdb.get("Director"),
        "IMDb_Rating": omdb.get("IMDb_Rating"),
        "Rotten_Tomatoes": omdb.get("Rotten_Tomatoes"),
        "Poster_URL": omdb.get("Poster_URL"),
        "imdbID": omdb.get("raw", {}).get("imdbID") if omdb.get("raw") else None
    }

    # Extract top-level fields for easier frontend access
    poster = tmdb_safe.get("poster_url") or omdb_safe.get("Poster_URL")
    
    # Convert rating to string if it's a float (TMDb fallback case)
    imdb_rating = omdb_safe.get("IMDb_Rating") or rating
    if isinstance(imdb_rating, (int, float)):
        imdb_rating = str(imdb_rating)
    
    rt_tomatometer = omdb_safe.get("Rotten_Tomatoes")
    
    # Build combined response (legacy format for backward compatibility)
    combined = {
        "query": title,
        "tmdb": tmdb_safe,
        "omdb": omdb_safe,
        "poster": poster,
        "rating": rating,
        "rating_source": rating_source,
        "note": note,
        "imdb_rating": imdb_rating,
        "rt_tomatometer": rt_tomatometer,
    }
    
    # Also include structured schema-validated data
    try:
        movie_schema = parse_movie_from_api(combined, source="combined")
        combined["schema"] = movie_schema.to_dict()
    except (ValidationError, Exception) as e:
        # If schema validation fails, log but don't break the response
        # (backward compatibility: legacy clients don't need the schema field)
        print(f"Schema validation warning for movie '{title}': {e}")
    
    return jsonify(combined)


@bp.route("/interaction", methods=["POST"])
def movie_interaction():
    """
    POST /api/interaction
    Handle like, dislike, and watchlist actions for movies.
    
    Expected JSON body:
    {
        "movie_title": "Inception",
        "movie_year": "2010",
        "movie_poster_url": "https://...",
        "director": "Christopher Nolan",
        "imdb_rating": "8.8",
        "action": "like" | "dislike" | "watchlist",
        "value": true | false
    }
    """
    session_id = get_or_create_session_id()
    data = request.get_json()
    
    if not data or 'movie_title' not in data or 'action' not in data:
        return jsonify({
            "status": "error", 
            "error": "Missing required fields: movie_title and action"
        }), 400
    
    movie_title = data.get('movie_title')
    action = data.get('action')
    value = data.get('value', True)
    
    # Validate action
    if action not in ['like', 'dislike', 'watchlist']:
        return jsonify({
            "status": "error",
            "error": "Invalid action. Must be 'like', 'dislike', or 'watchlist'"
        }), 400
    
    try:
        # Find or create interaction record
        interaction = MovieInteraction.query.filter_by(
            session_id=session_id,
            movie_title=movie_title
        ).first()
        
        if not interaction:
            interaction = MovieInteraction(
                session_id=session_id,
                movie_title=movie_title,
                movie_year=data.get('movie_year'),
                movie_poster_url=data.get('movie_poster_url'),
                director=data.get('director'),
                imdb_rating=data.get('imdb_rating')
            )
            db.session.add(interaction)
        
        # Update the appropriate field based on action
        if action == 'like':
            interaction.liked = value
            if value:  # If liking, remove dislike
                interaction.disliked = False
        elif action == 'dislike':
            interaction.disliked = value
            if value:  # If disliking, remove like
                interaction.liked = False
        elif action == 'watchlist':
            interaction.in_watchlist = value
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "interaction": interaction.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        # Log the actual error for debugging
        print(f"Error in movie_interaction: {e}")
        return jsonify({
            "status": "error",
            "error": "An error occurred while processing your request."
        }), 500


@bp.route("/interaction/<movie_title>", methods=["GET"])
def get_movie_interaction(movie_title):
    """
    GET /api/interaction/<movie_title>
    Get the current user's interaction status for a specific movie.
    """
    session_id = get_or_create_session_id()
    
    interaction = MovieInteraction.query.filter_by(
        session_id=session_id,
        movie_title=movie_title
    ).first()
    
    if interaction:
        return jsonify({
            "status": "success",
            "interaction": interaction.to_dict()
        })
    else:
        return jsonify({
            "status": "success",
            "interaction": None
        })


@bp.route("/watchlist", methods=["GET"])
def get_watchlist():
    """
    GET /api/watchlist
    Get all movies in the current user's watchlist.
    """
    session_id = get_or_create_session_id()
    
    watchlist = MovieInteraction.query.filter_by(
        session_id=session_id,
        in_watchlist=True
    ).order_by(MovieInteraction.created_at.desc()).all()
    
    return jsonify({
        "status": "success",
        "watchlist": [movie.to_dict() for movie in watchlist]
    })


@bp.route("/interactions", methods=["GET"])
def get_all_interactions():
    """
    GET /api/interactions
    Get all movie interactions (likes, dislikes, watchlist) for the current session.
    """
    session_id = get_or_create_session_id()
    
    interactions = MovieInteraction.query.filter_by(
        session_id=session_id
    ).order_by(MovieInteraction.created_at.desc()).all()
    
    return jsonify({
        "status": "success",
        "interactions": [interaction.to_dict() for interaction in interactions]
    })


@bp.route("/status", methods=["GET"])
def api_status():
    """
    GET /api/status
    Check the status of all external APIs (Gemini, TMDB, OMDB).
    
    Returns status information for each API service including:
    - status: "operational" | "degraded" | "error"
    - message: Human-readable status message
    - response_time: API response time in milliseconds
    """
    try:
        statuses = check_all_apis()
        return jsonify({
            "status": "success",
            "timestamp": int(time.time()),
            "services": statuses
        })
    except Exception as e:
        print(f"Error checking API status: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to check API status"
        }), 500


@bp.route("/session/timeout", methods=["GET"])
def session_timeout_info():
    """
    GET /api/session/timeout
    Get information about the current session timeout.
    
    Returns:
    - session_exists: Whether a valid session exists
    - timeout_seconds: Total session timeout in seconds (3600 = 1 hour)
    - remaining_seconds: Seconds remaining before session expires
    - last_accessed: ISO timestamp of last session access
    """
    from cineman.session_manager import get_session_manager
    
    session_id = session.get('session_id')
    session_manager = get_session_manager()
    
    if not session_id:
        return jsonify({
            "status": "success",
            "session_exists": False,
            "timeout_seconds": 3600,
            "remaining_seconds": 3600,
            "message": "No active session"
        })
    
    session_data = session_manager.peek_session(session_id)
    
    if not session_data:
        return jsonify({
            "status": "success",
            "session_exists": False,
            "timeout_seconds": 3600,
            "remaining_seconds": 3600,
            "message": "Session expired or not found"
        })
    
    # Calculate remaining time
    from datetime import datetime
    timeout_seconds = int(session_manager.session_timeout.total_seconds())
    elapsed = (datetime.now() - session_data.last_accessed).total_seconds()
    remaining = max(0, timeout_seconds - elapsed)
    
    return jsonify({
        "status": "success",
        "session_exists": True,
        "timeout_seconds": timeout_seconds,
        "remaining_seconds": int(remaining),
        "last_accessed": session_data.last_accessed.isoformat()
    })


@bp.route("/rate-limit", methods=["GET"])
def rate_limit_status():
    """
    GET /api/rate-limit
    Get current rate limit status for Gemini API.
    
    Returns:
    - status: Request status
    - usage: Current usage statistics including:
      - call_count: Number of calls made today
      - daily_limit: Maximum calls allowed per day
      - remaining: Number of calls remaining
      - reset_date: When the counter will reset (ISO format)
      - status: Rate limiter status ('active', 'unavailable', 'error')
    """
    try:
        rate_limiter = get_gemini_rate_limiter()
        usage_stats = rate_limiter.get_usage_stats()
        
        return jsonify({
            "status": "success",
            "usage": usage_stats
        })
    except Exception as e:
        print(f"Error getting rate limit status: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to get rate limit status"
        }), 500


@bp.route("/metrics", methods=["GET"])
def metrics():
    """
    GET /api/metrics
    Expose Prometheus metrics for monitoring.
    
    Returns metrics in Prometheus text format including:
    - HTTP request counts and durations
    - External API call counts and durations (TMDB, OMDB, Gemini)
    - Cache hit/miss rates
    - Movie validation statistics
    - Rate limiter usage
    - LLM invocation statistics
    - Session metrics
    
    Note: This endpoint does not expose sensitive information like API keys
    or user data. Only aggregated statistics are returned.
    """
    try:
        # Update rate limit metrics before generating output
        rate_limiter = get_gemini_rate_limiter()
        usage_stats = rate_limiter.get_usage_stats()
        update_rate_limit_metrics(
            usage_stats.get('call_count', 0),
            usage_stats.get('daily_limit', 0),
            usage_stats.get('remaining', 0)
        )
        
        # Generate and return metrics
        metrics_text, content_type = get_metrics()
        return Response(metrics_text, mimetype=content_type)
    except Exception as e:
        print(f"Error generating metrics: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to generate metrics"
        }), 500