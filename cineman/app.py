from flask import Flask, request, jsonify, render_template
from cineman.chain import get_recommendation_chain
import os

# Get the project root directory (parent of cineman package)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# Cache the chain instance globally (Phase 1 simplicity)
# In Phase 3, we would manage memory here.
try:
    movie_chain = get_recommendation_chain()
    print("🎬 Movie Recommendation Chain loaded successfully.")
except Exception as e:
    print(f"FATAL: Failed to load AI Chain: {e}")
    movie_chain = None  # Set to None to prevent calls

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

        # Invoke the LangChain Chain (your agent's logic)
        # Note: We must pass the input variable name expected by the chain: "user_input"
        agent_response = movie_chain.invoke({"user_input": user_message})
        
        # Return the response as JSON to the JavaScript frontend
        return jsonify({"response": agent_response})
    
    except Exception as e:
        print(f"Chat API Error: {e}")
        return jsonify({"response": "An unexpected error occurred while processing your request."}), 500

if __name__ == '__main__':
    # Run the server locally on http://127.0.0.1:5000
    # Note: Flask templates need a 'templates' folder.
    app.run(debug=True)

