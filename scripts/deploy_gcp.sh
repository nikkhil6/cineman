#!/bin/bash
# Quick deployment script for Google Cloud Platform
# This script helps deploy Cineman to either App Engine or Cloud Run

set -e

echo "🎬 Cineman GCP Deployment Script"
echo "================================"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project selected"
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📦 Current GCP Project: $PROJECT_ID"
echo ""

# Prompt for deployment type
echo "Choose deployment option:"
echo "1) App Engine (Recommended for beginners)"
echo "2) Cloud Run (More flexible, better for containers)"
read -p "Enter choice (1 or 2): " choice

# Check for API keys
if [ -z "$GEMINI_API_KEY" ] && [ -z "$TMDB_API_KEY" ] && [ -z "$OMDB_API_KEY" ]; then
    echo ""
    echo "⚠️  Environment variables not set"
    echo "You will need to provide API keys during deployment"
    echo ""
    read -p "Continue? (y/n): " continue_choice
    if [ "$continue_choice" != "y" ]; then
        exit 0
    fi
fi

if [ "$choice" = "1" ]; then
    echo ""
    echo "🚀 Deploying to App Engine..."
    echo ""
    
    # Enable required APIs
    echo "Enabling required APIs..."
    gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com
    
    # Check if App Engine app exists
    if ! gcloud app describe &>/dev/null; then
        echo ""
        echo "App Engine application not found. Creating one..."
        echo "Available regions: us-central, europe-west, asia-northeast1"
        read -p "Enter region (default: us-central): " region
        region=${region:-us-central}
        gcloud app create --region="$region"
    fi
    
    # Deploy with environment variables if available
    if [ -n "$GEMINI_API_KEY" ] && [ -n "$TMDB_API_KEY" ] && [ -n "$OMDB_API_KEY" ]; then
        echo "Deploying with environment variables..."
        gcloud app deploy --quiet --set-env-vars \
            GEMINI_API_KEY="$GEMINI_API_KEY",\
            TMDB_API_KEY="$TMDB_API_KEY",\
            OMDB_API_KEY="$OMDB_API_KEY"
    else
        echo ""
        echo "⚠️  Deploying without environment variables"
        echo "You will need to set them manually after deployment"
        echo ""
        gcloud app deploy --quiet
        echo ""
        echo "To set environment variables, run:"
        echo "gcloud app deploy --set-env-vars GEMINI_API_KEY=your_key,TMDB_API_KEY=your_key,OMDB_API_KEY=your_key"
    fi
    
    echo ""
    echo "✅ Deployment complete!"
    echo "🌐 Opening your application..."
    gcloud app browse

elif [ "$choice" = "2" ]; then
    echo ""
    echo "🚀 Deploying to Cloud Run..."
    echo ""
    
    # Enable required APIs
    echo "Enabling required APIs..."
    gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com
    
    # Select region
    read -p "Enter region (default: us-central1): " region
    region=${region:-us-central1}
    
    # Build container image
    echo ""
    echo "Building container image..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/cineman
    
    # Deploy to Cloud Run
    echo ""
    echo "Deploying to Cloud Run..."
    if [ -n "$GEMINI_API_KEY" ] && [ -n "$TMDB_API_KEY" ] && [ -n "$OMDB_API_KEY" ]; then
        gcloud run deploy cineman \
            --image gcr.io/$PROJECT_ID/cineman \
            --platform managed \
            --region "$region" \
            --allow-unauthenticated \
            --set-env-vars GEMINI_API_KEY="$GEMINI_API_KEY",TMDB_API_KEY="$TMDB_API_KEY",OMDB_API_KEY="$OMDB_API_KEY" \
            --memory 512Mi \
            --cpu 1 \
            --max-instances 10 \
            --min-instances 0 \
            --timeout 300
    else
        echo ""
        echo "⚠️  Deploying without environment variables"
        echo "You will need to set them manually after deployment"
        echo ""
        gcloud run deploy cineman \
            --image gcr.io/$PROJECT_ID/cineman \
            --platform managed \
            --region "$region" \
            --allow-unauthenticated \
            --memory 512Mi \
            --cpu 1 \
            --max-instances 10 \
            --min-instances 0 \
            --timeout 300
        echo ""
        echo "To set environment variables, run:"
        echo "gcloud run services update cineman --region $region --set-env-vars GEMINI_API_KEY=your_key,TMDB_API_KEY=your_key,OMDB_API_KEY=your_key"
    fi
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe cineman --region "$region" --format 'value(status.url)' 2>/dev/null || echo "")
    
    echo ""
    echo "✅ Deployment complete!"
    if [ -n "$SERVICE_URL" ]; then
        echo "🌐 Your application is available at: $SERVICE_URL"
        echo "🏥 Health check: $SERVICE_URL/health"
    fi

else
    echo "Invalid choice. Exiting."
    exit 1
fi

echo ""
echo "📊 To view logs, run:"
if [ "$choice" = "1" ]; then
    echo "   gcloud app logs tail -s default"
else
    echo "   gcloud run services logs read cineman --region $region"
fi
echo ""
echo "🎬 Deployment successful! Enjoy your Cineman app on GCP! ✨"
