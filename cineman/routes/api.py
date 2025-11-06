from flask import Blueprint, request, jsonify
from cineman.tools.tmdb import get_movie_poster_core
from cineman.tools.omdb import fetch_omdb_data_core

bp = Blueprint("api", __name__)


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
        # If OMDb blocked or errored, include note so UI can show message
        if omdb.get("status") in ("forbidden", "error"):
            note = {"omdb_status": omdb.get("status"), "omdb_error": omdb.get("error")}
        # Try TMDb vote_average fallback
        if tmdb.get("status") == "success" and tmdb.get("vote_average") is not None:
            rating = tmdb.get("vote_average")
            rating_source = "TMDb"
        else:
            rating = None
            rating_source = None

    combined = {
        "query": title,
        "tmdb": tmdb,
        "omdb": omdb,
        "rating": rating,
        "rating_source": rating_source,
        "note": note,
    }
    return jsonify(combined)