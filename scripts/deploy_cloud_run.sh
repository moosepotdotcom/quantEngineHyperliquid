#!/bin/bash
set -e

# Configuration
SERVICE_NAME="quant-engine-v1"
REGION="us-central1"
SOURCE_DIR="ADAPTIVE_SHIELD_V1_PRODUCTION"
ENV_FILE=".env.live_trading"

echo "🚀 Deploying Adaptive Shield V1 Production to Cloud Run..."
echo "--------------------------------------------------------"

# 1. Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: Source directory '$SOURCE_DIR' not found!"
    exit 1
fi

# 2. Prepare Environment File
echo "📝 Preparing configuration..."
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$SOURCE_DIR/.env"
    echo "✅ Copied $ENV_FILE to $SOURCE_DIR/.env"
else
    echo "⚠️  Warning: $ENV_FILE not found in root. Please ensure .env exists in $SOURCE_DIR or is empty."
fi

# 3. Deploy
echo "☁️  Deploying to Cloud Run (this may take a few minutes)..."
echo "   Settings: --no-cpu-throttling (Always CPU), 512Mi Memory, Min Instance 1"

gcloud run deploy "$SERVICE_NAME" \
    --source "$SOURCE_DIR" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --min-instances 1 \
    --max-instances 1 \
    --no-cpu-throttling \
    --quiet

echo "--------------------------------------------------------"
echo "✅ Deployment Complete!"
echo "   Service URL should be printed above."
echo "   Verify 'Win Rate: 92.9%' at the Service URL."
echo "   Check health at: [Service URL]/health"
echo "--------------------------------------------------------"
