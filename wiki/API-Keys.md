# API Keys Configuration

Guide to obtaining and configuring the required API keys for Cineman.

## Required API Keys

Cineman requires three API keys to function:

1. **Google Gemini API** - Powers AI recommendations
2. **TMDB API** - Provides movie posters and metadata
3. **OMDb API** - Provides ratings and additional movie data

## Obtaining API Keys

### 1. Google Gemini API Key

**Steps:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key

**Usage Limits:**
- Free tier available
- Check [Google AI pricing](https://ai.google.dev/pricing) for limits

### 2. TMDB API Key

**Steps:**
1. Create account at [TMDB](https://www.themoviedb.org/)
2. Go to [Settings → API](https://www.themoviedb.org/settings/api)
3. Request an API key
4. Fill in application details:
   - Type: Website
   - URL: `http://localhost:5000` (for development)
   - Summary: Personal movie recommendation project
5. Accept terms and submit
6. Copy the API key (v3 auth)

**Usage Limits:**
- Free tier: 40 requests per 10 seconds
- No daily limit for personal projects

### 3. OMDb API Key

**Steps:**
1. Visit [OMDb API](http://www.omdbapi.com/apikey.aspx)
2. Select "FREE" (1,000 daily requests)
3. Enter your email address
4. Verify email and activate key
5. Copy the API key from activation email

**Usage Limits:**
- Free tier: 1,000 requests per day
- Paid tiers available for higher limits

## Configuration Methods

### Method 1: Environment Variables (Recommended)

**Linux/Mac:**
```bash
export GEMINI_API_KEY='your_gemini_key'
export TMDB_API_KEY='your_tmdb_key'
export OMDB_API_KEY='your_omdb_key'
```

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your_gemini_key
set TMDB_API_KEY=your_tmdb_key
set OMDB_API_KEY=your_omdb_key
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY='your_gemini_key'
$env:TMDB_API_KEY='your_tmdb_key'
$env:OMDB_API_KEY='your_omdb_key'
```

### Method 2: .env File (Recommended for Development)

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_key_here
TMDB_API_KEY=your_tmdb_key_here
OMDB_API_KEY=your_omdb_key_here
```

**Important:** The `.env` file is already in `.gitignore` - never commit API keys!

### Method 3: Deployment Platform Variables

For production deployment (e.g., Render, Heroku):

1. Go to your app's settings/configuration
2. Add environment variables:
   - Key: `GEMINI_API_KEY`, Value: your key
   - Key: `TMDB_API_KEY`, Value: your key
   - Key: `OMDB_API_KEY`, Value: your key

## Verification

After configuring keys, verify they work:

```bash
# Test TMDB
python tests/test_tmdb.py

# Test OMDb
python tests/test_omdb.py

# Test full chain
python -m cineman.chain
```

## Security Best Practices

### ✅ Do:
- Store keys in `.env` file for local development
- Use environment variables in production
- Keep keys private and never share them
- Regenerate keys if accidentally exposed
- Use separate keys for development and production

### ❌ Don't:
- Commit keys to version control
- Share keys in public forums or chat
- Hardcode keys in source code
- Use production keys for testing
- Share your `.env` file

## API Key Rotation

If you need to rotate keys:

1. **Generate new keys** from each service
2. **Update your configuration** (`.env` or environment variables)
3. **Restart the application**
4. **Revoke old keys** from service dashboards

### Updating Gemini API Key on GCP

If you have deployed your application to Google Cloud Platform and need to update the Gemini API key, see the detailed **[Update Gemini API Key on GCP Guide](../docs/UPDATE_GEMINI_API_KEY.md)** for step-by-step instructions covering:
- Using Secret Manager (recommended for production)
- Updating environment variables directly
- Using the automated deployment scripts

## Troubleshooting API Keys

### Error: "GEMINI_API_KEY environment variable is not set"
- Ensure the key is set in your environment or `.env` file
- Restart your terminal/IDE after setting environment variables

### Error: "TMDB_API_KEY not configured"
- Verify the key is correct (v3 auth key, not v4)
- Check TMDB account is activated

### Error: OMDb returns 401 Unauthorized
- Verify email activation was completed
- Check daily limit hasn't been exceeded
- Ensure key is correctly copied (no extra spaces)

### All API calls failing
- Check internet connection
- Verify API services are operational
- Review service status pages
