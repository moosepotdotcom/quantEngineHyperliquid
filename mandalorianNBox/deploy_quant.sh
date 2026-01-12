#!/bin/bash
# Deploy Quant Engine to Google Cloud Run

PROJECT_ID="graphical-fort-427204-t3"
REGION="us-central1"
SERVICE_NAME="quant-engine"

echo "🚀 Deploying Quant Engine to Cloud Run..."

# Build and push image using cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml .

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 1 \
  --allow-unauthenticated

echo "✅ Deployment complete!"
echo "📊 View logs: gcloud run services logs read $SERVICE_NAME --region $REGION"
