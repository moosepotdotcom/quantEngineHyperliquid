# 🔐 Create Secret for Live Trading Deployment

## ✅ Secret Manager Ready

Secret Manager API has been enabled successfully!

## 📝 Create Your Secret

**Run this command with YOUR private key:**

```bash
# Get your private key from Hyperliquid first, then run:
echo -n 'YOUR_PRIVATE_KEY_HERE' | gcloud secrets create hyperliquid-private-key \
    --data-file=- \
    --project=graphical-fort-427204-t3
```

## 🔑 How to Get Your Private Key

1. Go to https://app.hyperliquid.xyz
2. Click on Settings
3. Find "API Keys" or "Export Private Key"
4. Copy your private key
5. Use it in the command above

## ⚠️ Security Note

- Keep your private key secret!
- Never share it publicly
- The secret will be encrypted in Google Cloud

## 🚀 After Creating Secret

Once the secret is created, run:

```bash
cd /Users/alifiyaa/Downloads/quantEngineHyperliquid
./quick_deploy_live.sh
```

This will deploy live trading to Cloud Run!

---

**Create the secret, then you're ready to deploy!** 🎉
