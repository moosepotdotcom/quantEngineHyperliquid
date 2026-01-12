# ⚡ Quick Start Guide

Get your first bot running in 5 minutes!

## 🎯 Fast Setup (3 Steps)

### 1. Install Dependencies
```bash
# Create and activate environment (choose one):

# Option A: Conda
conda create --name algotrader python=3.8.5 -y
conda activate algotrader

# Option B: Venv
python3 -m venv algotrader
source algotrader/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure API Keys

**For HyperLiquid bots (recommended to start):**

Edit `dontshare.py`:
```python
private_key = '0xYOUR_METAMASK_PRIVATE_KEY'
```

**How to get your private key:**
- Open MetaMask
- Click account icon → Account Details → Export Private Key
- Enter password and copy the key

### 3. Run Your First Bot

```bash
# Start with the Bollinger Bands bot
python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py
```

## ⚙️ Before Running - Adjust Settings

Open `10_day10_bots/day10_hyperliquid/10_bollinger_bot.py` and review:

```python
symbol = 'WIF'          # Change to your preferred coin
target = 5              # Take profit: 5%
max_loss = -10          # Stop loss: -10%
leverage = 3            # 3x leverage
size = 1                # Position size
```

**⚠️ START WITH SMALL SIZES!**

## 🛑 To Stop the Bot

Press `Ctrl+C` in the terminal

## 📖 Need More Help?

See `SETUP_GUIDE.md` for detailed instructions and troubleshooting.

---

**Ready? Let's go! 🚀**



