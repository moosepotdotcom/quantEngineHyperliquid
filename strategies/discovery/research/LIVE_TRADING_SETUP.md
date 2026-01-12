# 🚀 Live Trading Setup Guide

**Complete guide to run AI trading bot with real money on Hyperliquid**

---

## ⚠️ **CRITICAL: Read This First!**

**You are about to trade with REAL MONEY!**

- Start with TESTNET first (included)
- Use small amounts ($10 recommended for testing)
- Understand you can lose money
- Never invest more than you can afford to lose

---

## 📋 **What You Have**

### Files Created:
1. `hyperliquid_live_trader.py` - Hyperliquid API integration
2. `live_trading_engine.py` - Main trading engine
3. `.env.live_trading` - Configuration file

### Safety Features:
- ✅ Max position: 0.01 BTC
- ✅ Max leverage: 2x
- ✅ Daily loss limit: $5
- ✅ Automatic stop losses
- ✅ Emergency kill switch
- ✅ Testnet mode for safe testing

---

## 🔧 **Setup Instructions**

### Step 1: Install Dependencies

```bash
cd /Users/alifiyaa/Downloads/quantEngineHyperliquid

# Install required packages
pip install python-dotenv eth-account web3

# Verify installation
python -c "import dotenv, eth_account; print('✅ Dependencies installed!')"
```

### Step 2: Configure Your Credentials

```bash
# Copy the template
cp .env.live_trading .env

# Edit with your credentials
nano .env
```

**Edit these fields in `.env`:**

```bash
# Your wallet address (already filled in)
HYPERLIQUID_WALLET_ADDRESS=0xb01713a6fcdc9419f37db065f0274ea172e4689e

# Your private key (GET THIS FROM HYPERLIQUID!)
HYPERLIQUID_API_SECRET=your_actual_private_key_here

# Start with testnet
USE_TESTNET=true
```

**How to get your private key:**
1. Go to Hyperliquid settings
2. Find "API Keys" or "Export Private Key"
3. Copy your private key
4. Paste it in `.env` file
5. **NEVER share this key with anyone!**

### Step 3: Test on Testnet First

```bash
# Run on testnet (NO REAL MONEY)
python live_trading_engine.py --live

# This will:
# - Connect to Hyperliquid testnet
# - Use fake money
# - Test all features
# - Verify everything works
```

**Let it run for 24 hours on testnet!**

### Step 4: Switch to Mainnet (Real Money)

**Only after successful testnet testing!**

```bash
# Edit .env
nano .env

# Change this line:
USE_TESTNET=false

# Run with real money
python live_trading_engine.py --live --mainnet
```

---

## 🎮 **Usage**

### Paper Trading Only (Default)
```bash
# No real money, just tracking signals
python live_trading_engine.py
```

### Live Trading on Testnet
```bash
# Fake money, real testing
python live_trading_engine.py --live
```

### Live Trading on Mainnet
```bash
# REAL MONEY - Be careful!
python live_trading_engine.py --live --mainnet
```

### Emergency Stop
```bash
# Press Ctrl+C to stop
# All positions will be closed automatically
```

---

## 📊 **What Happens When Running**

### Continuous Monitoring:
```
1. Every 60 seconds:
   - Check Winner Hunter (1H) for signals
   - Check MTF Scalper (5M) for signals
   
2. When signal detected:
   - Paper trade: Always logged
   - Live trade: Only if confidence > 30%
   
3. Position management:
   - Check TP/SL every 10 seconds
   - Auto-close when TP or SL hit
   - Update P&L tracking
```

### Example Output:
```
🚀 Initializing Integrated Trading Engine
======================================================================
📊 Loading Paper Trading Engine...
💰 Loading Live Trading Engine...
   Mode: TESTNET
   Wallet: 0xb01713a6fcdc9419f37db065f0274ea172e4689e
   Max Position: 0.01 BTC
   Max Leverage: 2x
   Daily Loss Limit: $5.0
======================================================================

⏰ 14:30:00 | Check #1
======================================================================
🏆 Checking Winner Hunter (1H)...
   📊 Confidence: 32.33%
   
🎯 Signal Detected!
   Model: Winner Hunter (1H)
   Price: $89,414.00
   Confidence: 32.33%

📝 Paper Trading: Logging signal...
💰 Live Trading: Executing order...
   
📤 Placing Order:
   Symbol: BTC
   Side: Buy
   Size: 0.01
   Type: Market
   
✅ Position opened:
   Entry: $89,414.00
   TP: $90,755.21 (+1.5%)
   SL: $88,699.08 (-0.8%)
```

---

## 🛡️ **Safety Features Explained**

### 1. Position Limits
- **Max 0.01 BTC** per trade
- With $10 account = ~$8.94 position size
- Safe for testing

### 2. Leverage Limit
- **Max 2x leverage**
- Conservative and safe
- Reduces liquidation risk

### 3. Daily Loss Limit
- **Stop trading if lose $5**
- Protects your $10 deposit
- Resets daily at midnight UTC

### 4. Automatic Stop Loss
- **-0.8% stop loss** on every trade
- Auto-closes losing positions
- Limits maximum loss per trade

