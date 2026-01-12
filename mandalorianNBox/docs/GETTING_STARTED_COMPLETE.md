# 🎯 Complete Getting Started Guide

**Everything you need to go from zero to trading in one place.**

---

## 📋 What You Need

1. ✅ **Python 3.8+** (already installed on your Mac)
2. ✅ **MetaMask wallet** (free browser extension)
3. ✅ **Small amount of ETH** ($50-100 for testing)
4. ✅ **This codebase** (already downloaded)

---

## 🚀 Step-by-Step: From Zero to Trading

### Phase 1: Install MetaMask & Get Wallet (10 minutes)

#### Step 1.1: Install MetaMask
1. Go to: https://metamask.io/download
2. Click "Download" for Chrome/Brave/Edge
3. Click "Add to Chrome" → "Add Extension"
4. Click "Get Started" → "Create a Wallet"
5. **SAVE YOUR SEED PHRASE** (12 words) - write it down securely!
6. Set a password

#### Step 1.2: Add Arbitrum Network
1. Go to: https://app.hyperliquid.xyz
2. Click "Connect Wallet"
3. MetaMask will ask to add Arbitrum - click "Approve"
4. ✅ Network added!

#### Step 1.3: Get ETH on Arbitrum
**Option A: Bridge from Ethereum Mainnet**
1. Go to: https://bridge.arbitrum.io
2. Connect MetaMask
3. Make sure you're on Ethereum Mainnet
4. Enter amount (start with $50-100)
5. Click "Move funds to Arbitrum"
6. Wait 10-15 minutes for bridge

**Option B: Buy directly on Arbitrum**
- Use a DEX like Uniswap on Arbitrum
- Or buy on an exchange that supports Arbitrum withdrawals

**Minimum:** $50-100 for testing (use small amounts!)

---

### Phase 2: Get Your Private Key (2 minutes)

#### Step 2.1: Export Private Key
1. Open MetaMask extension
2. Click account icon (top right) → "Account Details"
3. Click "Export Private Key"
4. Enter your MetaMask password
5. **Copy the private key** (starts with `0x`)

**⚠️ SECURITY:** This key controls your wallet. Keep it secret!

#### Step 2.2: Add to Bot Config
1. Open `dontshare.py` in your project
2. Find: `private_key = 'YOUR_HYPERLIQUID_PRIVATE_KEY_HERE'`
3. Replace with your actual key:
   ```python
   private_key = '0xYOUR_ACTUAL_KEY_HERE'
   ```
4. Save the file

---

### Phase 3: Set Up Python Environment (5 minutes)

#### Step 3.1: Activate Environment
```bash
cd "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025"
source activate_env.sh
```

If that doesn't work:
```bash
source algotrader/bin/activate
```

#### Step 3.2: Verify Packages Installed
```bash
python test_setup.py
```

**Expected output:**
```
✅ All required packages are installed!
✅ dontshare.py - Configured
✅ HyperLiquid API - Connected
✅ All tests passed!
```

---

### Phase 4: Configure Your First Bot (5 minutes)

#### Step 4.1: Open Bot File
Open: `10_day10_bots/day10_hyperliquid/10_bollinger_bot.py`

#### Step 4.2: Adjust Settings
Find these lines and adjust:

```python
symbol = 'WIF'          # Change to: 'BTC', 'ETH', 'SOL', etc.
timeframe = '15m'       # Keep as is (15 minutes)
size = 1                # START SMALL! Use 0.1 or 0.5 for testing
target = 5              # Take profit: 5% (adjust as needed)
max_loss = -10          # Stop loss: -10% (adjust as needed)
leverage = 3            # Leverage: 3x (start with 1-3x)
max_positions = 1       # Keep as is
```

**⚠️ IMPORTANT:** 
- Start with `size = 0.1` or `size = 0.5` for testing
- Use low leverage (1-3x) initially
- Only trade what you can afford to lose

#### Step 4.3: Save the File

---

### Phase 5: Test Your Bot (2 minutes)

#### Step 5.1: Run Test Script
```bash
python test_setup.py
```

Make sure all checks pass!

#### Step 5.2: Verify Connection
```bash
python
```

Then type:
```python
import dontshare as d
from eth_account.signers.local import LocalAccount
import eth_account

account = eth_account.Account.from_key(d.private_key)
print(f"Wallet: {account.address}")
print("✅ Private key loaded successfully!")
```

Press `Ctrl+D` to exit Python.

---

