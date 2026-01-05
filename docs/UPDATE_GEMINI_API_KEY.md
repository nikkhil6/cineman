# 🔑 How to Update the Gemini API Key on GCP

This guide provides step-by-step instructions for updating the Gemini API key on Google Cloud Platform (GCP) for your deployed Cineman application.

## Prerequisites

- Access to the [Google AI Studio](https://makersuite.google.com/app/apikey) to generate a new API key
- `gcloud` CLI installed and authenticated ([Download](https://cloud.google.com/sdk/docs/install))
- Access to your GCP project with appropriate permissions

---

## Step 1: Generate a New Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"** or **"Get API Key"**
4. Copy the generated API key (keep it secure!)

**Important:** Keep this API key private and never commit it to version control.

---

## Deployment-Specific Update Methods

Choose the method based on how your application is deployed on GCP:

### Method A: Update Secret Manager (Recommended for Production)

If your application uses Google Secret Manager (the default for the current setup), follow these steps:

#### Option 1: Using the Automated Script

The repository includes a convenient script for updating secrets:

```bash
# 1. Navigate to the repository
cd /path/to/cineman

# 2. Run the secret creation/update script
./scripts/create_secret.sh YOUR_PROJECT_ID
```

When prompted, enter your new Gemini API key (input will be hidden for security).

The script will:
- ✅ Create the secret if it doesn't exist, or add a new version if it does
- ✅ Grant the App Engine service account access to the secret
- ✅ Clean up the key from memory for security

#### Option 2: Using gcloud Commands Manually

```bash
# 1. Set your GCP project
gcloud config set project YOUR_PROJECT_ID

# 2. Create or update the secret
echo -n "your_new_gemini_api_key" | gcloud secrets versions add gemini-api-key --data-file=-

# 3. Verify the secret was updated
gcloud secrets versions list gemini-api-key

# 4. (If first time) Grant access to App Engine service account
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Restart Your Application

After updating the secret in Secret Manager, you need to restart your application to pick up the new key:

**For App Engine:**
```bash
# Deploy a new version to pick up the updated secret
gcloud app deploy
```

**For Cloud Run:**
```bash
# Get your region
REGION=us-central1  # Replace with your actual region

# Force a new revision to pick up the updated secret
gcloud run services update cineman --region $REGION
```

---

### Method B: Update Environment Variables Directly

If your application uses environment variables instead of Secret Manager, use these commands:

#### For App Engine:

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Update the environment variable and deploy
gcloud app deploy --set-env-vars GEMINI_API_KEY=your_new_gemini_api_key
```

**Note:** You can also update other API keys at the same time:
```bash
gcloud app deploy --set-env-vars \
  GEMINI_API_KEY=your_new_gemini_api_key,\
  TMDB_API_KEY=your_tmdb_key,\
  OMDB_API_KEY=your_omdb_key
```

#### For Cloud Run:

```bash
# Set your project and region
gcloud config set project YOUR_PROJECT_ID
REGION=us-central1  # Replace with your actual region

# Update the environment variable
gcloud run services update cineman \
  --region $REGION \
  --set-env-vars GEMINI_API_KEY=your_new_gemini_api_key
```

**To update multiple keys:**
```bash
gcloud run services update cineman \
  --region $REGION \
  --set-env-vars GEMINI_API_KEY=your_new_key,TMDB_API_KEY=your_tmdb_key,OMDB_API_KEY=your_omdb_key
```

---

### Method C: Using the Deployment Script

If you prefer an interactive approach, use the deployment script:

```bash
# 1. Navigate to the repository
cd /path/to/cineman

# 2. Export your new API key
export GEMINI_API_KEY="your_new_gemini_api_key"
export TMDB_API_KEY="your_tmdb_key"  # Optional: keep existing
export OMDB_API_KEY="your_omdb_key"  # Optional: keep existing

# 3. Run the deployment script
./scripts/deploy_gcp.sh
```

The script will:
- ✅ Detect your current deployment type (App Engine or Cloud Run)
- ✅ Update the environment variables
- ✅ Deploy the new configuration

---

## Step 2: Verify the Update

After updating the API key, verify that your application is working correctly:

### 1. Check Application Health

```bash
# For App Engine
curl https://YOUR_PROJECT_ID.uc.r.appspot.com/health

# For Cloud Run
curl YOUR_CLOUD_RUN_URL/health
```

Expected response:
```json
{"status":"healthy","service":"cineman"}
```

### 2. Test the Application

1. Open your application URL in a browser
2. Try making a movie recommendation request
3. Verify that the AI responds correctly

### 3. Check Logs for Errors

**App Engine:**
```bash
gcloud app logs tail -s default
```

**Cloud Run:**
```bash
gcloud run services logs read cineman --region YOUR_REGION --limit 50
```

Look for messages like:
- ✅ `"Loaded GEMINI_API_KEY from Secret Manager"` (if using Secret Manager)
- ❌ Any errors related to API key authentication

---

## Step 3: Revoke the Old API Key (Optional but Recommended)

For security best practices, revoke the old API key after confirming the new one works:

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Find the old API key in your list
3. Click the **Delete** or **Revoke** button
4. Confirm the deletion

**Important:** Only revoke the old key after confirming the new one is working!

---

## Troubleshooting

### Issue: Application returns "API key not configured" error

**Solution:**
- Verify the secret was updated: `gcloud secrets versions list gemini-api-key`
- Check if the application was restarted after updating the secret
- Review application logs for specific error messages

### Issue: "Permission denied" when accessing Secret Manager

**Solution:**
```bash
# Verify service account has access
gcloud secrets get-iam-policy gemini-api-key

# If not, grant access
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: Changes not taking effect

**Solution:**
- For Secret Manager: Redeploy the application (`gcloud app deploy` or `gcloud run services update`)
- For environment variables: The deployment command should have applied changes immediately
- Clear browser cache and try again
- Check logs for any startup errors

### Issue: Old API key still being used

**Solution:**
- Verify the secret version: `gcloud secrets versions list gemini-api-key`
- Ensure you're accessing "latest" version in your code
- Force a new deployment to pick up changes
- Check if any environment variable is overriding the secret

---

## Security Best Practices

✅ **Do:**
- Use Secret Manager for production deployments
- Rotate API keys regularly (every 90 days recommended)
- Keep API keys in secure storage
- Use different keys for development and production
- Monitor API usage in Google AI Studio
- Revoke old keys after successful rotation

❌ **Don't:**
- Hardcode API keys in source code
- Commit API keys to version control
- Share API keys in chat or email
- Use production keys for development/testing
- Keep unused or compromised keys active

---

## Quick Reference

### Check Current Secret Version
```bash
gcloud secrets versions list gemini-api-key
```

### View Secret Metadata (not the value)
```bash
gcloud secrets describe gemini-api-key
```

### Check Who Has Access to the Secret
```bash
gcloud secrets get-iam-policy gemini-api-key
```

### Test API Key Locally
```bash
export GEMINI_API_KEY="your_new_key"
python -c "import os; from langchain_google_genai import ChatGoogleGenerativeAI; print(ChatGoogleGenerativeAI(model='gemini-2.5-flash', google_api_key=os.getenv('GEMINI_API_KEY')).invoke('Hello').content)"
```

---

## Related Documentation

- [API Keys Configuration Guide](../wiki/API-Keys.md)
- [GCP Deployment Guide](GCP_DEPLOYMENT.md)
- [GCP Quick Start](GCP_QUICK_START.md)
- [Google Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

---

## Need More Help?

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting Guide](../wiki/Troubleshooting.md)
2. Review GCP logs for specific error messages
3. Verify all prerequisites are met
4. Consult the [GCP Support Documentation](https://cloud.google.com/support)

---

**✅ That's it! Your Gemini API key on GCP has been updated successfully!** 🎬✨
