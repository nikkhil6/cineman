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
- ⏱️ **Session Timeout Timer**: Visual countdown showing time remaining before session expires
- 📊 **API Status Monitoring**: Real-time health indicators for external APIs (Gemini, TMDB, OMDb)

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

### Performance & Infrastructure Features
- 💨 **Response Caching**: In-memory caching layer for API responses with configurable TTL
- 🔄 **Automatic Retry Logic**: Exponential backoff for transient API failures
- 📈 **Prometheus Metrics**: Comprehensive metrics for monitoring and alerting
- 📝 **Structured Logging**: JSON logging with request tracing and automatic PII scrubbing
- 🔒 **Secret Management**: Google Cloud Secret Manager integration for secure API key storage
- ⚡ **Performance Optimization**: Reduced API calls through intelligent caching
- 🏗️ **Modular Architecture**: Clean separation of concerns for maintainability

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

# Optional configurations
export WATCHMODE_API_KEY=your_watchmode_api_key  # For streaming availability
export GEMINI_DAILY_LIMIT=50                      # Daily API call limit
export LOG_LEVEL=INFO                             # Logging level (DEBUG, INFO, WARNING, ERROR)
export MOVIE_CACHE_TTL=86400                      # Cache TTL in seconds (default 24 hours)
export MOVIE_CACHE_MAX_SIZE=1000                  # Maximum cache entries
```

Or create a `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key
TMDB_API_KEY=your_tmdb_api_key
OMDB_API_KEY=your_omdb_api_key

# Optional
WATCHMODE_API_KEY=your_watchmode_api_key
GEMINI_DAILY_LIMIT=50
LOG_LEVEL=INFO
MOVIE_CACHE_TTL=86400
MOVIE_CACHE_MAX_SIZE=1000
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

