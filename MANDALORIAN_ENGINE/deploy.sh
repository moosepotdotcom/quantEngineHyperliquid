#!/bin/bash
# Deployment script for ML Engine to Google Cloud Run

set -e

PROJECT_ID="your-project-id"  # Update this
REGION="us-central1"
SERVICE_NAME="ml-engine-paperbot"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying ML Engine to Google Cloud Run"
echo "============================================"

# Build the container
echo "📦 Building container image..."
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 1 \
  --no-allow-unauthenticated

echo "✅ Deployment complete!"
echo "Service URL:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)'
