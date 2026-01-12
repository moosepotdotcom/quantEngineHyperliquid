#!/bin/bash
# Quick Deploy - Live Trading (Separate Service)
# This deploys live trading WITHOUT affecting paper trading

PROJECT_ID="graphical-fort-427204-t3"
REGION="us-central1"

echo "🚀 Quick Deploy - Live Trading Service"
echo "======================================="
echo ""
echo "This will deploy a SEPARATE live trading service"
echo "Your paper trading (quant-engine-hl) will continue running"
echo ""

# Check if secret exists
echo "🔐 Checking for secret..."
if gcloud secrets describe hyperliquid-private-key --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Secret found: hyperliquid-private-key"
else
    echo "❌ Secret not found!"
    echo ""
    echo "Create it with:"
    echo "echo -n 'YOUR_PRIVATE_KEY' | gcloud secrets create hyperliquid-private-key --data-file=- --project=$PROJECT_ID"
    echo ""
    exit 1
fi

# Choose mode
echo ""
echo "🎯 Choose mode:"
echo "1) Testnet (recommended - fake money)"
echo "2) Mainnet (real money!)"
echo ""
read -p "Enter choice (1-2): " mode

if [ "$mode" == "1" ]; then
    USE_TESTNET="true"
    MODE_NAME="TESTNET"
elif [ "$mode" == "2" ]; then
    echo ""
    echo "⚠️  WARNING: Real money trading!"
    read -p "Type 'YES' to confirm: " confirm
    if [ "$confirm" != "YES" ]; then
        echo "❌ Cancelled"
        exit 1
    fi
    USE_TESTNET="false"
    MODE_NAME="MAINNET"
else
    echo "❌ Invalid choice"
    exit 1
fi

# Deploy
echo ""
echo "☁️  Deploying live trading service..."
echo "Mode: $MODE_NAME"
echo ""

gcloud run deploy quant-engine-hl-live \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars="HYPERLIQUID_WALLET_ADDRESS=0xC09589118faBf232f2aCb9d62a6467E3E584D170,ENABLE_LIVE_TRADING=true,USE_TESTNET=$USE_TESTNET,MAX_POSITION_SIZE=0.02,MAX_LEVERAGE=50,DAILY_LOSS_LIMIT=10.0,DESCRIPTION=Bidirectional Sentinel (Long/Short)" \
  --set-secrets="HYPERLIQUID_API_SECRET=hyperliquid-private-key:latest" \
  --project=$PROJECT_ID

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📊 Your Services:"
echo ""
echo "1. Paper Trading (unchanged):"
echo "   gcloud run services describe quant-engine-hl --region $REGION"
echo ""
echo "2. Live Trading (new):"
echo "   gcloud run services describe quant-engine-hl-live --region $REGION"
echo ""
echo "🔍 Check live trading status:"
LIVE_URL=$(gcloud run services describe quant-engine-hl-live --region $REGION --format="value(status.url)" 2>/dev/null || echo "pending")
echo "   curl $LIVE_URL/status"
echo ""
echo "📝 View live trading logs:"
echo "   gcloud run services logs tail quant-engine-hl-live --region $REGION"
echo ""
