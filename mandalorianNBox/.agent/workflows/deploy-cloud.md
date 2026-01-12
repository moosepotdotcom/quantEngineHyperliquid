---
description: Deploy the AI Trading Bot to Google Cloud Run
---

# Cloud Run Deployment Workflow

This workflow deploys the AI Trading Bot to Google Cloud Run. **Always validate before deploying!**

## Pre-Deployment Validation (REQUIRED)
// turbo
1. Run the validation script to check for missing dependencies:
```bash
python3 scripts/validate_deployment.py
```
If this fails, fix the missing dependencies in `requirements.txt` before proceeding!

## Deploy to Cloud Run

2. Build and push the container (this will take ~8-10 minutes):
```bash
gcloud builds submit --tag gcr.io/graphical-fort-427204-t3/ai-trading-bot --timeout=1800
```

3. Deploy the new container to Cloud Run:
```bash
gcloud run deploy ai-trading-bot \
    --image gcr.io/graphical-fort-427204-t3/ai-trading-bot \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 3600 \
    --min-instances 0 \
    --max-instances 1
```

## Post-Deployment Verification

4. Check the logs for errors:
```bash
gcloud run services logs read ai-trading-bot --region us-central1 --limit 50
```

5. Open the dashboard to verify it's working:
   - URL: https://ai-trading-bot-535493956190.us-central1.run.app

## Quick Restart (without rebuild)

If you just need to restart the container without rebuilding:
```bash
gcloud run services update ai-trading-bot --region us-central1 --update-env-vars RESTART_TRIGGER=$(date +%s)
```

## Key Files

- `requirements.txt` - All Python dependencies (MUST include all imports!)
- `Dockerfile` - Container build instructions
- `cloud_runner.py` - Entry point for cloud deployment
- `scripts/validate_deployment.py` - Pre-deployment validation script
