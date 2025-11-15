# 🎬 Cineman - AI Movie Recommender

An intelligent movie recommendation agent powered by Google Gemini AI (via LangChain) and integrated with The Movie Database (TMDB) and Open Movie Database (OMDB) APIs. Get personalized, conversational movie recommendations through a beautiful web interface.

## Features

### Core Features
- 🤖 **AI-Powered Recommendations**: Conversational movie recommendations using Google Gemini AI
- 🎯 **The Cinephile Agent**: Expert AI persona that provides curated movie suggestions
- 🎨 **Interactive Web Interface**: Beautiful Flask-based chat interface for seamless interaction
- 🎬 **Movie Data Integration**: 
  - TMDB API for movie posters and metadata
  - OMDb API for ratings, directors, and additional movie facts
- 🔧 **LangChain Tools**: Extensible tool system for movie data retrieval
- ✅ **Dependency Verification**: Built-in script to verify all dependencies are installed

### User Interaction Features
- 👍👎 **Like/Dislike System**: Express your opinion on recommended movies with simple thumbs up/down buttons
- 📋 **Watchlist Management**: Save movies to watch later and access them anytime from the watchlist modal
- 💾 **Session-Based Storage**: Your preferences (likes, dislikes, watchlist) are stored throughout your session using SQLite
- 🎴 **Interactive Flip Cards**: Click movie posters to flip and see full details with smooth 3D animation
- 📱 **Mobile-Optimized**: Swipe gestures for browsing movies on mobile devices
- 🎯 **Modal View**: Flipped cards expand to center with blurred background for enhanced readability

### Session Management & Conversation Features
- 🗨️ **Natural Conversations**: Engage in meaningful discussions about movies, directors, genres, and themes
- 🤖 **Intelligent Mode Switching**: AI automatically switches between conversational and recommendation modes
- 🧠 **Conversation Memory**: AI remembers previous recommendations to avoid duplicates
- 💬 **Chat History Tracking**: Maintains conversation context across messages
- 🎬 **Movie Tracking**: Tracks all recommended movies in your session
- 🔄 **New Session Button**: Clear history and start fresh anytime
- 🎭 **Creative Recommendations**: Enhanced AI creativity (temperature 1.2) for varied suggestions
- 💭 **Ask Questions**: Discuss movie themes, directors, trivia, and get expert insights
- 🔁 **Provide Feedback**: Share your thoughts on recommendations and get refined suggestions

### Deployment Options
- ☁️ **Google Cloud Platform**: Deploy to App Engine or Cloud Run with automated workflows
- 🐳 **Docker Support**: Containerized deployment ready for any platform
- 🚀 **CI/CD Ready**: GitHub Actions workflows for automated deployment

## Architecture

The application uses a modular architecture:
- **Flask Web Server**: Serves the chat interface and handles API requests
- **LangChain Chain**: Orchestrates the AI recommendation workflow
- **Google Gemini AI**: Powers the conversational recommendation engine
- **Movie Tools**: TMDB and OMDb integrations for real-time movie data

