from flask import Blueprint, request, jsonify, session
from cineman.tools.tmdb import get_movie_poster_core
from cineman.tools.omdb import fetch_omdb_data_core
from cineman.models import db, MovieInteraction
from cineman.schemas import parse_movie_from_api, MovieRecommendation
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
import uuid

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

    # Determine poster URL (prefer TMDb, fallback to OMDb)
    poster = tmdb_safe.get("poster_url") or omdb_safe.get("Poster_URL")
    
    # Build combined response (legacy format for backward compatibility)
    combined = {
        "query": title,
        "tmdb": tmdb_safe,
        "omdb": omdb_safe,
        "poster": poster,
        "rating": rating,
        "rating_source": rating_source,
        "note": note,
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