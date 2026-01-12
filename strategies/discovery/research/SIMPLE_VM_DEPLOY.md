# 🚀 SIMPLE VM DEPLOYMENT GUIDE

Cloud Run isn't working well for our trading bot (too many dependencies, startup timeout issues).

## ✅ RECOMMENDED: Use Compute Engine VM

### Option 1: Create VM via Console (Easiest)

1. Go to https://console.cloud.google.com/compute/instances
2. Click "CREATE INSTANCE"
3. Configure:
   - **Name**: `adaptive-shield-bot`
   - **Region**: `us-central1`
   - **Machine type**: `e2-medium` (2 vCPU, 4 GB RAM)
   - **Boot disk**: Ubuntu 22.04 LTS
   - **Firewall**: Allow HTTP/HTTPS (optional)
4. Click "CREATE"
5. Once created, click "SSH" to connect

### Option 2: Create VM via gcloud (Quick)

```bash
gcloud compute instances create adaptive-shield-bot \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB
```

---

## 📦 Deploy Bot to VM

### Step 1: SSH into VM

```bash
gcloud compute ssh adaptive-shield-bot --zone=us-central1-a
```

### Step 2: Upload Files

**From your local machine** (NOT in SSH):
```bash
cd /Users/alifiyaa/Downloads/quantEngineHyperliquid

gcloud compute scp --recurse ADAPTIVE_SHIELD_V1_PRODUCTION adaptive-shield-bot:/home/$(whoami)/ --zone=us-central1-a
```

### Step 3: Install and Run (In SSH)

```bash
# Navigate to bot directory
cd ~/ADAPTIVE_SHIELD_V1_PRODUCTION

# Install Python and dependencies
sudo apt-get update
sudo apt-get install -y python3-pip
pip3 install -r requirements.txt

# Create .env file with credentials
cat > .env << 'EOF'
HYPERLIQUID_WALLET_ADDRESS=0xb01713a6fcdc9419f37db065f0274ea172e4689e
HYPERLIQUID_API_SECRET=f06f4fd2a7516373cc4c8e99afd8c7445b4db0735de0fbe860cfa2b343bfc086
MAX_POSITION_SIZE=0.02
USE_TESTNET=false
EOF

# Test the bot (foreground)
python3 live_trading_engine.py --live --mainnet

# If it works, run in background:
# Ctrl+C to stop, then:
screen -S trading_bot
python3 live_trading_engine.py --live --mainnet
# Press Ctrl+A then D to detach
```

---

## 📊 Monitor the Bot

```bash
# Reattach to see live output
screen -r trading_bot

# Or check if running
ps aux | grep live_trading

# Check system resources
top
```

---

## 🛑 Stop the Bot

```bash
# Find the screen session
screen -ls

# Reattach
screen -r trading_bot

# Press Ctrl+C to stop bot
```

---

## 💰 Cost Estimate

- **e2-medium VM**: ~$25/month
- Much cheaper and more reliable than Cloud Run for 24/7 bots

---

**THIS IS THE RECOMMENDED APPROACH** for deploying trading bots!
