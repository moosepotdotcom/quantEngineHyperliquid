# 🚀 Quick Live Trading Deployment

**Deploy live trading to Cloud Run in 3 steps**

---

## Current Status

✅ **Paper Trading:** Running on Cloud Run (quant-engine-hl)  
⏳ **Live Trading:** Ready to deploy (separate service)

---

## 🎯 Deploy Live Trading (3 Steps)

### Step 1: Create Secret with Your Private Key

```bash
# Replace YOUR_PRIVATE_KEY with your actual Hyperliquid private key
echo -n 'YOUR_PRIVATE_KEY_HERE' | gcloud secrets create hyperliquid-private-key \
    --data-file=- \
    --project=graphical-fort-427204-t3

# Grant access
gcloud secrets add-iam-policy-binding hyperliquid-private-key \
    --member="serviceAccount:535493956190-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=graphical-fort-427204-t3
```

### Step 2: Deploy Live Trading Service

```bash
cd /Users/alifiyaa/Downloads/quantEngineHyperliquid

# Deploy as SEPARATE service (won't affect paper trading)
gcloud run deploy quant-engine-hl-live \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars="HYPERLIQUID_WALLET_ADDRESS=0xb01713a6fcdc9419f37db065f0274ea172e4689e,ENABLE_LIVE_TRADING=true,USE_TESTNET=true,MAX_POSITION_SIZE=0.01,MAX_LEVERAGE=2,DAILY_LOSS_LIMIT=5.0" \
  --set-secrets="HYPERLIQUID_API_SECRET=hyperliquid-private-key:latest" \
  --project=graphical-fort-427204-t3
```

### Step 3: Verify Both Services Running

```bash
# Check paper trading (existing)
gcloud run services describe quant-engine-hl --region us-central1

# Check live trading (new)
gcloud run services describe quant-engine-hl-live --region us-central1
```

---

## 📊 You'll Have Two Services

### Service 1: Paper Trading (Existing)
```
Name: quant-engine-hl
Mode: Paper trading only
Status: Running ✅
URL: https://quant-engine-hl-535493956190.us-central1.run.app
```

### Service 2: Live Trading (New)
```
Name: quant-engine-hl-live
Mode: Live trading (testnet first)
Status: Deploy when ready
URL: Will be generated after deployment
```

---

## 🔄 Switch Between Testnet and Mainnet

### Currently on Testnet (Safe)
```bash
# Already set: USE_TESTNET=true
```

### Switch to Mainnet (Real Money)
```bash
gcloud run services update quant-engine-hl-live \
  --region us-central1 \
  --set-env-vars="USE_TESTNET=false"
```

---

## 🛑 Stop Live Trading (Keep Paper Running)

```bash
# Option 1: Delete live service
gcloud run services delete quant-engine-hl-live --region us-central1

# Option 2: Disable live trading
gcloud run services update quant-engine-hl-live \
  --region us-central1 \
  --set-env-vars="ENABLE_LIVE_TRADING=false"
```

---

## 📝 Summary

**What you get:**
- ✅ Paper trading continues uninterrupted
- ✅ Live trading as separate service
- ✅ Can start/stop live trading independently
- ✅ Both run simultaneously
- ✅ No interference between them

**Cost:** ~$0.02/month (both services within free tier)

---

**Ready to deploy when you add your private key!** 🚀
