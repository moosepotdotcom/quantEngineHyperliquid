#!/bin/bash
set -e

# Versioned deployment script
# Usage: ./deploy_versioned.sh v1.0.5

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "❌ Error: Version tag required"
    echo "Usage: ./deploy_versioned.sh v1.0.5"
    exit 1
fi

echo "========================================"
echo "🚀 Deploying Version: $VERSION"
echo "========================================"

# Verify git tag exists
if ! git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "❌ Error: Git tag '$VERSION' does not exist"
    echo "Create it with: git tag -a $VERSION -m 'Release $VERSION'"
    exit 1
fi

# Verify we're on the tagged commit
CURRENT_COMMIT=$(git rev-parse HEAD)
TAG_COMMIT=$(git rev-parse "$VERSION")

if [ "$CURRENT_COMMIT" != "$TAG_COMMIT" ]; then
    echo "⚠️  Warning: Current HEAD is not at tag $VERSION"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run pre-deployment checks
echo "🔍 Running pre-deployment checks..."
python3 pre_deploy_check.py || {
    echo "❌ Pre-deployment checks failed"
    exit 1
}

# Build and deploy
echo "🏗️  Building Docker image..."
gcloud builds submit \
    --tag gcr.io/graphical-fort-427204-t3/quant-engine-hl:$VERSION \
    --timeout=20m

echo "🚀 Deploying to Cloud Run..."
gcloud run deploy quant-engine-hl \
    --image gcr.io/graphical-fort-427204-t3/quant-engine-hl:$VERSION \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars="ENABLE_LIVE_TRADING=true,USE_TESTNET=false,DEPLOYED_VERSION=$VERSION" \
    --set-secrets="HYPERLIQUID_API_SECRET=hyperliquid-private-key:latest" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --concurrency 1 \
    --min-instances 1 \
    --max-instances 1 \
    --tag $VERSION

# Record deployment
echo "📝 Recording deployment..."
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) - Deployed $VERSION - $(git log -1 --pretty=%B $VERSION | head -1)" >> deployments.log

echo "========================================"
echo "✅ Deployment Complete: $VERSION"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Monitor logs: python3 monitor_cloud.py"
echo "  2. Verify health: curl https://quant-engine-hl-xxx.run.app/health"
echo "  3. If issues, rollback: ./rollback.sh"
