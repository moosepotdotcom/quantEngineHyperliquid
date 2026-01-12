# 🎯 START HERE - Get Your Bot Running!

Welcome! This guide will get you trading in **under 10 minutes**.

---

## ✅ What's Been Set Up For You

I've created all the necessary files:
- ✅ `requirements.txt` - All packages needed
- ✅ `dontshare.py` - Template for your HyperLiquid private key
- ✅ `key_file.py` - Template for Phemex API keys (optional)
- ✅ `SETUP_GUIDE.md` - Detailed setup instructions
- ✅ `QUICK_START.md` - Fast 3-step guide
- ✅ `test_setup.py` - Verify everything works
- ✅ `.gitignore` - Protects your API keys

---

## Folder Renaming
This project is portable. You can rename the root folder (e.g., to `mandalorianNBox`) safely. However, you MUST re-create the virtual environment after moving/renaming:
1. Rename the folder.
2. Delete the old `algotrader` folder.
3. Run `bash scripts/setup.sh` to re-create it. (Choose Your Path)

### Path 1: I Want to Start Trading NOW (5 minutes)

1. **Install packages:**
   ```bash
   # Create environment
   python3 -m venv algotrader
   source algotrader/bin/activate
   
   # Install everything
   pip install -r requirements.txt
   ```

2. **Add your HyperLiquid private key:**
   - Open `dontshare.py`
   - Replace `YOUR_HYPERLIQUID_PRIVATE_KEY_HERE` with your actual MetaMask private key
   - Save the file

3. **Test your setup:**
   ```bash
   python test_setup.py
   ```

4. **Run your first bot:**
   ```bash
   python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py
   ```

**Done!** Your bot is now running. Press `Ctrl+C` to stop it.

---

### Path 2: I Want Detailed Instructions

Read `SETUP_GUIDE.md` for:
- Complete setup walkthrough
- Troubleshooting tips
- Security best practices
- Advanced configuration

---

## 📋 Step-by-Step Instructions

### Step 1: Set Up Python Environment

**Option A - Using venv (Simplest):**
```bash
cd "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025"
python3 -m venv algotrader
source algotrader/bin/activate
```

**Option B - Using Conda:**
```bash
cd "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025"
conda create --name algotrader python=3.8.5 -y
conda activate algotrader
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If TA-Lib fails to install, it's optional. You can skip it for now.

### Step 3: Configure Your API Keys

**For HyperLiquid (Required for Day 10-12 bots):**

1. Get your MetaMask private key:
   - Open MetaMask extension
   - Click account icon (top right)
   - Click "Account Details"
   - Click "Export Private Key"
   - Enter password and copy the key

2. Edit `dontshare.py`:
   ```python
   private_key = '0xYOUR_ACTUAL_KEY_HERE'  # Replace with your key
   ```

### Step 4: Test Your Setup

```bash
python test_setup.py
```

This will check:
- ✅ All packages installed
- ✅ Config files set up
- ✅ HyperLiquid connection working

### Step 5: Configure Your Bot

Before running, edit the bot file to set your preferences:

**File:** `10_day10_bots/day10_hyperliquid/10_bollinger_bot.py`

```python
symbol = 'WIF'          # Trading pair (BTC, ETH, SOL, etc.)
target = 5              # Take profit: 5%
max_loss = -10          # Stop loss: -10%
leverage = 3            # Leverage (start with 1-3x)
size = 1                # Position size (START SMALL!)
```

**⚠️ IMPORTANT:** Start with very small sizes to test!

### Step 6: Run Your Bot

```bash
python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py
```

You should see output like:
```
this is the ask for WIF 2.45
bollinger bands are tight: True
not in position we are quoteing a sell @ 2.45 and buy @ 2.44
```

### Step 7: Monitor Your Bot

- Watch the terminal output
- Check your HyperLiquid account
- The bot runs continuously until you stop it (`Ctrl+C`)

---

## 🎓 Recommended Learning Path

1. **Start Here:** Bollinger Bands Bot (Day 10)
   - File: `10_day10_bots/day10_hyperliquid/10_bollinger_bot.py`
   - Simple strategy, good for learning

2. **Next:** Supply & Demand Bot (Day 11)
   - File: `11_day11_bots/day11_hyperliquid/11_sdz_bot.py`
   - More advanced strategy

3. **Then:** VWAP Bot (Day 12)
   - File: `12_day12_bots/day12_hyperliquid/12_vwap_bot.py`
   - Volume-based trading

4. **Advanced:** Bonus Algorithms
   - Folder: `Bonus_algos_6ofthem/`
   - Professional trading strategies

---

## ⚠️ Safety Checklist

Before going live:

- [ ] Tested with `test_setup.py` - all checks pass
- [ ] API keys configured correctly
- [ ] Starting with **very small position sizes**
- [ ] Understand the bot's strategy
- [ ] Set appropriate stop loss and take profit
- [ ] Have funds in your HyperLiquid account
- [ ] Ready to monitor the bot

**Remember:** Start small, test thoroughly, scale gradually!

---

## 🆘 Need Help?

1. **Setup issues?** → Read `SETUP_GUIDE.md`
2. **Quick reference?** → Read `QUICK_START.md`
3. **Test your setup?** → Run `python test_setup.py`
4. **Import errors?** → Make sure environment is activated
5. **Connection issues?** → Check your API keys

---

## 📁 File Structure

```
ATC Bootcamp Code 2025/
├── START_HERE.md          ← You are here!
├── QUICK_START.md         ← 3-step quick guide
├── SETUP_GUIDE.md         ← Detailed instructions
├── requirements.txt       ← Package list
├── dontshare.py           ← Your API keys (configure this!)
├── test_setup.py          ← Test your setup
├── 10_day10_bots/         ← Bollinger Bands bot
├── 11_day11_bots/         ← Supply/Demand bot
├── 12_day12_bots/         ← VWAP bot
└── Bonus_algos_6ofthem/   ← Advanced strategies
```

---

## 🎉 You're Ready!

Follow the steps above and you'll be trading in minutes. Good luck! 🚀

**Questions?** Check the guides or review the code comments in each bot file.



