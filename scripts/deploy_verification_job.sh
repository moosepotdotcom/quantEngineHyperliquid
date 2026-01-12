#!/bin/bash
# deploy_verification_job.sh
# Deploys the manual_test_trade.py as a one-off Cloud Run Job

echo "🚀 Deploying Verification Job..."

# Ensure .env is ready
cp .env.live_trading ADAPTIVE_SHIELD_V1_PRODUCTION/.env

# Deploy Job
gcloud run jobs deploy verification-trade \
  --source ADAPTIVE_SHIELD_V1_PRODUCTION \
  --command python \
  --args manual_test_trade.py \
  --region us-central1 \
  --task-timeout 5m \
  --set-env-vars="ENABLE_LIVE_TRADING=true"

echo "✅ Job Deployed. Executing now..."

# Execute Job
gcloud run jobs execute verification-trade --region us-central1 --wait

echo "📋 Fetching Logs..."
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=verification-trade" --limit 20 --format="value(textPayload)"
