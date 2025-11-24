# Place this as early as possible in cineman/app.py (before any AI/chain init)
import cineman.secret_helper as secret_helper
secret_helper.inject_gemini_key()

# Initialize structured logging early
from cineman.logging_config import get_logger, configure_structlog
configure_structlog()

from flask import Flask, request, jsonify, render_template, session
from cineman.chain import get_recommendation_chain, build_session_context, format_chat_history
from cineman.session_manager import get_session_manager
from cineman.routes.api import bp as api_bp
from cineman.models import db
from cineman.rate_limiter import get_gemini_rate_limiter
from cineman.metrics import (
    http_requests_total, http_request_duration_seconds,
    track_llm_invocation, track_rate_limit_exceeded,
    track_duplicate_recommendation, update_active_sessions
)


from cineman.logging_middleware import init_logging_middleware
from cineman.logging_context import set_session_id, bind_context
from cineman.logging_metrics import track_phase, log_llm_usage
import os
import json
import time

# Configure structured logger for app
logger = get_logger(__name__)

# Get the project root directory (parent of cineman package)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# Initialize logging middleware
init_logging_middleware(app)

# Configure secret key for sessions (unified for both features)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Configure database for movie interactions
# In GCP, use Cloud SQL or fallback to in-memory SQLite
# In local development, use file-based SQLite
if os.getenv('GAE_ENV', '').startswith('standard') or os.getenv('CLOUD_RUN_SERVICE'):
    # Running on GCP - use in-memory SQLite or Cloud SQL
    # For Cloud SQL, set DATABASE_URL environment variable
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Use Cloud SQL (PostgreSQL/MySQL)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback to in-memory SQLite on GCP (data not persisted between instances)
        # Note: This is for testing. For production, use Cloud SQL.
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/cineman.db'
        logger.warning(
            "database_config_warning",
            message="Using temporary SQLite database. Data will not persist between deployments.",
            recommendation="Configure Cloud SQL and set DATABASE_URL environment variable for production"
        )
else:
    # Local development - use file-based SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cineman.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

app.register_blueprint(api_bp, url_prefix="/api")

# Initialize database tables
def init_db():
    """Initialize database tables."""
    with app.app_context():
        db.create_all()

# Initialize database when module is imported (needed for Gunicorn)
# Wrap in try-except to handle potential issues during import
try:
    init_db()
    logger.info("database_initialized", message="Database tables initialized successfully")
except Exception as e:
    logger.warning(
        "database_init_delayed",
        message="Could not initialize database tables on import",
        error=str(e),
        fallback="Tables will be created on first request if needed"
    )

# Cache the chain instance globally
try:
    movie_chain = get_recommendation_chain()
    logger.info("chain_initialized", message="Movie Recommendation Chain loaded successfully")
except Exception as e:
    logger.error("chain_init_failed", message="Failed to load AI Chain", error=str(e))
    movie_chain = None  # Set to None to prevent calls

# Initialize session manager for chat history and movie tracking
session_manager = get_session_manager()
logger.info("session_manager_initialized", message="Session Manager initialized successfully")

# Ensure database tables are created before first request (fallback if import-time init failed)
@app.before_request
def ensure_db_initialized():
    """Ensure database tables exist before handling requests."""
    if not hasattr(app, '_db_initialized'):
        try:
            with app.app_context():
                db.create_all()
            app._db_initialized = True
            logger.info("database_verified", message="Database tables verified/created on first request")
        except Exception as e:
            logger.error("database_verification_failed", error=str(e))

# Middleware to track HTTP request metrics
@app.before_request
def before_request_metrics():
    """Store request start time for duration tracking."""
    request._start_time = time.time()

@app.after_request
def after_request_metrics(response):
    """Track HTTP request metrics after each request."""
    if hasattr(request, '_start_time'):
        duration = time.time() - request._start_time
        # Get endpoint or use path
        endpoint = request.endpoint or request.path
        method = request.method
        status = response.status_code
        
        # Track metrics
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response

# --- Health Check Endpoint (for Render) ---
@app.route('/health')
def health():
    """Health check endpoint for deployment monitoring."""
    return jsonify({"status": "healthy", "service": "cineman"}), 200

# --- Route to serve the HTML chat interface ---
@app.route('/')
def index():
    # Renders the HTML template containing the chat interface
    return render_template('index.html')

