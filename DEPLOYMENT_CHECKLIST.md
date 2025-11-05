# Render Deployment Checklist

## ✅ Fixed Issues

1. ✅ **Added `gunicorn` to requirements.txt** - Required for production server
2. ✅ **Added `/health` endpoint** - Required by render.yaml health check
3. ✅ **Verified Dockerfile** - Correctly configured for Render
4. ✅ **Verified render.yaml** - Correct configuration

## Required Files (All Present)

- ✅ `requirements.txt` - Includes gunicorn
- ✅ `Dockerfile` - Docker configuration
- ✅ `render.yaml` - Render service configuration
- ✅ `Procfile` - Alternative deployment method
- ✅ `.gitignore` - Excludes venv, .env, etc.
- ✅ `.dockerignore` - Excludes unnecessary files from Docker build
- ✅ `cineman/app.py` - Flask application with health endpoint
- ✅ `templates/index.html` - Frontend template

## Environment Variables (Set in Render Dashboard)

Make sure these are set in Render dashboard:
- `GEMINI_API_KEY` - Your Google Gemini API key
- `TMDB_API_KEY` - Your TMDB API key  
- `OMDB_API_KEY` - Your OMDb API key

## Deployment Steps

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add gunicorn and health endpoint for Render deployment"
   git push origin main
   ```

2. **In Render Dashboard:**
   - Connect your GitHub repo: `https://github.com/nikkhil6/cineman`
   - Select branch: `main`
   - Render will auto-detect `render.yaml` OR you can manually configure:
     - **Environment:** Docker
     - **Build Command:** (leave empty, Dockerfile handles it)
     - **Start Command:** `gunicorn cineman.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
     - **Health Check Path:** `/health`
   
3. **Set Environment Variables** in Render dashboard (not in code!)

4. **Deploy** - Render will automatically build and deploy

## Common Issues & Solutions

### Issue: Build fails with "ModuleNotFoundError"
**Solution:** Make sure `cineman/__init__.py` exists and all files are committed

### Issue: App starts but returns 503
**Solution:** Check that `GEMINI_API_KEY` is set correctly in Render environment variables

### Issue: Health check fails
**Solution:** Verify `/health` endpoint returns 200 (already added ✅)

### Issue: Port binding errors
**Solution:** Make sure using `$PORT` environment variable (already configured ✅)

## Testing Locally Before Deploy

1. **Test with Docker:**
   ```bash
   docker build -t cineman .
   docker run -p 8000:8000 -e PORT=8000 -e GEMINI_API_KEY=xxx -e TMDB_API_KEY=yyy -e OMDB_API_KEY=zzz cineman
   ```

2. **Test with Gunicorn directly:**
   ```bash
   source venv/bin/activate
   pip install gunicorn
   gunicorn cineman.app:app --bind 0.0.0.0:8000 --workers 2
   ```

## File Structure Verification

```
cineman/
├── cineman/
│   ├── __init__.py ✅
│   ├── app.py ✅ (with /health endpoint)
│   ├── chain.py ✅
│   └── tools/ ✅
├── templates/
│   └── index.html ✅
├── requirements.txt ✅ (includes gunicorn)
├── Dockerfile ✅
├── render.yaml ✅
├── Procfile ✅
├── .gitignore ✅
└── .dockerignore ✅
```

All files are present and correctly configured! 🎉

