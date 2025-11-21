#!/usr/bin/env bash
# Usage: ./create_secret.sh [PROJECT_ID]
set -euo pipefail

PROJECT_ID="${1:-cineman-477616}"
gcloud config set project "$PROJECT_ID"

printf "Enter GEMINI secret value (hidden): "
read -r -s GEMINI_KEY
printf "\n"

if ! gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
  echo -n "$GEMINI_KEY" | gcloud secrets create gemini-api-key --replication-policy="automatic" --data-file=-
  echo "Created secret gemini-api-key and added version."
else
  echo -n "$GEMINI_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
  echo "Added new version to gemini-api-key."
fi

gcloud secrets add-iam-policy-binding "projects/${PROJECT_ID}/secrets/gemini-api-key" \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Clear secret from environment
unset GEMINI_KEY
echo "Done. App Engine service account granted secretAccessor role."