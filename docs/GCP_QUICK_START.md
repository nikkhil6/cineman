# 🚀 GCP Quick Start Guide

Get Cineman running on Google Cloud Platform in minutes!

## Prerequisites
- GCP account with billing enabled
- `gcloud` CLI installed ([Download](https://cloud.google.com/sdk/docs/install))
- API keys: GEMINI, TMDB, OMDB

## Option 1: App Engine (Easiest - 3 commands)

```bash
# 1. Authenticate and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Create App Engine app (one-time setup)
gcloud app create --region=us-central

# 3. Deploy
gcloud app deploy --set-env-vars \
  GEMINI_API_KEY=your_key,\
  TMDB_API_KEY=your_key,\
  OMDB_API_KEY=your_key
```

**View your app:**
```bash
gcloud app browse
```

## Option 2: Cloud Run (Best for Docker users)

```bash
# 1. Set project
export PROJECT_ID=$(gcloud config get-value project)

# 2. Build and deploy in one command
gcloud run deploy cineman \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key,TMDB_API_KEY=your_key,OMDB_API_KEY=your_key
```

## Using the Deployment Script

We provide an automated script for easier deployment:

```bash
# Export your API keys
export GEMINI_API_KEY="your_key"
export TMDB_API_KEY="your_key"
export OMDB_API_KEY="your_key"

# Run the deployment script
./scripts/deploy_gcp.sh
```

The script will:
- ✅ Check prerequisites
- ✅ Enable required APIs
- ✅ Guide you through deployment
- ✅ Configure environment variables
- ✅ Provide the deployed URL

## Verify Deployment

Check if your app is running:
```bash
# For App Engine
curl https://YOUR_PROJECT_ID.uc.r.appspot.com/health

# For Cloud Run
curl YOUR_CLOUD_RUN_URL/health
```

Expected response: `{"status":"healthy","service":"cineman"}`

## View Logs

**App Engine:**
```bash
gcloud app logs tail -s default
```

**Cloud Run:**
```bash
gcloud run services logs read cineman --region us-central1
```

## Update Environment Variables

**App Engine:**
```bash
gcloud app deploy --set-env-vars GEMINI_API_KEY=new_key
```

**Cloud Run:**
```bash
gcloud run services update cineman \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=new_key
```

## Common Issues

### "Permission denied"
```bash
gcloud auth login
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/editor"
```

### "App Engine application does not exist"
```bash
gcloud app create --region=us-central
```

### "Service unavailable"
- Check logs for errors
- Verify API keys are correct
- Ensure `/health` endpoint works

## Cost Estimate

Both options include generous free tiers:
- **App Engine**: ~$0-5/month for low traffic
- **Cloud Run**: ~$0-3/month for low traffic (scales to zero)

## Next Steps

- ✅ Test your deployment
- ✅ Set up custom domain (optional)
- ✅ Configure monitoring
- ✅ Review [Full Documentation](GCP_DEPLOYMENT.md)

## Need Help?

- 📖 [Full GCP Deployment Guide](GCP_DEPLOYMENT.md)
- 📖 [App Engine Docs](https://cloud.google.com/appengine/docs)
- 📖 [Cloud Run Docs](https://cloud.google.com/run/docs)

---

**Happy Deploying! 🎬✨**