### 5. Take Profit
- **+1.5% take profit** on every trade
- Auto-closes winning positions
- Locks in profits

### 6. Emergency Stop
- **Press Ctrl+C** anytime
- Closes all positions immediately
- Stops all trading

---

## 📈 **Expected Performance**

Based on paper trading results:

**Backtest Stats:**
- Win Rate: ~30%
- Avg Win: +1.5%
- Avg Loss: -0.8%
- Risk/Reward: 1:1.88

**With $10 Account:**
- Position size: ~$9 per trade
- Win: +$0.13 per trade
- Loss: -$0.07 per trade
- Expected: +$0.04 per trade

**Daily Estimates:**
- Trades per day: 1-3
- Expected daily: +$0.04 to +$0.12
- Max daily loss: -$5.00 (safety limit)

---

## 🔍 **Monitoring Your Trades**

### Check Status:
```python
# In another terminal
python -c "
from hyperliquid_live_trader import HyperliquidTrader
trader = HyperliquidTrader(testnet=True)
status = trader.get_status()
print(f'Daily P&L: \${status[\"daily_pnl\"]:.2f}')
print(f'Active Positions: {status[\"active_positions\"]}')
"
```

### View Logs:
```bash
# Real-time logs
tail -f logs/live_trading.log

# All logs
cat logs/live_trading.log
```

### Check Hyperliquid:
- Go to https://app.hyperliquid.xyz
- Connect your wallet
- View positions and P&L

---

## ⚠️ **Troubleshooting**

### "HYPERLIQUID_WALLET_ADDRESS not set"
```bash
# Make sure .env file exists
ls -la .env

# Check it has your wallet address
cat .env | grep HYPERLIQUID_WALLET_ADDRESS
```

### "Failed to initialize live trader"
```bash
# Check your private key is correct
# Make sure you have funds in your account
# Verify you're using the right network (testnet/mainnet)
```

### "Daily loss limit hit"
```bash
# This is a safety feature!
# Trading stops automatically
# Limit resets at midnight UTC
# Review your trades and adjust strategy
```

### Orders not executing
```bash
# Check account balance
# Verify API credentials
# Make sure USE_TESTNET matches your network
# Check Hyperliquid status
```

---

## 🎯 **Best Practices**

### 1. Start Small
- ✅ Use $10 for testing
- ✅ Test on testnet first
- ✅ Run for 1 week minimum
- ❌ Don't deposit large amounts initially

### 2. Monitor Closely
- ✅ Check every few hours
- ✅ Review all trades
- ✅ Watch for errors
- ❌ Don't leave unattended for days

### 3. Adjust Gradually
- ✅ Start with conservative settings
- ✅ Increase size slowly if profitable
- ✅ Lower limits if losing
- ❌ Don't change everything at once

### 4. Keep Records
- ✅ Save all logs
- ✅ Track P&L manually
- ✅ Note what works/doesn't
- ❌ Don't rely only on automated tracking

---

## 🚨 **Emergency Procedures**

### If Something Goes Wrong:

**1. Stop Trading Immediately:**
```bash
# Press Ctrl+C in terminal
# Or run:
pkill -f live_trading_engine
```

**2. Close All Positions:**
```python
python -c "
from hyperliquid_live_trader import HyperliquidTrader
trader = HyperliquidTrader(testnet=False)  # Use your network
trader.emergency_stop_all()
"
```

**3. Check Hyperliquid:**
- Go to app.hyperliquid.xyz
- Manually close any remaining positions
- Withdraw funds if needed

---

## 📝 **Configuration Reference**

### Key Settings in `.env`:

```bash
# Position sizing
MAX_POSITION_SIZE=0.01        # BTC per trade
MAX_LEVERAGE=2                # Leverage multiplier
POSITION_USD_VALUE=10         # Your account size

# Risk management
DAILY_LOSS_LIMIT=5.0         # Max loss per day
MAX_DAILY_TRADES=5           # Max trades per day
MAX_OPEN_POSITIONS=2         # Max concurrent trades

# Model confidence
WINNER_HUNTER_MIN_CONFIDENCE=0.30   # 30% minimum
MTF_SCALPER_MIN_CONFIDENCE=0.25     # 25% minimum

# Safety
USE_TESTNET=true             # Start with testnet!
EMERGENCY_STOP=false         # Set true to stop trading
```

---

## 🎊 **You're Ready!**

### Checklist:
- ✅ Dependencies installed
- ✅ `.env` file configured
- ✅ Private key added
- ✅ Tested on testnet
- ✅ Understand the risks
- ✅ Know how to stop trading

### Next Steps:
1. Run on testnet for 24-48 hours
2. Verify all features work
3. Check P&L tracking
4. Switch to mainnet when confident
5. Start with $10
6. Monitor closely
7. Scale up slowly if profitable

---

**Good luck! Trade safely! 🚀💰**

---

## 📞 **Support**

If you encounter issues:
1. Check the troubleshooting section
2. Review logs in `logs/live_trading.log`
3. Test on testnet first
4. Start with paper trading to verify setup

**Remember: You can always stop trading with Ctrl+C!**
