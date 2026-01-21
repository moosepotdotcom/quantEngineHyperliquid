#!/bin/bash

# Mandalorian Engine - Cloud Run Deployment Script

set -e

PROJECT_ID="graphical-fort-427204-t3"
REGION="us-central1"
SERVICE_NAME="mandalorian-engine"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🛡️ Deploying Mandalorian Engine to Cloud Run"
echo "=============================================="

# Build and push image
echo "📦 Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME} --project ${PROJECT_ID}

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --memory 2Gi \
  --cpu 2 \
  --port 5001 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --timeout 3600 \
  --project ${PROJECT_ID}

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --format 'value(status.url)' \
  --project ${PROJECT_ID})

echo ""
echo "✅ Deployment complete!"
echo "📡 Dashboard URL: ${SERVICE_URL}"
echo "🔐 Login: mandalorian / thisIsTheWay2026"
echo ""
echo "📊 View logs:"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --limit 50 --project ${PROJECT_ID}"