- **Regression testing (single LLM invocation)**:
```bash
pytest tests/test_llm_service_regression.py
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
│   ├── session_manager.py   # Session management and chat history
│   ├── cache.py             # In-memory caching layer for API responses
│   ├── metrics.py           # Prometheus metrics collection
│   ├── validation.py        # LLM hallucination validation
│   ├── rate_limiter.py      # API rate limiting
│   ├── api_client.py        # HTTP client abstraction with retry logic
│   ├── api_status.py        # External API health checking
│   ├── secret_helper.py     # GCP Secret Manager integration
│   ├── logging_config.py    # Structured logging configuration
│   ├── logging_context.py   # Request/session context for logging
│   ├── logging_metrics.py   # Logging performance metrics
│   ├── logging_middleware.py # Flask logging middleware
│   ├── utils.py             # Utility functions
│   ├── services/            # Core business logic services
│   │   └── llm_service.py   # LLM interaction and orchestration
│   ├── routes/              # API routes
│   │   └── api.py          # Movie API endpoints, /metrics, /api/status
│   └── tools/               # Movie data tools
│       ├── __init__.py
│       ├── tmdb.py          # TMDB API integration tool
│       ├── omdb.py          # OMDb API integration tool
│       └── watchmode.py     # Watchmode streaming availability tool
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_schemas.py      # Schema validation tests
│   ├── test_metrics.py      # Metrics collection tests
│   ├── test_cache.py        # Cache unit tests
│   ├── test_cache_integration.py # Cache integration tests
│   ├── test_api_status.py   # API status monitoring tests
│   ├── test_llm_service_regression.py # Regression tests for LLM service
│   ├── test_tmdb.py         # TMDB tool tests
│   └── test_omdb.py         # OMDb tool tests
├── docs/                    # Documentation
│   ├── SCHEMA_GUIDE.md      # Movie data schema guide
│   ├── metrics.md           # Metrics and monitoring guide
│   ├── logging.md           # Structured logging guide
│   ├── CACHE_GUIDE.md       # Caching layer documentation
│   ├── VALIDATION_GUIDE.md  # LLM validation documentation
│   ├── api-client-abstraction.md # API client documentation
│   ├── API_STATUS_FEATURE.md # API status monitoring guide
│   ├── SESSION_TIMER_FEATURE.md # Session timeout timer guide
│   └── GCP_DEPLOYMENT.md    # Google Cloud deployment guide
├── wiki/                    # Wiki documentation
│   ├── Home.md              # Wiki home page
│   ├── Getting-Started.md   # Quick start guide
│   ├── Architecture.md      # Technical architecture
│   ├── API-Keys.md          # API key configuration
│   └── Troubleshooting.md   # Common issues and solutions
├── scripts/                 # Utility scripts
│   └── verify_dependencies.py
├── static/                  # Static assets
│   ├── css/                 # Stylesheets
│   │   ├── api-status.css   # API status styling
│   │   ├── chat.css         # Chat interface styling
│   │   └── session-timer.css # Session timer styling
│   ├── js/                  # JavaScript files
│   │   ├── api-status.js    # API status monitoring
│   │   ├── session-timer.js # Session timeout timer
│   │   ├── movie-integration.js # Movie card interactions
│   │   ├── watchlist.js     # Watchlist management
│   │   └── chat-enhancements.js # Chat UI enhancements
│   └── images/              # Images and assets
├── templates/               # Flask templates
│   └── index.html          # Chat interface HTML
├── prompts/                 # AI prompts
│   └── cineman_system_prompt.txt # System prompt for Gemini AI
├── run.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker containerization
├── app.yaml                # Google App Engine configuration
├── cloudrun.yaml           # Google Cloud Run configuration
├── render.yaml             # Render deployment configuration
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Key Components

### 1. Flask Application (`cineman/app.py`)
- Serves the web interface
- Handles chat API requests and delegates to `LLMService`
- Manages user sessions and basic routing
- Integrates structured logging and metrics collection

### 2. LLM Service (`cineman/services/llm_service.py`)
- Orchestrates the chat request lifecycle (Single-Invocation Chain)
- Manages the LangChain chain instance
- Handles session context and movie validation
- **Structured-Direct Orchestration**: Aggregates TMDB/OMDb data and enriches the LLM response
- Ensures performance by optimizing LLM calls and eliminating frontend fetches

### 3. Recommendation Chain (`cineman/chain.py`)
- Configures Google Gemini AI model (gemini-2.5-flash)
- Defines "The Cinephile" persona and prompt structure
- Uses structured output via Pydantic schemas
- Implements creative recommendation generation (temperature 1.2)

### 4. Movie Tools (`cineman/tools/`)

**TMDB Tool (`cineman/tools/tmdb.py`):**
- Searches TMDB for movie posters and metadata
- Returns poster URLs and release years
- Core function for direct testing, LangChain tool wrapper for agent use

**OMDb Tool (`cineman/tools/omdb.py`):**
- Fetches movie facts (ratings, directors, posters)
- Provides IMDb ratings and additional metadata
- Core function for direct testing, LangChain tool wrapper for agent use

**Watchmode Tool (`cineman/tools/watchmode.py`):**
- Provides streaming availability information
- Searches for movies across streaming platforms
- Returns platform-specific viewing links
- Supports fallback with dummy data for development

### 5. Data Schemas (`cineman/schemas.py`)
- **Structured-Direct Architecture**: Orchestrates movie data flow directly from backend to frontend without redundant client-side fetching.
- **Comprehensive Movie Schema**: Validates movie data from multiple sources (TMDB, OMDb, LLM)
- **Type Safety**: Pydantic models ensure data integrity
- **Enriched Enrichment**: Backend validates recommendations and attaches posters/ratings/directors directly to the JSON response.
- See [Schema Guide](docs/SCHEMA_GUIDE.md) for detailed documentation

### 6. Session Management (`cineman/session_manager.py`)
- Manages user chat sessions and conversation history
- Tracks recommended movies to avoid duplicates
- Implements session timeout and cleanup
- Provides session data persistence across requests

### 7. Caching Layer (`cineman/cache.py`)
- In-memory caching for TMDB/OMDb API responses
- Configurable TTL (default 24 hours)
- LRU eviction policy for cache management
- Normalized key generation for improved hit rates
- Reduces API calls and improves performance

### 8. Structured Logging (`cineman/logging_*.py`)
- JSON structured logging for production environments
- Request/session ID propagation for tracing
- Automatic scrubbing of sensitive data (API keys, PII)
- Performance metrics tracking
- Configurable via LOG_LEVEL environment variable

### 9. API Client Abstraction (`cineman/api_client.py`)
- Robust HTTP client with automatic retry logic
- Exponential backoff for transient failures
- Configurable timeouts and retry limits
- Standardized error taxonomy (AuthError, QuotaError, TransientError)
- Used by all movie data tools for reliable API integration

### 10. API Status Monitoring (`cineman/api_status.py`)
- Real-time health checks for external APIs
- Monitors Gemini AI, TMDB, and OMDb availability
- Provides status endpoint for frontend integration
- Displays response times and error messages

### 11. Secret Management (`cineman/secret_helper.py`)
- Loads API keys from Google Cloud Secret Manager
- Supports fallback to environment variables for local development
- Automatic injection at application startup
- Graceful degradation when secrets unavailable

### 12. Verification Script (`scripts/verify_dependencies.py`)
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

### Rate Limiting Configuration (Optional)
By default, the application enforces a limit of 50 Gemini API calls per day (matching the free tier limit). You can customize this:

1. Set the `GEMINI_DAILY_LIMIT` environment variable to your desired limit
2. Example: `export GEMINI_DAILY_LIMIT=100` for paid tier

The rate limiter:
- Tracks API usage in the database (persistent across restarts)
- Automatically resets the counter at midnight UTC
- Returns a graceful error message (HTTP 429) when the limit is reached
- Provides a `/api/rate-limit` endpoint to check current usage

### Optional API Keys

#### Watchmode API (Optional)
For streaming availability information:
1. Visit [Watchmode API](https://api.watchmode.com/)
2. Sign up for an API key
3. Set as `WATCHMODE_API_KEY` environment variable
4. If not configured, the application uses dummy data with search links

**Note:** Watchmode integration provides real streaming platform availability but is not required for core functionality.

### Metrics and Monitoring

CineMan exposes comprehensive metrics in Prometheus format for external monitoring:

**Metrics Endpoint:** `GET /api/metrics`

**Available Metrics:**
- HTTP request counts and latencies (by endpoint and status code)
- External API call statistics (TMDB, OMDB, Gemini)
- Cache hit/miss rates for performance optimization
- Movie validation metrics (valid, dropped, corrected recommendations)
- Rate limiter usage and quota tracking
- LLM invocation statistics and performance
- Active sessions and user engagement

**Example Usage:**
```bash
# View metrics in Prometheus format
curl http://localhost:5000/api/metrics

