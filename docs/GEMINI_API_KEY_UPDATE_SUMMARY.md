# Quick Summary: Updating Gemini API Key on GCP

This is a quick reference for updating your Gemini API key on Google Cloud Platform. For detailed instructions, see the [Complete Guide](UPDATE_GEMINI_API_KEY.md).

## Prerequisites
✅ New Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)  
✅ `gcloud` CLI installed and authenticated  
✅ Access to your GCP project

---

## Quick Steps

### Method 1: Using Secret Manager (Recommended - Current Setup)

```bash
# Update the secret
echo -n "your_new_gemini_api_key" | gcloud secrets versions add gemini-api-key --data-file=-

# Restart the app (App Engine)
gcloud app deploy

# OR restart the app (Cloud Run)
gcloud run services update cineman --region us-central1
```

**Or use the automated script:**
```bash
./scripts/create_secret.sh YOUR_PROJECT_ID
```

---

### Method 2: Using Environment Variables

**For App Engine:**
```bash
gcloud app deploy --set-env-vars GEMINI_API_KEY=your_new_key
```

**For Cloud Run:**
```bash
gcloud run services update cineman \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=your_new_key
```

---

### Method 3: Using Deployment Script

```bash
export GEMINI_API_KEY="your_new_key"
./scripts/deploy_gcp.sh
```

---

## Verify the Update

```bash
# Check health endpoint
curl https://YOUR_PROJECT_ID.uc.r.appspot.com/health

# Check logs
gcloud app logs tail -s default  # For App Engine
# OR
gcloud run services logs read cineman --region YOUR_REGION  # For Cloud Run
```

---

## Need More Help?

📖 **[Complete Update Guide](UPDATE_GEMINI_API_KEY.md)** - Detailed step-by-step instructions with troubleshooting  
📖 **[API Keys Guide](../wiki/API-Keys.md)** - General API key configuration  
📖 **[GCP Deployment Guide](GCP_DEPLOYMENT.md)** - Full GCP deployment documentation

---

✅ **That's it!** Your Gemini API key is now updated on GCP.
