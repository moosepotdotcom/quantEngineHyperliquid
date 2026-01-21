#!/bin/bash
echo "🚀 Deploying Mandalorian Phase 3 (Hybrid Mode) to Cloud Run..."

# Set Project ID
PROJECT_ID=$(gcloud config get-value project)
echo "Using Project ID: $PROJECT_ID"

# Build Container
echo "🔨 Building Container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/mandalorian-phase3 .

# Deploy to Cloud Run
echo "🚢 Deploying Service..."
gcloud run deploy mandalorian-phase3 \
    --image gcr.io/$PROJECT_ID/mandalorian-phase3 \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --timeout 3600 \
    --concurrency 1

echo "✅ Deployment Complete! The Mandalorian is hunting."
