# Place this as early as possible in cineman/app.py (before any AI/chain init)
import cineman.secret_helper as secret_helper
secret_helper.inject_gemini_key()

# Initialize structured logging early
from cineman.logging_config import get_logger, configure_structlog
configure_structlog()

from flask import Flask, request, jsonify, render_template, session
from cineman.session_manager import get_session_manager
from cineman.routes.api import bp as api_bp
from cineman.models import db
from cineman.rate_limiter import get_gemini_rate_limiter
from cineman.services.llm_service import llm_service
from cineman.metrics import (
    http_requests_total, http_request_duration_seconds,
    track_llm_invocation, track_rate_limit_exceeded,
    track_duplicate_recommendation
)


from cineman.logging_middleware import init_logging_middleware
from cineman.logging_context import set_session_id
from cineman.logging_metrics import track_phase
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

# Chain initialization is now handled by LLMService

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

# Helper functions moved to cineman.services.llm_service

# --- API Endpoint for Chat Communication ---
@app.route('/chat', methods=['POST'])
def chat():
    if not llm_service.is_available():
        logger.error("chat_request_failed", reason="AI service not initialized")
        return jsonify({"response": "Error: AI service failed to initialize. Please check API configuration."}), 503

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
        
        # Get chat history
        chat_history = session_data.get_chat_history(limit=10) # Last 10 messages
        # Note: LLMService now handles getting recommended movies from DB if needed contextually, 
        # but session_data cache is also useful. We pass just history to service.
        
        logger.info(
            "chat_context_loaded",
            history_count=len(chat_history)
        )
        
        # Delegate to LLM Service
        llm_start_time = time.time()
        try:
            result = llm_service.process_chat_request(user_message, chat_history, session_id)
            
            validated_response = result['response_text']
            new_movies = result['movies']
            validation_summary = result['validation']
            
            llm_duration = time.time() - llm_start_time
            track_llm_invocation(success=True, duration=llm_duration)
            
        except Exception as llm_error:
            llm_duration = time.time() - llm_start_time
            track_llm_invocation(success=False, duration=llm_duration)
            raise
        
        # Increment rate limiter counter after successful API call
        rate_limiter.increment()
        
        # Get updated remaining count after increment
        updated_stats = rate_limiter.get_usage_stats()
        
        # Add validated movies to session tracking
        recommended_movies = session_data.get_recommended_movies()
        if new_movies:
            # Check for duplicates before adding
            for movie in new_movies:
                title = movie.get('title')
                if title and title in recommended_movies:
                    track_duplicate_recommendation()
            movie_titles = [m.get('title') for m in new_movies if m.get('title')]
            session_data.add_recommended_movies(movie_titles)
            
            logger.info(
                "movies_recommended",
                count=len(new_movies),
                titles=movie_titles
            )
        
        # Add messages to session history
        session_data.add_message("user", user_message)
        session_data.add_message("assistant", validated_response)
        
        # Build response with validation info
        response_data = {
            "response": validated_response,
            "response_text": validated_response, # Support both keys
            "movies": new_movies,
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
    # Run the server locally
    init_db()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