# Check rate limit status
curl http://localhost:5000/api/rate-limit
```

**Key Features:**
- Prometheus-compatible text format for easy integration
- No sensitive data exposed (no API keys, user data, or credentials)
- Real-time performance monitoring and alerting support
- Comprehensive test coverage including load and error scenarios

For detailed metrics documentation, see [docs/metrics.md](docs/metrics.md).

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
- **Session timeout timer**: Visual countdown showing time remaining before session expires
- **API status monitoring**: Real-time health checks for Gemini AI, TMDB, and OMDb
- **Response caching**: In-memory cache with configurable TTL and LRU eviction
- **Structured logging**: JSON logging with request tracing and PII scrubbing
- **Automatic retry logic**: Exponential backoff for transient API failures
- **Movie validation**: LLM hallucination detection and correction against TMDB/OMDb
- **Rate Limiting**: Intelligent API usage tracking with daily limits (50 calls/day for free tier)
  - Persistent tracking across restarts using database storage
  - Automatic daily reset at midnight UTC
  - Graceful degradation with user-friendly error messages
  - Rate limit status API endpoint for monitoring usage
- **Prometheus metrics**: Comprehensive monitoring for HTTP requests, API calls, cache performance, and more
- **Secret management**: Google Cloud Secret Manager integration for secure API key storage
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party API Attribution

This application uses third-party APIs and their data is subject to their respective terms:

**The Movie Database (TMDB)**
- This product uses the TMDB API but is not endorsed or certified by TMDB.
- Movie data and images are sourced from [The Movie Database (TMDB)](https://www.themoviedb.org/).
- TMDB API is used under their [API Terms of Use](https://www.themoviedb.org/api-terms-of-use).
- For non-commercial use only, unless you have a commercial TMDB API license.

**Open Movie Database (OMDb)**
- Movie ratings and metadata are sourced from [OMDb API](https://www.omdbapi.com/).
- OMDb API requires an API key for usage, available at their website.
- Data is used in accordance with OMDb API terms of service.

## Contributing

Contributions are welcome! By contributing to this project, you agree that your contributions will be licensed under the MIT License.

Please feel free to:
- Submit issues for bugs, feature requests, or improvements
- Fork the repository and create pull requests
- Improve documentation
- Share feedback and suggestions

When contributing, please ensure:
- Your code follows the existing style and conventions
- You test your changes thoroughly
- You update documentation as needed
- You respect the attribution requirements for TMDB and OMDb APIs

## Acknowledgments

- [Google Gemini AI](https://deepmind.google/technologies/gemini/) for the AI model
- [LangChain](https://www.langchain.com/) for the AI orchestration framework
- [The Movie Database (TMDB)](https://www.themoviedb.org/) for movie data and posters
- [Open Movie Database (OMDb)](http://www.omdbapi.com/) for additional movie metadata
- [Flask](https://flask.palletsprojects.com/) for the web framework

---

Enjoy discovering your next favorite movie! 🎬✨
