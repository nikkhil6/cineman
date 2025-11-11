# Getting Started

Quick guide to set up and run Cineman.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (for cloning)

## Installation Steps

### 1. Clone the Repository
```bash
git clone https://github.com/nikkhil6/cineman.git
cd cineman
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python scripts/verify_dependencies.py
```

### 5. Configure API Keys

Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_gemini_api_key
TMDB_API_KEY=your_tmdb_api_key
OMDB_API_KEY=your_omdb_api_key
```

See [API Keys](API-Keys.md) for detailed instructions on obtaining these keys.

## Running the Application

### Start the Server
```bash
python run.py
```

The application will start on `http://127.0.0.1:5000`

### Using the Chat Interface

1. Open your browser to `http://127.0.0.1:5000`
2. Type your movie request (e.g., "I want a thriller with unexpected twists")
3. Get AI-powered recommendations with detailed information

## Testing

### Test Individual Components
```bash
# Test TMDB integration
python tests/test_tmdb.py

# Test OMDb integration
python tests/test_omdb.py

# Test recommendation chain
python -m cineman.chain
```

## Next Steps

- Learn about the [Architecture](Architecture.md)
- Review [Troubleshooting](Troubleshooting.md) tips
- Explore the codebase and customize
