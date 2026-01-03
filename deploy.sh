#!/bin/bash
set -e

echo "🚀 Deploying Quant Engine to Cloud Run..."

# Build and deploy
gcloud builds submit --config cloudbuild.yaml

echo "✅ Deployment complete!"
echo "📊 View logs: gcloud run services logs read quant-engine-hl --region us-central1"
