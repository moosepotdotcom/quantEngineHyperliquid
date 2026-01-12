# Quant Engine - Cloud Deployment & Monitoring Guide

## 📊 Backtest Trade Data

The backtest results have been exported to:
- **CSV**: `quant_engine/data/winner_hunter_1h_backtest_trades.csv`
- **JSON**: `quant_engine/data/winner_hunter_1h_backtest_trades.json`

### Backtest Summary
- **Total Trades**: 82
- **Win Rate**: 100%
- **Total PnL**: $107,000.06
- **Avg PnL/Trade**: $1,304.88
- **Avg Confidence**: 97.22%

Each trade record includes:
- Trade ID
- Entry/Exit timestamps
- Entry/Exit prices
- Take Profit price
- Stop Loss price
- Confidence level
- Outcome (WIN/LOSS)
- PnL (dollars and %)
- Technical indicators (RSI, MACD, ATR%)

---

## ☁️ Cloud Deployment

### Prerequisites
```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### Deploy to Google Cloud Run

```bash
# 1. Navigate to project directory
cd /Users/alifiyaa/Downloads/mandalorianNBox

# 2. Edit deploy_quant.sh with your project ID
# Replace "your-project-id" with your actual GCP project ID

# 3. Run deployment
./deploy_quant.sh
```

The deployment script will:
1. Build Docker image with all models and dependencies
2. Push to Google Container Registry
3. Deploy to Cloud Run with 2GB RAM, 2 CPUs
4. Set timeout to 3600s (1 hour per request)

---

## 📊 Monitoring the Live Engine

### Option 1: Cloud Run Logs (Real-time)

```bash
# Stream live logs
gcloud run services logs tail quant-engine --region us-central1 --follow

# View recent logs
gcloud run services logs read quant-engine --region us-central1 --limit 100
```

### Option 2: Cloud Logging Console

1. Go to: https://console.cloud.google.com/logs
2. Select your project
3. Filter by: `resource.type="cloud_run_revision"`
4. Search for: `quant-engine`

### Option 3: Download Trade Logs

Trade logs are saved to `/app/logs/` in the container. To access:

```bash
# Get running instance
gcloud run services describe quant-engine --region us-central1

# Execute command in container (if supported)
gcloud run services proxy quant-engine --region us-central1
```

### Option 4: Cloud Storage Integration (Recommended)

Add to `full_sandbox.py` to upload logs to Cloud Storage:

```python
from google.cloud import storage

def upload_logs_to_gcs(bucket_name='quant-engine-logs'):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Upload trade logs
    blob = bucket.blob(f'trades_{datetime.now().strftime("%Y%m%d")}.json')
    blob.upload_from_filename('logs/trades_*.json')
```

---

## 🔔 Monitoring Checklist

### What to Monitor:

1. **Trade Signals**
   - Look for: `🎉 TRADE SIGNAL DETECTED!`
   - Shows: Entry price, confidence, TP/SL targets

2. **Confidence Levels**
   - Look for: `Confidence: X.XX%`
   - Alert if: Confidence stays <50% for >24 hours

3. **Position Status**
   - Look for: `📊 OPEN POSITIONS`
   - Shows: Unrealized PnL, distance to TP/SL

4. **Trade Exits**
   - Look for: `📝 TRADE LOGGED - EXIT`
   - Shows: Final PnL, win/loss result

5. **System Health**
   - Look for: `✅ Winner Hunter (1H) loaded`
   - Alert if: Model loading fails

### Alert Patterns:

```bash
# Trade detected
grep "TRADE SIGNAL DETECTED" logs.txt

# Wins
grep "Result: WIN" logs.txt

# Losses
grep "Result: LOSS" logs.txt

# High confidence signals
grep "Confidence: 9[5-9]" logs.txt
```

---

## 📈 Performance Tracking

### Daily Summary Script

Create `check_performance.sh`:

```bash
#!/bin/bash
# Download and analyze today's trades

DATE=$(date +%Y%m%d)
LOG_FILE="trades_${DATE}.json"

# Download from cloud (if using GCS)
gsutil cp gs://quant-engine-logs/${LOG_FILE} .

# Analyze
python3 << EOF
import json

with open('${LOG_FILE}') as f:
    trades = json.load(f)

wins = [t for t in trades if t['pnl']['result'] == 'WIN']
losses = [t for t in trades if t['pnl']['result'] == 'LOSS']

print(f"📊 Daily Summary - {DATE}")
print(f"   Total Trades: {len(trades)}")
print(f"   Wins: {len(wins)}")
print(f"   Losses: {len(losses)}")
print(f"   Win Rate: {len(wins)/len(trades)*100:.1f}%")
print(f"   Total PnL: \${sum([t['pnl']['dollars'] for t in trades]):,.2f}")
EOF
```

---

## 🚨 Troubleshooting

### Container Not Starting
```bash
# Check build logs
gcloud builds list --limit=5

# View specific build
gcloud builds log BUILD_ID
```

### High Memory Usage
```bash
# Increase memory allocation
gcloud run services update quant-engine \
  --memory 4Gi \
  --region us-central1
```

### Timeout Issues
```bash
# Increase timeout
gcloud run services update quant-engine \
  --timeout 7200 \
  --region us-central1
```

---

## 📞 Quick Commands

```bash
# Deploy
./deploy_quant.sh

# View logs
gcloud run services logs tail quant-engine --region us-central1 --follow

# Check status
gcloud run services describe quant-engine --region us-central1

# Stop service
gcloud run services delete quant-engine --region us-central1

# Update configuration
gcloud run services update quant-engine --memory 4Gi --region us-central1
```

---

## ✅ Deployment Checklist

- [ ] GCP project created
- [ ] Cloud Run API enabled
- [ ] Container Registry API enabled
- [ ] `deploy_quant.sh` updated with project ID
- [ ] Models present in `quant_engine/models/`
- [ ] Deployment script executed
- [ ] Logs streaming successfully
- [ ] First signal detected and logged
- [ ] Trade logging working
- [ ] Monitoring alerts configured
