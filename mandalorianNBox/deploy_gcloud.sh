#!/bin/bash
# Deploy to Google Cloud Run

# Configuration
PROJECT_ID="your-gcp-project-id"  # <-- CHANGE THIS
REGION="us-central1"
SERVICE_NAME="ai-trading-bot"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "☁️ Deploying AI Trading Bot to Google Cloud Run..."
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Authenticate (if needed)
echo "🔑 Checking authentication..."
gcloud auth list

# Set project
echo "📁 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Build the container
echo "🐳 Building Docker image..."
gcloud builds submit --tag $IMAGE_NAME --dockerfile Dockerfile.cloudrun .

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 3600 \
    --min-instances 0 \
    --max-instances 1

echo ""
echo "✅ Deployment Complete!"
echo "=================================================="
echo "🌐 Your bot will be available at the URL shown above."
echo ""
echo "📊 To view logs:"
echo "   gcloud run logs read $SERVICE_NAME --region $REGION"