### Phase 6: Run Your Bot! (Now!)

#### Step 6.1: Start the Bot
```bash
python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py
```

#### Step 6.2: What You'll See
You should see output like:
```
this is the ask for WIF 2.45
these are positions for WIF []
bollinger bands are tight: True
not in position we are quoteing a sell @ 2.45 and buy @ 2.44
just canceled all orders
just placed an order for 0.5 at 2.44
```

#### Step 6.3: Monitor Your Bot
- **Watch the terminal** for updates
- **Check HyperLiquid:** https://app.hyperliquid.xyz
- **Monitor positions** in real-time
- **The bot runs continuously** until you stop it

#### Step 6.4: Stop the Bot
Press `Ctrl+C` in the terminal

---

## ✅ Checklist: Are You Ready?

Before running live, make sure:

- [ ] MetaMask installed and set up
- [ ] Arbitrum network added to MetaMask
- [ ] ETH on Arbitrum (at least $50)
- [ ] Private key added to `dontshare.py`
- [ ] Environment activated (`source activate_env.sh`)
- [ ] Test script passes (`python test_setup.py`)
- [ ] Bot settings configured (small size, low leverage)
- [ ] Understand what the bot does
- [ ] Ready to monitor closely

**If all checked ✅ → You're ready to trade!**

---

## 🎓 Recommended First Steps

### Day 1: Test Run
1. Set `size = 0.1` (very small)
2. Set `leverage = 1` (no leverage)
3. Run bot for 1-2 hours
4. Monitor closely
5. Stop and review

### Day 2: Small Position
1. Set `size = 0.5` (still small)
2. Set `leverage = 2` (low leverage)
3. Run for a few hours
4. Monitor results

### Day 3+: Scale Gradually
- Only increase size if bot is performing well
- Never risk more than you can afford to lose
- Always use stop losses

---

## 📊 Understanding Your Bot

### What the Bollinger Bands Bot Does:

1. **Checks market conditions** every 30 seconds
2. **Calculates Bollinger Bands** (volatility indicator)
3. **Enters trades** when bands are "tight" (low volatility)
4. **Places limit orders** at bid/ask prices
5. **Monitors positions** for profit/loss targets
6. **Closes positions** automatically at target or stop loss

### Key Settings Explained:

- **`symbol`**: What coin to trade (BTC, ETH, SOL, WIF, etc.)
- **`size`**: Position size (how much to trade)
- **`target`**: Take profit percentage (e.g., 5% = close at +5%)
- **`max_loss`**: Stop loss percentage (e.g., -10% = close at -10%)
- **`leverage`**: Multiplier (3x = 3x your position size)
- **`timeframe`**: Chart timeframe (15m = 15-minute candles)

---

## 🆘 Common Issues & Solutions

### "ModuleNotFoundError"
**Solution:** Activate environment first
```bash
source activate_env.sh
```

### "Invalid private key"
**Solution:** 
- Make sure key starts with `0x`
- Check for extra spaces
- Verify you copied entire key

### "Insufficient funds"
**Solution:**
- Add more ETH to Arbitrum
- Reduce position size
- Check you're on Arbitrum network

### Bot not placing orders
**Solution:**
- Check HyperLiquid website for account status
- Verify private key is correct
- Check internet connection
- Review bot output for error messages

---

## 📚 Next Steps

Once comfortable with the basic bot:

1. **Try other bots:**
   - Day 11: Supply & Demand bot
   - Day 12: VWAP bot

2. **Learn more:**
   - Read bot code to understand strategies
   - Experiment with different settings
   - Study the `nice_funcs.py` utilities

3. **Advanced:**
   - Try bonus algorithms
   - Backtest strategies
   - Develop your own strategies

---

## 🎯 Quick Command Reference

```bash
# Activate environment
source activate_env.sh

# Test setup
python test_setup.py

# Run bot
python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py

# Stop bot
Ctrl+C

# Check installed packages
pip list

# Update packages
pip install --upgrade -r requirements.txt
```

---

## ⚠️ Final Reminders

1. **Start small** - test with tiny amounts first
2. **Monitor closely** - don't leave bot unattended initially
3. **Use stop losses** - always set max_loss
4. **Never risk more than you can lose**
5. **Keep learning** - understand what the bot does
6. **Be patient** - trading takes time to learn

---

**You're all set!** Follow the phases above and you'll be trading in under 30 minutes. 🚀

**Questions?** Check `API_KEYS_SETUP.md` for detailed API key instructions.



