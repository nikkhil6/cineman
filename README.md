# 🎬 Cineman - AI Movie Recommender

An intelligent movie recommendation agent powered by Google Gemini AI (via LangChain) and integrated with The Movie Database (TMDB) and Open Movie Database (OMDB) APIs. Get personalized, conversational movie recommendations through a beautiful web interface.

## Features

- 🤖 **AI-Powered Recommendations**: Conversational movie recommendations using Google Gemini AI
- 🎯 **The Cinephile Agent**: Expert AI persona that provides curated movie suggestions
- 🎨 **Interactive Web Interface**: Beautiful Flask-based chat interface for seamless interaction
- 🧠 **Session Memory**: AI remembers your conversation and never recommends the same movie twice in a session
- 🎲 **Creative Diversity**: Enhanced temperature settings ensure varied and interesting recommendations
- 🔄 **Session Management**: Clear button to start fresh conversations anytime
- 🎬 **Movie Data Integration**: 
  - TMDB API for movie posters and metadata
  - OMDb API for ratings, directors, and additional movie facts
- 🔧 **LangChain Tools**: Extensible tool system for movie data retrieval
- ✅ **Dependency Verification**: Built-in script to verify all dependencies are installed

## Architecture

The application uses a modular architecture:
- **Flask Web Server**: Serves the chat interface and handles API requests
- **Session Manager**: Tracks chat history and recommended movies per user session
- **LangChain Chain**: Orchestrates the AI recommendation workflow with memory support
- **Google Gemini AI**: Powers the conversational recommendation engine with increased creativity
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
3. **View detailed information** - Each recommendation includes plot, matching reasons, and awards
4. **Continue the conversation** - Ask for more recommendations and the AI will remember what it already suggested
5. **Start fresh** - Click the "🔄 New Session" button to clear history and begin a new conversation

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

**Test session manager:**
```bash
python tests/test_session_manager.py
```

## Project Structure

```
cineman/
├── cineman/                    # Main package
│   ├── __init__.py
│   ├── app.py                 # Flask web application with session support
│   ├── chain.py               # LangChain recommendation chain with Gemini AI
│   ├── session_manager.py     # Session management for chat history and recommendations
│   ├── routes/                # API routes
│   │   └── api.py            # Movie data API endpoints
│   └── tools/                 # Movie data tools
│       ├── __init__.py
│       ├── tmdb.py            # TMDB API integration tool
│       └── omdb.py            # OMDb API integration tool
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_tmdb.py           # TMDB tool tests
│   ├── test_omdb.py           # OMDb tool tests
│   └── test_session_manager.py # Session manager tests
├── scripts/                   # Utility scripts
│   └── verify_dependencies.py
├── templates/                 # Flask templates
│   └── index.html            # Chat interface HTML
├── static/                    # Static assets
│   └── js/                   # JavaScript files
│       ├── movie-integration.js
│       └── chat-enhancements.js
├── prompts/                   # AI prompts
│   └── cineman_system_prompt.txt
├── run.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## Key Components

### 1. Flask Application (`cineman/app.py`)
- Serves the web interface
- Handles chat API requests with session management
- Manages the LangChain chain instance
- Tracks conversation history and recommended movies per session

### 2. Session Manager (`cineman/session_manager.py`)
- Manages user sessions with in-memory storage
- Tracks chat history for conversation context
- Prevents duplicate movie recommendations within a session
- Automatic session cleanup after timeout (60 minutes)

### 3. Recommendation Chain (`cineman/chain.py`)
- Configures Google Gemini AI model with enhanced creativity (temperature 1.2)
- Defines "The Cinephile" persona and prompt structure
- Creates the LangChain chain for recommendations with memory support
- Integrates session context to avoid repetition

### 4. Movie Tools (`cineman/tools/`)

**TMDB Tool (`cineman/tools/tmdb.py`):**
- Searches TMDB for movie posters and metadata
- Returns poster URLs and release years
- Core function for direct testing, LangChain tool wrapper for agent use

**OMDb Tool (`cineman/tools/omdb.py`):**
- Fetches movie facts (ratings, directors, posters)
- Provides IMDb ratings and additional metadata
- Core function for direct testing, LangChain tool wrapper for agent use

### 5. Verification Script (`scripts/verify_dependencies.py`)
- Automatically checks all dependencies from `requirements.txt`
- Shows installed versions and missing packages
- Provides color-coded output for easy verification

## Technologies Used

- **Flask**: Web framework for the chat interface
- **LangChain**: AI orchestration framework
- **Google Gemini AI**: Large language model for recommendations
- **TMDB API**: Movie database and poster images
- **OMDb API**: Movie ratings and additional metadata
- **Python Requests**: HTTP library for API calls
- **Python-dotenv**: Environment variable management

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

## Session Management

CineMan now includes intelligent session management that ensures you never get the same movie recommendation twice in a single conversation:

### How It Works

1. **Automatic Session Creation**: A unique session is created for each user when they first visit
2. **Chat History Tracking**: All messages are stored and used to provide context to the AI
3. **Movie Tracking**: Every recommended movie is tracked to prevent duplicates
4. **Smart Context**: The AI is automatically informed about previously recommended movies
5. **Session Timeout**: Sessions expire after 60 minutes of inactivity

### Features

- **Memory**: The AI remembers your conversation and preferences within a session
- **No Duplicates**: You'll never see the same movie recommended twice in one session
- **Variety**: Enhanced creativity settings ensure diverse recommendations
- **Clear Session**: Use the "🔄 New Session" button to start fresh anytime

### API Endpoints

- `POST /chat` - Send a message and get recommendations (manages session automatically)
- `POST /session/clear` - Clear the current session and start fresh

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

## Future Enhancements

Potential improvements:
- Integration of movie tools into the LangChain agent
- Persistent user preferences and chat history
- Movie comparison features
- Watchlist functionality
- Streaming service availability integration
- User ratings and reviews
- Movie recommendations based on viewing history

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
