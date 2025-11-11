# Architecture

Technical overview of Cineman's system design and components.

## System Overview

Cineman uses a modular architecture with clear separation of concerns:

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Flask Server   │
│   (app.py)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LangChain      │
│  Chain          │
│  (chain.py)     │
└────────┬────────┘
         │
         ├─────────────────┐
         ▼                 ▼
┌──────────────┐   ┌────────────┐
│ Gemini AI    │   │ Movie APIs │
│              │   │ TMDB/OMDb  │
└──────────────┘   └────────────┘
```

## Core Components

### 1. Flask Application (`cineman/app.py`)

**Responsibilities:**
- Serves static files and HTML templates
- Exposes `/chat` API endpoint for user messages
- Manages LangChain chain instance
- Handles error responses

**Key Endpoints:**
- `GET /` - Chat interface
- `POST /chat` - Process user messages
- `GET /health` - Health check for deployment
- `/api/*` - Additional API routes

### 2. LangChain Chain (`cineman/chain.py`)

**Responsibilities:**
- Configures Google Gemini AI model
- Loads and manages system prompts
- Creates conversational chain
- Parses AI responses

**Key Functions:**
- `get_recommendation_chain()` - Builds the AI chain
- `load_prompt_from_file()` - Loads system prompts
- `escape_braces_for_prompt()` - Handles template formatting

**Configuration:**
- Model: `gemini-2.5-flash`
- Temperature: `1.0` (creative recommendations)
- Prompt: External file (`prompts/cineman_system_prompt.txt`)

### 3. Movie Data Tools (`cineman/tools/`)

#### TMDB Tool (`tmdb.py`)
- Searches for movies by title
- Retrieves poster URLs and metadata
- Returns release years and movie IDs

#### OMDb Tool (`omdb.py`)
- Fetches detailed movie information
- Provides IMDb ratings
- Returns director, cast, and awards

**Design Pattern:**
- Core function for direct testing
- LangChain `@tool` decorator for agent integration
- Error handling with graceful degradation

### 4. Web Interface

**Frontend:**
- HTML/CSS/JavaScript chat UI
- Real-time message exchange
- Responsive design

**Location:**
- Templates: `templates/index.html`
- Static assets: `static/` (CSS, JS, images)

## Data Flow

1. **User Input** → Browser sends message to `/chat` endpoint
2. **Flask Handler** → Receives JSON, validates message
3. **Chain Invocation** → Passes to LangChain chain with `user_input` key
4. **AI Processing** → Gemini AI generates recommendation
5. **Response** → Chain returns formatted response
6. **Display** → Browser receives and displays message

## Configuration Management

### Environment Variables
- `GEMINI_API_KEY` - Google Gemini API authentication
- `TMDB_API_KEY` - TMDB API authentication
- `OMDB_API_KEY` - OMDb API authentication

### File Structure
```
cineman/
├── cineman/           # Main package
│   ├── app.py        # Flask application
│   ├── chain.py      # LangChain setup
│   ├── routes/       # API routes
│   └── tools/        # Movie API tools
├── prompts/          # AI prompts
├── templates/        # HTML templates
├── static/           # CSS, JS, images
├── tests/            # Test suite
└── scripts/          # Utility scripts
```

## Technology Stack

- **Backend:** Flask 3.0+
- **AI Framework:** LangChain
- **LLM:** Google Gemini 2.5 Flash
- **APIs:** TMDB, OMDb
- **Frontend:** HTML, CSS, JavaScript
- **Deployment:** Gunicorn, Render-ready

## Scalability Considerations

**Current (Phase 1):**
- Single chain instance cached globally
- Synchronous request handling
- No persistent storage

**Future Enhancements:**
- Session management for user context
- Async request handling
- Response caching
- Database for user preferences
- Rate limiting and API optimization
