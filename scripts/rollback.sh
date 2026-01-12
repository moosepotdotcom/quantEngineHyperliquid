#!/bin/bash
set -e

# Quick rollback script
# Usage: ./rollback.sh [version]
# If no version specified, rolls back to previous revision

VERSION=$1

echo "========================================"
echo "🔄 ROLLBACK INITIATED"
echo "========================================"

if [ -z "$VERSION" ]; then
    echo "No version specified, finding previous revision..."
    
    # Get current and previous revisions
    CURRENT=$(gcloud run services describe quant-engine-hl \
        --region us-central1 \
        --format="value(status.latestCreatedRevisionName)")
    
    PREVIOUS=$(gcloud run revisions list \
        --service=quant-engine-hl \
        --region=us-central1 \
        --format="value(metadata.name)" \
        --limit=2 | tail -1)
    
    echo "Current:  $CURRENT"
    echo "Previous: $PREVIOUS"
    echo ""
    read -p "Rollback to $PREVIOUS? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    
    TARGET=$PREVIOUS
else
    # Rollback to specific version tag
    echo "Rolling back to version: $VERSION"
    TARGET=$VERSION
fi

echo "🔄 Switching traffic to $TARGET..."
gcloud run services update-traffic quant-engine-hl \
    --region us-central1 \
    --to-revisions $TARGET=100

echo "========================================"
echo "✅ Rollback Complete"
echo "========================================"
echo ""
echo "Active revision: $TARGET"
echo ""
echo "Monitor logs: python3 monitor_cloud.py"
