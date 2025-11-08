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

### Session Management Features
- 🧠 **Conversation Memory**: AI remembers previous recommendations to avoid duplicates
- 💬 **Chat History Tracking**: Maintains conversation context across messages
- 🎬 **Movie Tracking**: Tracks all recommended movies in your session
- 🔄 **New Session Button**: Clear history and start fresh anytime
- 🎭 **Creative Recommendations**: Enhanced AI creativity (temperature 1.2) for varied suggestions

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

1. **Enter your movie request** in the chat input (e.g., "I'm in the mood for a sci-fi movie with a clever plot twist")
2. **Get AI recommendations** - The Cinephile agent will provide personalized movie suggestions
3. **View movie posters** - Each recommendation appears as an interactive poster card with hover effects
4. **Click to flip** - Click anywhere on a poster to flip it with 3D animation and see full details
5. **View detailed information** - Flipped cards show:
   - Movie poster on the left
   - Title, year, director, and IMDB rating
   - The Quick Pitch
   - Why It Matches Your Request
   - Award & Prestige Highlights
6. **Interact with movies** - Action buttons on both front and back of cards:
   - Click the 👍 button to like a movie
   - Click the 👎 button to dislike a movie
   - Click the 📋 button to add to your watchlist
7. **Close flipped view** - Click anywhere on the flipped card or backdrop to return to normal view
8. **Mobile navigation** - On mobile, swipe left/right to browse through movie recommendations
9. **Access your watchlist** - Click the "📋 Watchlist" button in the header to view all saved movies
10. **Manage your watchlist** - Remove movies from the watchlist modal when you've watched them
11. **Continue the conversation** - Ask for more recommendations - the AI remembers what it already suggested
12. **Start fresh** - Click the "🔄 New Session" button to clear all history and begin anew

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

## Project Structure

```
cineman/
├── cineman/                  # Main package
│   ├── __init__.py
│   ├── app.py               # Flask web application
│   ├── chain.py             # LangChain recommendation chain with Gemini AI
│   └── tools/               # Movie data tools
│       ├── __init__.py
│       ├── tmdb.py          # TMDB API integration tool
│       └── omdb.py          # OMDb API integration tool
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_tmdb.py         # TMDB tool tests
│   └── test_omdb.py         # OMDb tool tests
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

### 4. Verification Script (`scripts/verify_dependencies.py`)
- Automatically checks all dependencies from `requirements.txt`
- Shows installed versions and missing packages
- Provides color-coded output for easy verification

## Technologies Used

### Backend
- **Flask**: Web framework for the chat interface
- **Flask-SQLAlchemy**: ORM for database interactions
- **SQLite**: Database for storing user preferences
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
- AI-powered conversational movie recommendations
- Session memory to avoid duplicate suggestions
- Like/dislike/watchlist functionality with SQLite storage
- Interactive flip cards with 3D animations and modal view
- Mobile-optimized navigation with swipe gestures
- Session management with New Session button
- GCP deployment support (App Engine and Cloud Run)
- Automated CI/CD workflows
- Comprehensive testing suite

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
