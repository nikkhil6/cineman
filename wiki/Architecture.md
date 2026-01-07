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
│  LLM Service    │
│ (llm_service.py)│
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
- Manages user sessions and delegates orchestration to `LLMService`
- Handles error responses

### 2. LLM Service (`cineman/services/llm_service.py`)

**Responsibilities:**
- Orchestrates the complete chat request lifecycle
- Manages the LangChain chain instance
- Handles session context (previously recommended movies)
- Performs movie validation (hallucination checks)
- Optimizes LLM invocations to prevent redundant calls

### 3. LangChain Chain (`cineman/chain.py`)

**Responsibilities:**
- Configures Google Gemini AI model
- Loads and manages system prompts
- Defines the structured output schema via Pydantic
- Creates the sequence: Prompt | LLM | Structured Output

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

#### Watchmode Tool (`watchmode.py`)
- Fetches streaming availability information
- Searches across multiple streaming platforms
- Returns platform-specific viewing links
- Supports fallback with dummy data

**Design Pattern:**
- Core function for direct testing
- LangChain `@tool` decorator for agent integration
- Error handling with graceful degradation

### 4. Caching Layer (`cineman/cache.py`)

**Responsibilities:**
- In-memory caching of API responses
- Configurable TTL (default 24 hours)
- LRU eviction policy for cache management
- Normalized key generation for improved hit rates
- Metrics tracking for cache performance

### 5. Logging System (`cineman/logging_*.py`)

**Components:**
- `logging_config.py` - Structured logging setup
- `logging_context.py` - Request/session context propagation
- `logging_metrics.py` - Performance metrics tracking
- `logging_middleware.py` - Flask middleware integration

**Features:**
- JSON formatting for production
- Console formatting for development
- Automatic PII scrubbing
- Configurable via LOG_LEVEL environment variable

### 6. API Client (`cineman/api_client.py`)

**Responsibilities:**
- HTTP client abstraction for external APIs
- Automatic retry with exponential backoff
- Configurable timeouts
- Error taxonomy (AuthError, QuotaError, TransientError, NotFoundError)
- Used by all movie data tools

### 7. API Status Monitoring (`cineman/api_status.py`)

**Responsibilities:**
- Health checks for Gemini AI, TMDB, OMDb
- Response time monitoring
- Status endpoint for frontend integration
- Real-time error detection

### 8. Secret Management (`cineman/secret_helper.py`)

**Responsibilities:**
- Google Cloud Secret Manager integration
- Environment variable fallback for local development
- Automatic API key injection at startup
- Graceful degradation when unavailable

### 9. Session Management (`cineman/session_manager.py`)

**Responsibilities:**
- Chat history tracking per session
- Recommended movie tracking
- Session timeout management
- Cleanup of expired sessions

### 10. Web Interface

**Frontend:**
- HTML/CSS/JavaScript chat UI
- Real-time message exchange
- Responsive design

**Location:**
- Templates: `templates/index.html`
- Static assets: `static/` (CSS, JS, images)

## Data Flow

1. **User Input** → Browser sends message to `/chat` endpoint
2. **Flask Handler** → Receives JSON, loads session, calls `llm_service.process_chat_request`
3. **LLM Service** → Prepares context, calls LangChain chain
4. **Chain Invocation** → Invokes Gemini AI with structured output enabled
5. **Validation & Enrichment** → `LLM Service` validates recommended movies against TMDB/OMDb AND enriches them with posters, director, and ratings.
6. **Response** → Returns enriched JSON containing text and fully-populated movie list.
7. **Display** → Browser renders conversational text, detailed summaries, and finally interactive flip cards.

## Configuration Management

### Environment Variables

#### Required
- `GEMINI_API_KEY` - Google Gemini API authentication
- `TMDB_API_KEY` - TMDB API authentication
- `OMDB_API_KEY` - OMDb API authentication

#### Optional
- `WATCHMODE_API_KEY` - Watchmode streaming availability API
- `GEMINI_DAILY_LIMIT` - Daily API call limit (default: 50)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, default: INFO)
- `MOVIE_CACHE_TTL` - Cache TTL in seconds (default: 86400)
- `MOVIE_CACHE_MAX_SIZE` - Maximum cache entries (default: 1000)
- `MOVIE_CACHE_ENABLED` - Enable/disable caching (default: 1)
- `SECRET_KEY` - Flask session secret (default: auto-generated for dev)
- `PORT` - Server port (default: 5000)

#### Google Cloud Platform
- `GCP_PROJECT` - GCP project ID for Secret Manager
- `GEMINI_SECRET_NAME` - Secret name in Secret Manager (default: gemini-api-key)
- `GAE_ENV` - App Engine environment indicator
- `CLOUD_RUN_SERVICE` - Cloud Run service indicator

### File Structure
```
cineman/
├── cineman/           # Main package
│   ├── app.py        # Flask application
│   ├── chain.py      # LangChain setup
│   ├── services/     # Business logic
│   │   └── llm_service.py
│   ├── routes/       # API routes
│   │   └── api.py
│   ├── tools/        # Movie API tools
│   │   ├── tmdb.py
│   │   ├── omdb.py
│   │   └── watchmode.py
│   ├── cache.py      # Caching layer
│   ├── session_manager.py # Session management
│   ├── logging_*.py  # Logging system
│   ├── api_client.py # HTTP client abstraction
│   ├── api_status.py # API health checks
│   ├── secret_helper.py # Secret management
│   ├── validation.py # Movie validation
│   ├── rate_limiter.py # Rate limiting
│   ├── metrics.py    # Prometheus metrics
│   ├── schemas.py    # Pydantic schemas
│   ├── models.py     # Database models
│   └── utils.py      # Utilities
├── prompts/          # AI prompts
├── templates/        # HTML templates
├── static/           # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── images/
├── tests/            # Test suite
├── docs/             # Documentation
├── wiki/             # Wiki pages
└── scripts/          # Utility scripts
```

## Technology Stack

- **Backend:** Flask 3.0+, Gunicorn
- **Database:** SQLite (Flask-SQLAlchemy), PostgreSQL support
- **AI Framework:** LangChain
- **LLM:** Google Gemini 2.5 Flash
- **APIs:** TMDB, OMDb, Watchmode (optional)
- **Data Validation:** Pydantic 2.0+
- **Logging:** structlog (JSON structured logging)
- **Metrics:** prometheus_client
- **Caching:** In-memory (custom implementation)
- **HTTP Client:** requests with retry logic
- **Cloud:** Google Cloud (Secret Manager, App Engine, Cloud Run)
- **Frontend:** HTML, CSS, JavaScript (Vanilla)
- **Deployment:** Docker, Gunicorn, GCP, Render

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
