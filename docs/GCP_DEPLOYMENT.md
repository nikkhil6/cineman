# 🚀 Deploying Cineman to Google Cloud Platform (GCP)

This guide provides complete instructions for deploying the Cineman application to GCP. Two deployment options are available:

1. **Google App Engine** - Easiest, fully managed PaaS (Recommended for beginners)
2. **Google Cloud Run** - Container-based, more flexible, scales to zero

## Prerequisites

### 1. GCP Account Setup
- Create a Google Cloud account at [https://cloud.google.com](https://cloud.google.com)
- Create a new project or select an existing one
- Enable billing for your project (required for deployment)

### 2. Install Google Cloud SDK
Download and install the `gcloud` CLI tool:

**Linux/macOS:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows:**
Download installer from [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

### 3. Initialize gcloud
```bash
gcloud init
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

### 4. API Keys Required
Ensure you have these API keys ready:
- **GEMINI_API_KEY**: [Get from Google AI Studio](https://makersuite.google.com/app/apikey)
- **TMDB_API_KEY**: [Get from TMDB](https://www.themoviedb.org/settings/api)
- **OMDB_API_KEY**: [Get from OMDb](http://www.omdbapi.com/apikey.aspx)

---

## Option 1: Deploy to Google App Engine (Recommended)

App Engine is a fully managed platform that automatically handles infrastructure, scaling, and monitoring.

### Step 1: Enable Required APIs

```bash
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 2: Create App Engine Application

```bash
# Choose a region (e.g., us-central, europe-west, asia-northeast1)
gcloud app create --region=us-central
```

**Note:** You can only create one App Engine app per project, and the region cannot be changed later.

### Step 3: Configure Environment Variables

**Option A: Set during deployment**
```bash
gcloud app deploy --set-env-vars \
  GEMINI_API_KEY=your_gemini_api_key,\
  TMDB_API_KEY=your_tmdb_api_key,\
  OMDB_API_KEY=your_omdb_api_key
```

**Option B: Update app.yaml (NOT recommended for production)**
Edit `app.yaml` and add your keys (do not commit this to Git):
```yaml
env_variables:
  GEMINI_API_KEY: "your_gemini_api_key"
  TMDB_API_KEY: "your_tmdb_api_key"
  OMDB_API_KEY: "your_omdb_api_key"
```

Then deploy:
```bash
gcloud app deploy
```

### Step 4: View Your Application

```bash
gcloud app browse
```

Or visit: `https://YOUR_PROJECT_ID.uc.r.appspot.com`

### Step 5: View Logs

```bash
gcloud app logs tail -s default
```

### Step 6: Database Configuration (Important!)

By default, the app uses a temporary SQLite database in `/tmp` which means:
- ⚠️ **Data is lost when instances restart**
- ⚠️ **Each instance has its own database**

**For production use with persistent data**, configure Cloud SQL:
See the **[GCP Database Setup Guide](GCP_DATABASE_SETUP.md)** for detailed instructions.

**Quick Setup:**
```bash
# Create Cloud SQL instance
gcloud sql instances create cineman-db --database-version=POSTGRES_15 --tier=db-f1-micro --region=us-central1

# Then deploy with DATABASE_URL
gcloud app deploy --set-env-vars \
  DATABASE_URL="postgresql://user:pass@/cineman?host=/cloudsql/PROJECT:REGION:cineman-db",\
  GEMINI_API_KEY=your_key,\
  TMDB_API_KEY=your_key,\
  OMDB_API_KEY=your_key
```

### Managing Your App Engine Deployment

**Update environment variables:**
```bash
gcloud app deploy --set-env-vars GEMINI_API_KEY=new_key
```

> 💡 **Tip:** For detailed instructions on updating your Gemini API key, see the [Update Gemini API Key Guide](UPDATE_GEMINI_API_KEY.md).

**Check app status:**
```bash
gcloud app describe
```

**View instances:**
```bash
gcloud app instances list
```

---

## Option 2: Deploy to Google Cloud Run

Cloud Run is a container-based platform that scales automatically and only charges when requests are being handled.

### Step 1: Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 2: Build and Push Container Image

```bash
# Set your project ID
export PROJECT_ID=$(gcloud config get-value project)

# Build the Docker image using Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/cineman

# Or build locally and push
# docker build -t gcr.io/$PROJECT_ID/cineman .
# docker push gcr.io/$PROJECT_ID/cineman
```

### Step 3: Deploy to Cloud Run

**Option A: Deploy with environment variables in command**
```bash
gcloud run deploy cineman \
  --image gcr.io/$PROJECT_ID/cineman \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_gemini_api_key,TMDB_API_KEY=your_tmdb_api_key,OMDB_API_KEY=your_omdb_api_key \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 0 \
  --timeout 300
```

**Option B: Use Cloud Run YAML configuration**
```bash
# First deploy without env vars
gcloud run services replace cloudrun.yaml --region us-central1

# Then set environment variables
gcloud run services update cineman \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=your_key,TMDB_API_KEY=your_key,OMDB_API_KEY=your_key
```

### Step 4: Get Service URL

```bash
gcloud run services describe cineman --region us-central1 --format 'value(status.url)'
```

### Step 5: View Logs

```bash
gcloud run services logs read cineman --region us-central1
```

### Managing Your Cloud Run Deployment

**Update service:**
```bash
# Rebuild and redeploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/cineman
gcloud run deploy cineman --image gcr.io/$PROJECT_ID/cineman --region us-central1
```

**Update environment variables:**
```bash
gcloud run services update cineman \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=new_key
```

> 💡 **Tip:** For detailed instructions on updating your Gemini API key, see the [Update Gemini API Key Guide](UPDATE_GEMINI_API_KEY.md).

**Scale configuration:**
```bash
gcloud run services update cineman \
  --region us-central1 \
  --min-instances 1 \
  --max-instances 20
```

---

## Using Google Secret Manager (Recommended for Production)

For better security, store API keys in Secret Manager instead of environment variables.

### Step 1: Enable Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com
```

### Step 2: Create Secrets

```bash
# Create secrets
echo -n "your_gemini_api_key" | gcloud secrets create gemini-api-key --data-file=-
echo -n "your_tmdb_api_key" | gcloud secrets create tmdb-api-key --data-file=-
echo -n "your_omdb_api_key" | gcloud secrets create omdb-api-key --data-file=-

# Grant access to App Engine service account
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding tmdb-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding omdb-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 3: Update Application Code

Modify `cineman/chain.py` and `cineman/tools/*.py` to fetch secrets:

```python
from google.cloud import secretmanager

def get_secret(secret_id):
    """Fetch secret from Google Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')

# Use in code
gemini_api_key = os.getenv("GEMINI_API_KEY") or get_secret("gemini-api-key")
```

---

## Monitoring and Debugging

### View Application Logs

**App Engine:**
```bash
gcloud app logs tail -s default
```

**Cloud Run:**
```bash
gcloud run services logs read cineman --region us-central1 --limit 50
```

### Check Health Endpoint

```bash
curl https://YOUR_APP_URL/health
```

### View Metrics in GCP Console

1. Go to [GCP Console](https://console.cloud.google.com)
2. Navigate to **App Engine** or **Cloud Run**
3. Select your service
4. View metrics: requests, latency, errors, CPU, memory

### Enable Cloud Monitoring

```bash
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com
```

---

## Cost Optimization

### App Engine
- Uses **automatic scaling** with min 0 instances (scales to zero when idle)
- First 28 instance hours per day are free
- Pay per instance hour after free tier

### Cloud Run
- **Charges only when handling requests**
- First 2 million requests per month are free
- 180,000 GB-seconds of memory free per month
- Scales to zero when not in use

### Tips to Reduce Costs
1. Set `min_instances: 0` to scale to zero when idle
2. Use appropriate memory/CPU limits
3. Set reasonable timeout values
4. Enable request timeout (120-300 seconds)
5. Monitor usage in GCP Console

---

## Custom Domain Setup

### For App Engine
```bash
gcloud app domain-mappings create yourdomain.com
```

### For Cloud Run
```bash
gcloud run domain-mappings create \
  --service cineman \
  --domain yourdomain.com \
  --region us-central1
```

Then update your DNS records as instructed by GCP.

---

## Continuous Deployment with GitHub Actions

Create `.github/workflows/deploy-gcp.yml`:

```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - id: auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'
      
      - name: Deploy to App Engine
        run: |
          gcloud app deploy --quiet --set-env-vars \
            GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }},\
            TMDB_API_KEY=${{ secrets.TMDB_API_KEY }},\
            OMDB_API_KEY=${{ secrets.OMDB_API_KEY }}
```

---

## Troubleshooting

### Issue: "Permission denied" errors

**Solution:**
```bash
gcloud auth application-default login
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/editor"
```

### Issue: "Module not found" errors during deployment

**Solution:**
- Ensure all dependencies are in `requirements.txt`
- Check `.gcloudignore` doesn't exclude necessary files
- Verify Python version in `app.yaml` matches your local version

### Issue: "Service unavailable" or 502 errors

**Solution:**
- Check application logs: `gcloud app logs tail -s default`
- Verify environment variables are set correctly
- Ensure `/health` endpoint returns 200 OK
- Check if API keys are valid

### Issue: Deployment takes too long or times out

**Solution:**
```bash
# Increase timeout
gcloud config set app/cloud_build_timeout 1200

# Or specify during deployment
gcloud app deploy --timeout=20m
```

### Issue: API rate limits or quota exceeded

**Solution:**
- Check GCP Console → IAM & Admin → Quotas
- Request quota increases if needed
- Implement caching in your application

---

## Comparison: App Engine vs Cloud Run

| Feature | App Engine | Cloud Run |
|---------|------------|-----------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ Very Easy | ⭐⭐⭐⭐ Easy |
| **Flexibility** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Very Flexible |
| **Cost (Low Traffic)** | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| **Scaling** | Automatic | Automatic |
| **Cold Starts** | Moderate | Fast |
| **Custom Domains** | ✅ Yes | ✅ Yes |
| **Container Support** | Limited | ✅ Full |
| **Best For** | Traditional web apps | Microservices, APIs |

**Recommendation:**
- **App Engine**: If you want the simplest deployment with minimal configuration
- **Cloud Run**: If you need more control, better cost efficiency, or already use Docker

---

## Next Steps

After deployment:
1. ✅ Test your application at the provided URL
2. ✅ Set up custom domain (optional)
3. ✅ Configure monitoring and alerts
4. ✅ Set up continuous deployment (optional)
5. ✅ Review and optimize costs
6. ✅ Enable Cloud Armor for DDoS protection (optional)

## Support and Resources

- [GCP App Engine Documentation](https://cloud.google.com/appengine/docs)
- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GCP Console](https://console.cloud.google.com)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)

---

**Need Help?** File an issue on the repository or consult GCP support documentation.

🎬 Enjoy your Cineman app on Google Cloud! ✨
