# 🔄 Migration Guide: Render → Google Cloud Platform

This guide helps you migrate your Cineman deployment from Render to GCP.

## Why Migrate to GCP?

| Feature | Render | GCP App Engine | GCP Cloud Run |
|---------|--------|----------------|---------------|
| **Free Tier** | Limited free tier | 28 hrs/day free | 2M requests/month free |
| **Cold Starts** | ~30 seconds | ~10 seconds | ~5 seconds |
| **Scale to Zero** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Auto Scaling** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Custom Domains** | ✅ Free | ✅ Free | ✅ Free |
| **Monitoring** | Basic | Advanced (free) | Advanced (free) |
| **Log Retention** | 7 days | 30 days (free) | 30 days (free) |
| **Container Support** | ✅ Yes | Limited | ✅ Full |
| **Region Options** | Limited | Global | Global |
| **Cost (Low Traffic)** | $7/month | $0-5/month | $0-3/month |

## Migration Steps

### Step 1: Prepare Your GCP Account

1. **Create GCP Project**
   ```bash
   gcloud projects create PROJECT_ID --name="Cineman"
   gcloud config set project PROJECT_ID
   ```

2. **Enable Billing**
   - Visit [GCP Console](https://console.cloud.google.com)
   - Navigate to Billing → Link a billing account

3. **Install gcloud CLI**
   ```bash
   curl https://sdk.cloud.google.com | bash
   gcloud init
   ```

### Step 2: Export Render Environment Variables

From your Render dashboard:
1. Go to your service → Environment tab
2. Copy your environment variables:
   - `GEMINI_API_KEY`
   - `TMDB_API_KEY`
   - `OMDB_API_KEY`

### Step 3: Choose Deployment Method

#### Option A: App Engine (Recommended for simplicity)

```bash
# Enable APIs
gcloud services enable appengine.googleapis.com

# Create App Engine app
gcloud app create --region=us-central

# Deploy with environment variables
gcloud app deploy --set-env-vars \
  GEMINI_API_KEY="<from_render>",\
  TMDB_API_KEY="<from_render>",\
  OMDB_API_KEY="<from_render>"
```

#### Option B: Cloud Run (Better for cost optimization)

```bash
# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy (Cloud Run will build from source)
gcloud run deploy cineman \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="<from_render>",TMDB_API_KEY="<from_render>",OMDB_API_KEY="<from_render>"
```

### Step 4: Update DNS (If Using Custom Domain)

1. **Get your new GCP URL:**
   - App Engine: `https://PROJECT_ID.uc.r.appspot.com`
   - Cloud Run: Get from deployment output

2. **Map Custom Domain in GCP:**
   ```bash
   # App Engine
   gcloud app domain-mappings create yourdomain.com
   
   # Cloud Run
   gcloud run domain-mappings create \
     --service cineman \
     --domain yourdomain.com \
     --region us-central1
   ```

3. **Update DNS Records:**
   - Update your DNS provider with records shown by GCP
   - Wait for DNS propagation (5 minutes - 48 hours)

### Step 5: Test Your Deployment

```bash
# Test health endpoint
curl https://YOUR_GCP_URL/health

# Test the application
curl -X POST https://YOUR_GCP_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Recommend a sci-fi movie"}'
```

### Step 6: Set Up Monitoring

```bash
# Enable monitoring
gcloud services enable monitoring.googleapis.com logging.googleapis.com

# View logs
gcloud app logs tail -s default  # App Engine
gcloud run services logs read cineman --region us-central1  # Cloud Run
```

### Step 7: Decommission Render

Once you've verified everything works on GCP:

1. Test your GCP deployment thoroughly
2. Update any external integrations to point to GCP URL
3. Monitor for 24-48 hours
4. Delete or suspend your Render service

## Configuration Mapping

### Render → GCP Equivalents

| Render | GCP App Engine | GCP Cloud Run |
|--------|----------------|---------------|
| `render.yaml` | `app.yaml` | `cloudrun.yaml` |
| Build command | Automatic | `Dockerfile` or automatic |
| Start command | `entrypoint` in `app.yaml` | `CMD` in `Dockerfile` |
| Health check | `/health` route | `/health` route |
| Environment vars | `env_variables` in `app.yaml` | `--set-env-vars` flag |
| Dockerfile | Not used | Used directly |

### Files No Longer Needed on GCP

These Render-specific files are not needed for GCP (but safe to keep):
- `render.yaml` - Render configuration
- `Procfile` - Render process file
- `RENDER_DOCKER_SETUP.md` - Render docs

Files automatically excluded by `.gcloudignore`.

## GitHub Actions CI/CD

### Render Approach
- Automatic deploys from GitHub (push to main)

### GCP Approach (Similar automation available)

We've included GitHub Actions workflows:
- `.github/workflows/deploy-gcp-appengine.yml` - App Engine deploy
- `.github/workflows/deploy-gcp-cloudrun.yml` - Cloud Run deploy

**Setup:**
1. Create GCP Service Account:
   ```bash
   gcloud iam service-accounts create github-actions
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/editor"
   ```

2. Generate key and add to GitHub Secrets:
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=github-actions@PROJECT_ID.iam.gserviceaccount.com
   ```

3. Add these GitHub Secrets:
   - `GCP_SA_KEY` - Contents of `key.json`
   - `GCP_PROJECT_ID` - Your project ID
   - `GEMINI_API_KEY` - Your Gemini key
   - `TMDB_API_KEY` - Your TMDB key
   - `OMDB_API_KEY` - Your OMDb key

4. Push to `main` branch to trigger deployment

## Cost Comparison

### Render (Current)
- **Free Tier**: 750 hours/month, sleeps after inactivity
- **Paid**: $7/month minimum (always on)

### GCP App Engine
- **Free Tier**: 28 instance hours/day (840 hrs/month)
- **Paid**: ~$0.05/hour after free tier
- **Estimated**: $0-5/month for low traffic

### GCP Cloud Run
- **Free Tier**: 
  - 2 million requests/month
  - 180,000 GB-seconds of memory
  - 360,000 vCPU-seconds
- **Paid**: 
  - $0.00002400/request
  - $0.00001800/GB-second
- **Estimated**: $0-3/month for low traffic

**💡 Tip**: Cloud Run typically costs less for sporadic traffic because it scales to zero.

## Troubleshooting Migration Issues

### Issue: "Permission denied" during deployment

**Solution:**
```bash
gcloud auth login
gcloud auth application-default login
```

### Issue: Different behavior after migration

**Cause**: Environment differences
**Solution**: 
- Check environment variables are set correctly
- Review logs: `gcloud app logs tail -s default`
- Verify Python version matches (3.11 in `app.yaml`)

### Issue: Slower response times

**Cause**: Cold starts
**Solution**: 
- Set `min_instances: 1` in `app.yaml` (costs more)
- Use Cloud Run with minimum instances
- Accept cold starts as trade-off for lower cost

### Issue: Database/external service connections fail

**Cause**: Different IP ranges
**Solution**: 
- Whitelist GCP IP ranges in external services
- Use VPC connector for private resources

## Rollback Plan

If you need to rollback to Render:

1. Your Render configuration is still in the repo (`render.yaml`, `Dockerfile`)
2. Re-enable your Render service
3. Redeploy from Render dashboard
4. Update DNS back to Render

## Post-Migration Checklist

- [ ] GCP deployment successful
- [ ] Health check passes
- [ ] API integrations working (Gemini, TMDB, OMDb)
- [ ] Custom domain configured (if applicable)
- [ ] Monitoring and logging set up
- [ ] Cost alerts configured
- [ ] GitHub Actions CI/CD working
- [ ] Performance acceptable
- [ ] 24-48 hours of stable operation
- [ ] Render service decommissioned

## Support Resources

- [GCP Support](https://cloud.google.com/support)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Stack Overflow - GCP Tag](https://stackoverflow.com/questions/tagged/google-cloud-platform)

## Need Help?

Open an issue in the repository or consult GCP documentation.

---

**Welcome to GCP! 🎬✨**
