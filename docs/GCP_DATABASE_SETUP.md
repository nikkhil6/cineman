# Database Configuration for GCP Deployment

## Problem
The movie interaction features (like/dislike/watchlist) use SQLite database which doesn't work properly on GCP App Engine because:
1. App Engine has an ephemeral file system - files are not persisted between deployments
2. Multiple instances can't share a single SQLite file
3. SQLite is designed for single-user, local applications

## Solutions

### Option 1: In-Memory SQLite (Quick Fix - Testing Only)
**Current Implementation** - The app now automatically uses `/tmp/cineman.db` when deployed to GCP.

**Pros:**
- No additional configuration needed
- Works immediately after deployment
- Good for testing and demos

**Cons:**
- ⚠️ Data is lost when instance restarts
- ⚠️ Each instance has its own database (data not shared)
- ⚠️ NOT suitable for production use

**No action needed** - This is automatically configured.

### Option 2: Cloud SQL (Recommended for Production)
Cloud SQL provides a fully managed PostgreSQL or MySQL database that persists data and can be shared across multiple instances.

#### Step 1: Create Cloud SQL Instance
```bash
# Create a PostgreSQL instance (recommended)
gcloud sql instances create cineman-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1

# Create a database
gcloud sql databases create cineman --instance=cineman-db

# Create a user
gcloud sql users create cineman-user \
    --instance=cineman-db \
    --password=YOUR_SECURE_PASSWORD
```

#### Step 2: Update requirements.txt
Add PostgreSQL driver:
```
psycopg2-binary>=2.9.0
```

Or for MySQL:
```
PyMySQL>=1.0.0
```

#### Step 3: Configure Database Connection

**For App Engine:**
Update `app.yaml`:
```yaml
env_variables:
  DATABASE_URL: "postgresql://cineman-user:YOUR_PASSWORD@/cineman?host=/cloudsql/YOUR_PROJECT:us-central1:cineman-db"
```

Get your connection string:
```bash
gcloud sql instances describe cineman-db --format="value(connectionName)"
# Output: YOUR_PROJECT:us-central1:cineman-db
```

**For Cloud Run:**
Update `cloudrun.yaml`:
```yaml
spec:
  template:
    spec:
      containers:
      - env:
        - name: DATABASE_URL
          value: "postgresql://cineman-user:YOUR_PASSWORD@/cineman?host=/cloudsql/YOUR_PROJECT:us-central1:cineman-db"
        - name: CLOUD_SQL_CONNECTION_NAME
          value: "YOUR_PROJECT:us-central1:cineman-db"
```

#### Step 4: Deploy
```bash
# App Engine
gcloud app deploy --set-env-vars \
  DATABASE_URL="postgresql://cineman-user:YOUR_PASSWORD@/cineman?host=/cloudsql/YOUR_PROJECT:us-central1:cineman-db",\
  GEMINI_API_KEY=your_key,\
  TMDB_API_KEY=your_key,\
  OMDB_API_KEY=your_key

# Cloud Run
./scripts/deploy_gcp.sh
```

### Option 3: Cloud Firestore (NoSQL Alternative)
For a serverless, NoSQL option, you could refactor to use Firestore instead of SQLAlchemy.

**Pros:**
- Fully serverless
- Auto-scaling
- No instance management

**Cons:**
- Requires code refactoring
- Different query model than SQL

This would require significant changes to `cineman/models.py` and `cineman/routes/api.py`.

## Current Behavior

The app now automatically detects the environment:

**Local Development:**
- Uses `sqlite:///cineman.db` (file in project root)
- Data persists between runs

**GCP Deployment:**
1. Checks for `DATABASE_URL` environment variable
2. If found → Uses Cloud SQL (PostgreSQL/MySQL)
3. If not found → Uses `sqlite:////tmp/cineman.db` (temporary)

**Environment Detection:**
- Checks `GAE_ENV` environment variable (App Engine)
- Checks `CLOUD_RUN_SERVICE` environment variable (Cloud Run)

## Testing After Deployment

### 1. Check Database Connection
Visit your app and try:
1. Like a movie
2. Add movie to watchlist
3. Click Watchlist button - should show your movies

### 2. Check Logs
```bash
# App Engine
gcloud app logs tail -s default

# Cloud Run
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

Look for:
- ✅ `"📋 Session Manager initialized successfully"`
- ✅ `"🎬 Movie Recommendation Chain loaded successfully"`
- ⚠️ `"WARNING: Using temporary SQLite database"` (if using /tmp)

### 3. Verify Database
```bash
# For Cloud SQL
gcloud sql connect cineman-db --user=cineman-user

# Then in PostgreSQL shell:
\c cineman
SELECT * FROM movie_interactions;
```

## Cost Considerations

**SQLite in /tmp:**
- FREE - No additional costs

**Cloud SQL db-f1-micro:**
- ~$10-15/month
- 0.6 GB RAM, shared CPU
- Suitable for small apps

**Cloud SQL db-g1-small:**
- ~$30-40/month
- 1.7 GB RAM, shared CPU
- Better performance

## Migration from SQLite to Cloud SQL

If you start with SQLite and want to migrate:

1. Export data (if any exists):
```python
# Run locally
from cineman.app import app
from cineman.models import db, MovieInteraction

with app.app_context():
    interactions = MovieInteraction.query.all()
    # Save to file or backup
```

2. Set up Cloud SQL (see Option 2)
3. Deploy with DATABASE_URL configured
4. Database tables are auto-created on first run

## Troubleshooting

### Issue: "No such table: movie_interactions"
**Cause:** Database not initialized
**Fix:** 
```python
# The app automatically calls db.create_all() on startup
# Check logs for errors during initialization
```

### Issue: "Data disappears after restart"
**Cause:** Using /tmp SQLite on GCP
**Fix:** Set up Cloud SQL (Option 2)

### Issue: "Database is locked"
**Cause:** SQLite can't handle concurrent writes
**Fix:** Use Cloud SQL for production (Option 2)

### Issue: Cloud SQL connection fails
**Check:**
1. Connection name is correct
2. Cloud SQL Admin API is enabled
3. App Engine service account has Cloud SQL Client role

```bash
# Enable API
gcloud services enable sqladmin.googleapis.com

# Grant permission
gcloud projects add-iam-policy-binding YOUR_PROJECT \
    --member="serviceAccount:YOUR_PROJECT@appspot.gserviceaccount.com" \
    --role="roles/cloudsql.client"
```

## Recommended Setup

**For Development/Testing:**
- Use local SQLite (automatic)

**For Production:**
- Use Cloud SQL PostgreSQL
- db-f1-micro for small apps
- Regular backups enabled
- High availability for critical apps

**For Serverless/Cost-Sensitive:**
- Consider Firestore (requires refactoring)
- Or accept data loss with /tmp SQLite

## Additional Resources

- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Connecting from App Engine](https://cloud.google.com/sql/docs/postgres/connect-app-engine-standard)
- [Connecting from Cloud Run](https://cloud.google.com/sql/docs/postgres/connect-run)
- [SQLAlchemy Engine Configuration](https://docs.sqlalchemy.org/en/14/core/engines.html)
