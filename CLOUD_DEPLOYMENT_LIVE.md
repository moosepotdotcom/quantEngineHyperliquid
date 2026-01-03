# 🚀 Cloud Deployment Guide - Live Trading

**Deploying AI Trading Bot with Live Execution to Google Cloud Run**

---

## 🔐 Step 1: Store Private Key Securely

### Create Secret in Google Cloud Secret Manager

```bash
# Set your project ID
export PROJECT_ID=graphical-fort-427204-t3

# Enable Secret Manager API (if not already enabled)
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Create secret for your private key
# IMPORTANT: Replace 'YOUR_PRIVATE_KEY_HERE' with your actual private key
echo -n "YOUR_PRIVATE_KEY_HERE" | gcloud secrets create hyperliquid-private-key \
    --data-file=- \
    --project=$PROJECT_ID

# Verify secret was created
gcloud secrets describe hyperliquid-private-key --project=$PROJECT_ID
```

---

## 📦 Step 2: Update Dockerfile

The Dockerfile has been updated to include:
- Live trading modules
- Environment variable support
- Secret mounting capability

---

## ☁️ Step 3: Deploy to Cloud Run

```bash
cd /Users/alifiyaa/Downloads/quantEngineHyperliquid

# Build and deploy with secrets
gcloud run deploy quant-engine-hl \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars="HYPERLIQUID_WALLET_ADDRESS=0xc692111d70b42e32e7b87abdd7dae7900b6cdde1,ENABLE_LIVE_TRADING=true,USE_TESTNET=true,MAX_POSITION_SIZE=0.01,MAX_LEVERAGE=2,DAILY_LOSS_LIMIT=5.0" \
  --set-secrets="HYPERLIQUID_API_SECRET=hyperliquid-private-key:latest" \
  --project=$PROJECT_ID
```

---

## 🔧 Configuration Options

### Environment Variables

Set these when deploying:

```bash
# Required
HYPERLIQUID_WALLET_ADDRESS=0xc692111d70b42e32e7b87abdd7dae7900b6cdde1
ENABLE_LIVE_TRADING=true

# Safety Settings
USE_TESTNET=true              # Start with testnet!
MAX_POSITION_SIZE=0.01        # BTC per trade
MAX_LEVERAGE=2                # Leverage limit
DAILY_LOSS_LIMIT=5.0          # USD loss limit

# Model Settings
WINNER_HUNTER_MIN_CONFIDENCE=0.30
MTF_SCALPER_MIN_CONFIDENCE=0.25
```

---

## 🎯 Deployment Modes

### Mode 1: Paper Trading Only (Current)
```bash
--set-env-vars="ENABLE_LIVE_TRADING=false"
```

### Mode 2: Live Trading on Testnet (Recommended First)
```bash
--set-env-vars="ENABLE_LIVE_TRADING=true,USE_TESTNET=true"
```

### Mode 3: Live Trading on Mainnet (After Testing)
```bash
--set-env-vars="ENABLE_LIVE_TRADING=true,USE_TESTNET=false"
```

---

## 🛡️ Security Best Practices

### Secret Management
- ✅ Private key stored in Secret Manager
- ✅ Never in code or logs
- ✅ Encrypted at rest
- ✅ Access controlled by IAM

### Access Control
```bash
# Grant Cloud Run service account access to secret
gcloud secrets add-iam-policy-binding hyperliquid-private-key \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
```

---

## 📊 Monitoring

### View Logs
```bash
# Real-time logs
gcloud run services logs tail quant-engine-hl --region us-central1

# Search for trades
gcloud run services logs read quant-engine-hl --region us-central1 | grep "TRADE"

# Check live trading status
gcloud run services logs read quant-engine-hl --region us-central1 | grep "Live Trading"
```

### Check Service Status
```bash
gcloud run services describe quant-engine-hl --region us-central1
```

---

## 🚨 Emergency Stop

### Stop Live Trading
```bash
# Update to disable live trading
gcloud run services update quant-engine-hl \
  --region us-central1 \
  --set-env-vars="ENABLE_LIVE_TRADING=false,EMERGENCY_STOP=true"
```

### Redeploy Previous Version
```bash
# List revisions
gcloud run revisions list --service quant-engine-hl --region us-central1

# Rollback to previous revision
gcloud run services update-traffic quant-engine-hl \
  --to-revisions=REVISION_NAME=100 \
  --region us-central1
```

---

## ✅ Verification Checklist

After deployment:

- [ ] Secret created in Secret Manager
- [ ] Service deployed successfully
- [ ] Environment variables set correctly
- [ ] Logs show "Live Trading: ENABLED"
- [ ] Testnet mode active
- [ ] First signal detected and logged
- [ ] Position management working

---

## 🎯 Testing Plan

### Phase 1: Testnet (24-48 hours)
1. Deploy with `USE_TESTNET=true`
2. Monitor for signals
3. Verify order execution
4. Check TP/SL management
5. Confirm P&L tracking

### Phase 2: Mainnet (After Success)
1. Update `USE_TESTNET=false`
2. Start with $10
3. Monitor closely
4. Scale gradually

---

## 📝 Cost Estimate

**Cloud Run:**
- Free tier: 2M requests/month
- Your usage: ~1,440 requests/day (60s intervals)
- Cost: ~$0 (within free tier)

**Secret Manager:**
- $0.06 per 10,000 access operations
- Your usage: ~1,440/day
- Cost: ~$0.01/month

**Total: ~$0.01/month** (essentially free!)

---

## 🎊 Summary

**What you get:**
- ✅ 24/7 automated trading
- ✅ Secure secret management
- ✅ Both paper and live trading
- ✅ Complete monitoring
- ✅ Emergency stop capability
- ✅ Minimal cost (~$0.01/month)

**Ready to deploy!** 🚀
