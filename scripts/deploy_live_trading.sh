#!/bin/bash
# Deploy Live Trading to Cloud Run
# This script handles secure deployment with Secret Manager

set -e

PROJECT_ID="graphical-fort-427204-t3"
SERVICE_NAME="quant-engine-hl"
REGION="us-central1"

echo "🚀 Deploying Live Trading to Cloud Run"
echo "========================================"
echo ""

# Step 1: Create secret (if not exists)
echo "📦 Step 1: Setting up Secret Manager..."
echo ""
echo "⚠️  IMPORTANT: You need to create the secret first!"
echo ""
echo "Run this command with YOUR private key:"
echo ""
echo "echo -n 'YOUR_PRIVATE_KEY_HERE' | gcloud secrets create hyperliquid-private-key \\"
echo "    --data-file=- \\"
echo "    --project=$PROJECT_ID"
echo ""
read -p "Have you created the secret? (yes/no): " secret_created

if [ "$secret_created" != "yes" ]; then
    echo "❌ Please create the secret first, then run this script again"
    exit 1
fi

# Step 2: Enable Secret Manager API
echo ""
echo "🔧 Step 2: Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Step 3: Grant access to secret
echo ""
echo "🔐 Step 3: Granting Cloud Run access to secret..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding hyperliquid-private-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

# Step 4: Choose deployment mode
echo ""
echo "🎯 Step 4: Choose deployment mode:"
echo ""
echo "1) Paper Trading Only (current mode)"
echo "2) Live Trading on TESTNET (recommended for testing)"
echo "3) Live Trading on MAINNET (real money!)"
echo ""
read -p "Enter choice (1-3): " mode_choice

case $mode_choice in
    1)
        ENABLE_LIVE="false"
        USE_TESTNET="true"
        MODE_NAME="Paper Trading"
        ;;
    2)
        ENABLE_LIVE="true"
        USE_TESTNET="true"
        MODE_NAME="Live Trading (TESTNET)"
        ;;
    3)
        echo ""
        echo "⚠️  WARNING: This will trade with REAL MONEY!"
        read -p "Are you sure? Type 'YES' to confirm: " confirm
        if [ "$confirm" != "YES" ]; then
            echo "❌ Deployment cancelled"
            exit 1
        fi
        ENABLE_LIVE="true"
        USE_TESTNET="false"
        MODE_NAME="Live Trading (MAINNET)"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

# Step 5: Deploy to Cloud Run
echo ""
echo "☁️  Step 5: Deploying to Cloud Run..."
echo "Mode: $MODE_NAME"
echo ""

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars="HYPERLIQUID_WALLET_ADDRESS=0xb01713a6fcdc9419f37db065f0274ea172e4689e,ENABLE_LIVE_TRADING=$ENABLE_LIVE,USE_TESTNET=$USE_TESTNET,MAX_POSITION_SIZE=0.01,MAX_LEVERAGE=2,DAILY_LOSS_LIMIT=5.0,WINNER_HUNTER_MIN_CONFIDENCE=0.30,MTF_SCALPER_MIN_CONFIDENCE=0.25" \
  --set-secrets="HYPERLIQUID_API_SECRET=hyperliquid-private-key:latest" \
  --project=$PROJECT_ID

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📊 Service Details:"
echo "   Name: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   Mode: $MODE_NAME"
echo ""
echo "🔍 Check status:"
echo "   gcloud run services describe $SERVICE_NAME --region $REGION"
echo ""
echo "📝 View logs:"
echo "   gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "🌐 Service URL:"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")
echo "   $SERVICE_URL"
echo ""
echo "🎯 Test endpoints:"
echo "   curl $SERVICE_URL"
echo "   curl $SERVICE_URL/status"
echo ""