# Helper function to extract movie titles from the response
def extract_movie_titles_from_response(response: str) -> list:
    """Extract movie titles from the AI response JSON manifest."""
    try:
        # Find JSON at the end of response
        json_start = response.rfind('\n\n{')
        if json_start == -1:
            json_start = response.rfind('{')
        
        if json_start != -1:
            json_str = response[json_start:].strip()
            if json_str.startswith('\n\n'):
                json_str = json_str[2:]
            
            manifest = json.loads(json_str)
            if 'movies' in manifest and isinstance(manifest['movies'], list):
                return [movie.get('title', '') for movie in manifest['movies'] if movie.get('title')]
    except (json.JSONDecodeError, Exception) as e:
        logger.debug("extract_titles_failed", error=str(e))
    
    return []


def extract_and_validate_movies(response: str, session_id: str = None) -> tuple:
    """
    Extract movies from LLM response and validate them against TMDB/OMDb.
    
    Args:
        response: LLM response text containing JSON manifest
        session_id: Session ID for logging
        
    Returns:
        Tuple of (validated_response, movie_titles, validation_summary)
    """
    from cineman.validation import validate_movie_list
    
    try:
        # Find JSON at the end of response
        json_start = response.rfind('\n\n{')
        if json_start == -1:
            json_start = response.rfind('{')
        
        if json_start == -1:
            # No JSON manifest found - likely conversational response
            return response, [], None
        
        # Split response into text part and JSON part
        text_part = response[:json_start].strip()
        json_str = response[json_start:].strip()
        if json_str.startswith('\n\n'):
            json_str = json_str[2:]
        
        # Parse JSON manifest
        manifest = json.loads(json_str)
        if 'movies' not in manifest or not isinstance(manifest['movies'], list):
            return response, [], None
        
        movies = manifest['movies']
        if not movies:
            return response, [], None
        
        # Validate movies
        valid_movies, dropped_movies, summary = validate_movie_list(movies, session_id)
        
        # Build validation message if there were drops or corrections
        validation_notes = []
        
        if dropped_movies:
            dropped_titles = [m.get('title', 'Unknown') for m in dropped_movies]
            validation_notes.append(
                f"\n\n**Note:** {len(dropped_movies)} recommendation(s) were filtered out because "
                f"they could not be verified in movie databases: {', '.join(dropped_titles)}. "
                f"This helps ensure all recommendations are real, accurate movies."
            )
        
        # Count corrections
        corrected_count = sum(1 for m in valid_movies if m.get('validation', {}).get('corrections'))
        if corrected_count > 0:
            validation_notes.append(
                f"\n**Note:** {corrected_count} movie detail(s) were automatically corrected "
                f"to match official database records."
            )
        
        # Rebuild manifest with only valid movies
        updated_manifest = {"movies": valid_movies}
        updated_json = json.dumps(updated_manifest, indent=2)
        
        # Combine text part with updated manifest and validation notes
        validated_response = text_part
        if validation_notes:
            validated_response += '\n' + ''.join(validation_notes)
        validated_response += '\n\n' + updated_json
        
        # Extract titles for tracking
        movie_titles = [m.get('title', '') for m in valid_movies if m.get('title')]
        
        return validated_response, movie_titles, summary
        
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error in extract_and_validate_movies: {e}", exc_info=True)
        # Return original response on error
        return response, extract_movie_titles_from_response(response), None