## Setup

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- TMDB API key ([Get one here](https://www.themoviedb.org/settings/api))
- OMDb API key ([Get one here](http://www.omdbapi.com/apikey.aspx))

### Installation

1. **Clone or navigate to this repository:**
```bash
cd cineman
```

2. **Create a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Verify installation:**
```bash
python scripts/verify_dependencies.py
```

5. **Set environment variables:**

Create a `.env` file in the project root or export them in your shell:
```bash
export GEMINI_API_KEY=your_gemini_api_key
export TMDB_API_KEY=your_tmdb_api_key
export OMDB_API_KEY=your_omdb_api_key
```

Or create a `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key
TMDB_API_KEY=your_tmdb_api_key
OMDB_API_KEY=your_omdb_api_key
```

## Usage

### Running the Application

1. **Activate the virtual environment:**
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Start the Flask server:**
```bash
python run.py
```

Or alternatively:
```bash
python -m cineman.app
```

3. **Open your browser:**
Navigate to `http://127.0.0.1:5000` to access the chat interface

### Using the Chat Interface

#### Conversational Mode
CineMan can engage in natural conversations about movies:
- **Ask questions**: "What makes Christopher Nolan such a great director?"
- **Discuss movies**: "Tell me about the themes in The Matrix"
- **Share preferences**: "I really enjoy movies with complex plots"
- **Get insights**: "What's the difference between sci-fi and fantasy films?"
- **Provide feedback**: "I really liked that suggestion, but I've seen it already"

#### Recommendation Mode
When you're ready for recommendations, just ask:
- **Request movies**: "Recommend some sci-fi movies"
- **Be specific**: "Suggest thrillers with plot twists"
- **Get suggestions**: "What should I watch tonight?"

#### Interacting with Recommendations
1. **View movie posters** - Each recommendation appears as an interactive poster card with hover effects
2. **Click to flip** - Click anywhere on a poster to flip it with 3D animation and see full details
3. **View detailed information** - Flipped cards show:
   - Movie poster on the left
   - Title, year, director, and IMDB rating
   - The Quick Pitch
   - Why It Matches Your Request
   - Award & Prestige Highlights
4. **Interact with movies** - Action buttons on both front and back of cards:
   - Click the 👍 button to like a movie
   - Click the 👎 button to dislike a movie
   - Click the 📋 button to add to your watchlist
5. **Close flipped view** - Click anywhere on the flipped card or backdrop to return to normal view
6. **Mobile navigation** - On mobile, swipe left/right to browse through movie recommendations
7. **Access your watchlist** - Click the "📋 Watchlist" button in the header to view all saved movies
8. **Manage your watchlist** - Remove movies from the watchlist modal when you've watched them
9. **Continue the conversation** - Ask follow-up questions or for more recommendations - the AI remembers context
10. **Start fresh** - Click the "🔄 New Session" button to clear all history and begin anew

### Testing Individual Components

**Test TMDB integration:**
```bash
python tests/test_tmdb.py
```

**Test OMDb integration:**
```bash
python tests/test_omdb.py
```

**Test the recommendation chain:**
```bash
python -m cineman.chain
```

**Test movie interactions (like/dislike/watchlist):**
```bash
python tests/test_interactions.py
```

**Test conversation holding and session management:**
```bash
python tests/test_conversation.py
python tests/test_session_manager.py
```

**Test conversation with actual LLM (requires API keys):**
```bash
python tests/test_conversation_integration.py
```

**Interactive conversation testing:**
```bash
python scripts/test_conversation.py
```

## Project Structure

```
cineman/
├── cineman/                  # Main package
│   ├── __init__.py
│   ├── app.py               # Flask web application
│   ├── chain.py             # LangChain recommendation chain with Gemini AI
│   ├── models.py            # Database models (MovieInteraction)
│   ├── schemas.py           # Pydantic data schemas for validation
│   ├── utils.py             # Utility functions
│   ├── routes/              # API routes
│   │   └── api.py          # Movie API endpoints
│   └── tools/               # Movie data tools
│       ├── __init__.py
│       ├── tmdb.py          # TMDB API integration tool
│       └── omdb.py          # OMDb API integration tool
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_schemas.py      # Schema validation tests
│   ├── test_tmdb.py         # TMDB tool tests
│   └── test_omdb.py         # OMDb tool tests
├── docs/                    # Documentation
│   └── SCHEMA_GUIDE.md     # Movie data schema guide
├── scripts/                 # Utility scripts
│   └── verify_dependencies.py
├── templates/               # Flask templates
│   └── index.html          # Chat interface HTML
├── run.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Key Components

### 1. Flask Application (`cineman/app.py`)
- Serves the web interface
- Handles chat API requests
- Manages the LangChain chain instance

### 2. Recommendation Chain (`cineman/chain.py`)
- Configures Google Gemini AI model
- Defines "The Cinephile" persona and prompt structure
- Creates the LangChain chain for recommendations

### 3. Movie Tools (`cineman/tools/`)

**TMDB Tool (`cineman/tools/tmdb.py`):**
- Searches TMDB for movie posters and metadata
- Returns poster URLs and release years
- Core function for direct testing, LangChain tool wrapper for agent use

**OMDb Tool (`cineman/tools/omdb.py`):**
- Fetches movie facts (ratings, directors, posters)
- Provides IMDb ratings and additional metadata
- Core function for direct testing, LangChain tool wrapper for agent use

### 4. Data Schemas (`cineman/schemas.py`)
- **Comprehensive Movie Schema**: Validates movie data from multiple sources
- **Type Safety**: Pydantic models ensure data integrity
- **Nested Structures**: Ratings, identifiers, credits, and details
- **Backward Compatibility**: Legacy format support for existing code
- **Extensible**: Easy to add new fields for future features
- See [Schema Guide](docs/SCHEMA_GUIDE.md) for detailed documentation

### 5. Verification Script (`scripts/verify_dependencies.py`)
- Automatically checks all dependencies from `requirements.txt`
- Shows installed versions and missing packages
- Provides color-coded output for easy verification

## Technologies Used

### Backend
- **Flask**: Web framework for the chat interface
- **Flask-SQLAlchemy**: ORM for database interactions
- **SQLite**: Database for storing user preferences
- **Pydantic**: Data validation and schema definition
- **LangChain**: AI orchestration framework
- **Google Gemini AI**: Large language model for recommendations
- **TMDB API**: Movie database and poster images
- **OMDb API**: Movie ratings and additional metadata
- **Python Requests**: HTTP library for API calls
- **Python-dotenv**: Environment variable management

### Frontend
- **HTML5/CSS3**: Modern web interface
- **JavaScript**: Interactive poster cards and session management
- **Bootstrap**: Responsive UI components
- **CSS 3D Transforms**: Flip card animations

### Deployment
- **Docker**: Containerization for consistent deployment
- **Google Cloud Platform**: App Engine and Cloud Run support
- **GitHub Actions**: CI/CD workflows for automated deployment
- **Gunicorn**: Production-grade WSGI server

## API Keys Setup

### Google Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Set as `GEMINI_API_KEY` environment variable

### TMDB API Key
1. Visit [TMDB Settings](https://www.themoviedb.org/settings/api)
2. Create a new API key (use `http://localhost:5000` as application URL)
3. Set as `TMDB_API_KEY` environment variable

### OMDb API Key
1. Visit [OMDb API](http://www.omdbapi.com/apikey.aspx)
2. Request a free API key
3. Set as `OMDB_API_KEY` environment variable

## Development

### Running Tests

```bash
# Test TMDB integration
python tests/test_tmdb.py

# Test OMDb integration
python tests/test_omdb.py

# Test recommendation chain
python -m cineman.chain
```

### Verifying Dependencies

```bash
python scripts/verify_dependencies.py
```

### Adding New Tools

To add new movie data tools:
1. Create a new tool file (e.g., `new_tool.py`)
2. Implement a core function for direct testing
3. Wrap it with `@tool` decorator for LangChain integration
4. Follow the pattern in `tmdb_tool.py` and `omdb_tool.py`

## Troubleshooting

**Issue: "GEMINI_API_KEY environment variable is not set"**
- Ensure you've set the API key: `export GEMINI_API_KEY=your_key`
- Or create a `.env` file with the key

**Issue: "TMDB_API_KEY not configured"**
- Set the TMDB API key as an environment variable
- Verify the key is valid at TMDB

**Issue: Dependencies not found**
- Run `python verify_dependencies.py` to check
- Reinstall: `pip install -r requirements.txt`

**Issue: Flask app won't start**
- Ensure virtual environment is activated
- Check that port 5000 is available
- Verify all dependencies are installed

## Deployment

### Deploy to Google Cloud Platform (GCP)

This application can be easily deployed to GCP using either App Engine or Cloud Run. See the **[GCP Deployment Guide](GCP_DEPLOYMENT.md)** for complete instructions.

**Important:** The database configuration automatically adapts to the environment:
- **Local Development**: Uses SQLite file (`cineman.db`)
- **GCP Deployment**: Uses SQLite in `/tmp` (temporary) or Cloud SQL (recommended for production)
- See **[GCP Database Setup Guide](GCP_DATABASE_SETUP.md)** for persistent database configuration

**Quick Deploy to App Engine:**
```bash
gcloud app deploy --set-env-vars \
  GEMINI_API_KEY=your_key,\
  TMDB_API_KEY=your_key,\
  OMDB_API_KEY=your_key
```

**Quick Deploy to Cloud Run:**
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/cineman
gcloud run deploy cineman --image gcr.io/PROJECT_ID/cineman --allow-unauthenticated
```

For detailed setup, monitoring, and troubleshooting, refer to **[GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md)**.

### Deploy to Render

The application can also be deployed to Render using Docker. See `Dockerfile` and `RENDER_DOCKER_SETUP.md` for Render-specific instructions.

## Current Feature Set Summary

This application now includes a complete movie recommendation experience:

### ✅ Implemented Features
- **Natural Conversation Mode**: Engage in discussions about movies, directors, genres, and themes
- **Intelligent Mode Detection**: AI automatically switches between conversation and recommendation modes
- **AI-powered movie recommendations**: Get curated lists of 3 movies when you request them
- **Session memory**: Tracks conversation history and avoids duplicate suggestions
- **Context awareness**: AI remembers your preferences and previous discussions
- **Like/dislike/watchlist functionality**: Full interaction system with SQLite storage
- **Interactive flip cards**: 3D animations and modal view for movie details
- **Mobile-optimized navigation**: Swipe gestures for browsing movies
- **Session management**: New Session button to clear history and start fresh
- **GCP deployment support**: App Engine and Cloud Run ready
- **Automated CI/CD workflows**: GitHub Actions for deployment
- **Comprehensive testing suite**: Unit tests, integration tests, and interactive testing tools

### 🚀 Future Enhancements

Potential improvements:
- Persistent user accounts and cross-session preferences
- Movie comparison features
- Streaming service availability integration
- Social features - share watchlist with friends
- Advanced filtering and sorting of watchlist
- Movie recommendations based on viewing history and preferences
- Export watchlist to external services
- Multi-user support with authentication
- Real-time collaboration features

## License

This project is open source and available for personal and educational use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Acknowledgments

- [Google Gemini AI](https://deepmind.google/technologies/gemini/) for the AI model
- [LangChain](https://www.langchain.com/) for the AI orchestration framework
- [The Movie Database (TMDB)](https://www.themoviedb.org/) for movie data and posters
- [Open Movie Database (OMDb)](http://www.omdbapi.com/) for additional movie metadata
- [Flask](https://flask.palletsprojects.com/) for the web framework

---

Enjoy discovering your next favorite movie! 🎬✨
