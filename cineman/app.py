from flask import Flask, request, jsonify, render_template, session
from cineman.chain import get_recommendation_chain, build_session_context, format_chat_history
from cineman.session_manager import get_session_manager
from cineman.routes.api import bp as api_bp
from cineman.models import db
import os
import json

# Get the project root directory (parent of cineman package)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

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
        print("⚠️  WARNING: Using temporary SQLite database. Data will not persist between deployments.")
        print("⚠️  For production, configure Cloud SQL and set DATABASE_URL environment variable.")
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
    print("✅ Database tables initialized successfully.")
except Exception as e:
    print(f"⚠️  Warning: Could not initialize database tables on import: {e}")
    print("⚠️  Tables will be created on first request if needed.")

# Cache the chain instance globally
try:
    movie_chain = get_recommendation_chain()
    print("🎬 Movie Recommendation Chain loaded successfully.")
except Exception as e:
    print(f"FATAL: Failed to load AI Chain: {e}")
    movie_chain = None  # Set to None to prevent calls

# Initialize session manager for chat history and movie tracking
session_manager = get_session_manager()
print("📋 Session Manager initialized successfully.")

# Ensure database tables are created before first request (fallback if import-time init failed)
@app.before_request
def ensure_db_initialized():
    """Ensure database tables exist before handling requests."""
    if not hasattr(app, '_db_initialized'):
        try:
            with app.app_context():
                db.create_all()
            app._db_initialized = True
            print("✅ Database tables verified/created on first request.")
        except Exception as e:
            print(f"⚠️  Could not initialize database tables: {e}")

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
        print(f"Could not extract movie titles: {e}")
    
    return []

# --- API Endpoint for Chat Communication ---
@app.route('/chat', methods=['POST'])
def chat():
    if not movie_chain:
        return jsonify({"response": "Error: AI service failed to initialize."}), 503

    try:
        # Get the user's message from the JSON request
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"response": "Please type a movie request."}), 400

        # Get or create session for chat history
        session_id = session.get('session_id')
        session_id, session_data = session_manager.get_or_create_session(session_id)
        session['session_id'] = session_id
        
        # Get chat history and recommended movies from session
        chat_history = session_data.get_chat_history(limit=10)  # Last 10 messages
        recommended_movies = session_data.get_recommended_movies()
        
        # Build session context to avoid repeating recommendations
        session_context = build_session_context(chat_history, recommended_movies)
        
        # Append session context to user message if there are previous recommendations
        enhanced_user_message = user_message
        if session_context:
            enhanced_user_message = user_message + session_context
        
        # Format chat history for LangChain
        formatted_history = format_chat_history(chat_history[-6:])  # Last 3 exchanges
        
        # Invoke the LangChain Chain with chat history
        agent_response = movie_chain.invoke({
            "user_input": enhanced_user_message,
            "chat_history": formatted_history
        })
        
        # Extract movie titles from response and add to session
        new_movies = extract_movie_titles_from_response(agent_response)
        if new_movies:
            session_data.add_recommended_movies(new_movies)
        
        # Add messages to session history
        session_data.add_message("user", user_message)
        session_data.add_message("assistant", agent_response)
        
        # Return the response as JSON to the JavaScript frontend
        return jsonify({"response": agent_response, "session_id": session_id})
    
    except Exception as e:
        print(f"Chat API Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "An unexpected error occurred while processing your request."}), 500

# --- API Endpoint to clear/reset session ---
@app.route('/session/clear', methods=['POST'])
def clear_session():
    """Clear the current session and start fresh."""
    try:
        session_id = session.get('session_id')
        if session_id:
            session_manager.delete_session(session_id)
        session.clear()
        return jsonify({"status": "success", "message": "Session cleared successfully."})
    except Exception as e:
        print(f"Session clear error: {e}")
        return jsonify({"status": "error", "message": "Failed to clear session. Please try again."}), 500

if __name__ == '__main__':
    # Run the server locally on http://127.0.0.1:5000
    # Note: Flask templates need a 'templates' folder.
    init_db()
    app.run(debug=True)