# --- API Endpoint for Chat Communication ---
@app.route('/chat', methods=['POST'])
def chat():
    if not movie_chain:
        logger.error("chat_request_failed", reason="AI service not initialized")
        return jsonify({"response": "Error: AI service failed to initialize."}), 503

    try:
        # Get the user's message from the JSON request
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            logger.info("chat_request_rejected", reason="empty_message")
            return jsonify({"response": "Please type a movie request."}), 400

        # Check rate limit before making API call
        rate_limiter = get_gemini_rate_limiter()
        allowed, remaining, error_message = rate_limiter.check_limit()
        
        if not allowed:
            # Track rate limit exceeded event
            track_rate_limit_exceeded()
            logger.warning("rate_limit_exceeded", remaining_calls=0)
            # Rate limit exceeded - return graceful error message
            return jsonify({
                "response": f"🎬 **Daily API Limit Reached**\n\n{error_message}\n\n"
                           "In the meantime, you can:\n"
                           "- Browse your watchlist for movies you've saved\n"
                           "- Review previously recommended movies in this session\n"
                           "- Come back tomorrow for fresh recommendations!\n\n"
                           "Thank you for understanding! 🙏",
                "rate_limit_exceeded": True,
                "remaining_calls": 0
            }), 429

        # Get or create session for chat history
        session_id = session.get('session_id')
        session_id, session_data = session_manager.get_or_create_session(session_id)
        session['session_id'] = session_id
        
        # Bind session_id to logging context
        set_session_id(session_id)
        
        # Get chat history and recommended movies from session
        chat_history = session_data.get_chat_history(limit=10)  # Last 10 messages
        recommended_movies = session_data.get_recommended_movies()
        
        logger.info(
            "chat_context_loaded",
            history_count=len(chat_history),
            recommended_count=len(recommended_movies)
        )
        
        # Build session context to avoid repeating recommendations
        session_context = build_session_context(chat_history, recommended_movies)
        
        # Append session context to user message if there are previous recommendations
        enhanced_user_message = user_message
        if session_context:
            enhanced_user_message = user_message + session_context
        
        # Format chat history for LangChain
        formatted_history = format_chat_history(chat_history[-6:])  # Last 3 exchanges
        
        # Invoke the LangChain Chain with chat history and track duration
        llm_start_time = time.time()
        try:
            agent_response = movie_chain.invoke({
                "user_input": enhanced_user_message,
                "chat_history": formatted_history
            })
            llm_duration = time.time() - llm_start_time
            track_llm_invocation(success=True, duration=llm_duration)
        except Exception as llm_error:
            llm_duration = time.time() - llm_start_time
            track_llm_invocation(success=False, duration=llm_duration)
            raise
        
        # Log LLM call (Note: Gemini API doesn't always return token counts in response)
        logger.info(
            "llm_call_completed",
            model="gemini-2.5-flash",
            duration_ms=round(llm_duration * 1000, 2),
            response_length=len(agent_response) if agent_response else 0
        )
        
        # Increment rate limiter counter after successful API call
        rate_limiter.increment()
        
        # Get updated remaining count after increment
        updated_stats = rate_limiter.get_usage_stats()
        
        logger.info(
            "rate_limit_updated",
            call_count=updated_stats.get('call_count', 0),
            remaining=updated_stats.get('remaining', 0)
        )
        
        # Validate movie recommendations if present in response
        with track_phase("movie_validation", session_id=session_id):
            validated_response, new_movies, validation_summary = extract_and_validate_movies(
                agent_response, 
                session_id
            )
        
        # Add validated movies to session tracking
        if new_movies:
            # Check for duplicates before adding
            for movie in new_movies:
                if movie in recommended_movies:
                    track_duplicate_recommendation()
            session_data.add_recommended_movies(new_movies)
            logger.info(
                "movies_recommended",
                count=len(new_movies),
                titles=new_movies
            )
        
        # Add messages to session history (store validated response)
        session_data.add_message("user", user_message)
        session_data.add_message("assistant", validated_response)
        
        # Build response with validation info
        response_data = {
            "response": validated_response, 
            "session_id": session_id,
            "remaining_calls": updated_stats['remaining']
        }
        
        # Add validation metrics if available
        if validation_summary:
            response_data["validation"] = {
                "checked": validation_summary["total_checked"],
                "valid": validation_summary["valid_count"],
                "dropped": validation_summary["dropped_count"],
                "avg_latency_ms": round(validation_summary["avg_latency_ms"], 1)
            }
            
            logger.info(
                "validation_completed",
                total_checked=validation_summary["total_checked"],
                valid_count=validation_summary["valid_count"],
                dropped_count=validation_summary["dropped_count"],
                avg_latency_ms=round(validation_summary["avg_latency_ms"], 1)
            )
        
        logger.info("chat_request_completed", response_length=len(validated_response))
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error("chat_request_failed", error=str(e), exc_info=True)
        return jsonify({"response": "An unexpected error occurred while processing your request."}), 500

# --- API Endpoint to clear/reset session ---
@app.route('/session/clear', methods=['POST'])
def clear_session():
    """Clear the current session and start fresh."""
    try:
        session_id = session.get('session_id')
        if session_id:
            session_manager.delete_session(session_id)
            logger.info("session_cleared", session_id=session_id)
        session.clear()
        return jsonify({"status": "success", "message": "Session cleared successfully."})
    except Exception as e:
        logger.error("session_clear_failed", error=str(e))
        return jsonify({"status": "error", "message": "Failed to clear session. Please try again."}), 500

if __name__ == '__main__':
    # Run the server locally on http://127.0.0.1:5000
    # Note: Flask templates need a 'templates' folder.
    init_db()
    app.run(debug=True)

