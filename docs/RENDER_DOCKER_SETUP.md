# How to Configure Docker Environment on Render

## Method 1: Automatic Detection (Easiest)

**Render automatically detects Docker if:**
- A `Dockerfile` exists in your repository root ✅ (You have this!)

**Steps:**
1. Go to Render Dashboard → New → Web Service
2. Connect your GitHub repo: `https://github.com/nikkhil6/cineman`
3. Render will **automatically detect** the Dockerfile
4. It will show "Docker" as the environment type
5. You can then set:
   - **Start Command:** `gunicorn cineman.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Environment Variables:** Add your API keys
   - **Health Check Path:** `/health`

## Method 2: Using render.yaml (Infrastructure as Code)

Your `render.yaml` file should have `env: docker` which tells Render to use Docker.

**If render.yaml is detected, Render will:**
- Use Docker automatically
- Read the startCommand from render.yaml
- Use the environment variables defined there

**To use render.yaml:**
1. Make sure `render.yaml` is committed to your repo
2. In Render Dashboard, when creating a service:
   - Select "Apply render.yaml" option if available
   - OR Render will auto-detect it on first deploy

## Method 3: Manual Configuration in Dashboard

If Render doesn't auto-detect or you want to set it manually:

1. **Create Web Service** in Render Dashboard
2. Connect your GitHub repo
3. **In the settings, look for:**
   - **"Environment"** dropdown → Select "Docker"
   - OR **"Build and Deploy"** section → Set to "Docker"
   
4. **If you don't see an "Environment" field:**
   - Render might be auto-detecting from Dockerfile
   - Check the build logs - if it shows "Building Docker image", it's using Docker

## Where to Set Start Command in Render Dashboard

**Location:** After creating the service, go to:
- **Settings** → **Build & Deploy** section
- Look for **"Start Command"** field
- Enter: `gunicorn cineman.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

**OR** if using render.yaml, it will use:
```yaml
startCommand: "gunicorn cineman.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"
```

## How to Verify Docker is Being Used

**Check the build logs:**
- If you see: `Building Docker image...` → Docker is being used ✅
- If you see: `Installing dependencies...` → Python build (not Docker) ❌

**In the service settings:**
- Look for "Docker" mentioned in the environment section
- Build command should be empty or Docker-related

## Troubleshooting

**Issue: Render is using Python build instead of Docker**

**Solution:**
1. Make sure `Dockerfile` is in the **root** of your repo (✅ you have this)
2. In Render Dashboard → Settings → **Clear build cache** and redeploy
3. OR explicitly set in render.yaml: `env: docker`

**Issue: Can't find "Environment" field**

**Solution:**
- Render might have moved this to a different location
- Look for "Build and Deploy" → "Build Type" or "Buildpack"
- OR just ensure Dockerfile exists - Render will auto-detect

## Recommended: Use render.yaml

Your `render.yaml` already has `env: docker` configured. Make sure it's committed and Render will use it automatically!

```yaml
services:
  - type: web
    name: cineman-web
    env: docker  # ← This tells Render to use Docker
    plan: free
    startCommand: "gunicorn cineman.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"
```

