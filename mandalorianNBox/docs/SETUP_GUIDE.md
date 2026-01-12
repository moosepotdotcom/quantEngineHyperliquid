# 🚀 ATC Bootcamp Trading Bots - Setup Guide

This guide will help you set up and run the trading bots on your local machine.

## 📋 Prerequisites

1. **Python 3.8+** (Python 3.8.5 recommended)
2. **Anaconda or Miniconda** (recommended) OR just use `pip` with regular Python
3. **MetaMask wallet** (for HyperLiquid bots)
4. **Phemex account** (optional, for older bots)

---

## 🔧 Step 1: Environment Setup

### Option A: Using Anaconda (Recommended)

```bash
# Create a new conda environment
conda create --name algotrader python=3.8.5

# Activate the environment
conda activate algotrader

# Navigate to the project directory
cd "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025"
```

### Option B: Using Regular Python

```bash
# Create a virtual environment
python3 -m venv algotrader

# Activate the environment
# On macOS/Linux:
source algotrader/bin/activate
# On Windows:
# algotrader\Scripts\activate

# Navigate to the project directory
cd "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025"
```

---

## 📦 Step 2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

**Note:** If you have issues installing TA-Lib, see the troubleshooting section below.

---

## 🔐 Step 3: Configure API Keys

### For HyperLiquid Bots (Days 10-12)

1. **Get your HyperLiquid private key:**
   - Open MetaMask
   - Go to your account
   - Click "Account Details" > "Export Private Key"
   - Enter your password and copy the private key

2. **Edit `dontshare.py`:**
   ```python
   private_key = '0xYOUR_ACTUAL_PRIVATE_KEY_HERE'
   ```

### For Phemex Bots (Days 4-9)

1. **Get your Phemex API keys:**
   - Log in to Phemex
   - Go to Account > API Management
   - Create a new API key
   - Copy the API Key and Secret

2. **Edit `key_file.py`:**
   ```python
   xP_KEY = 'YOUR_PHEMEX_API_KEY'
   xP_SECRET = 'YOUR_PHEMEX_API_SECRET'
   ```

⚠️ **SECURITY WARNING:** 
- Never commit these files to git
- Never share your private keys
- Consider adding them to `.gitignore`

---

## 🎯 Step 4: Choose Your First Bot

### Recommended Starting Points:

#### **Beginner: Bollinger Bands Bot (Day 10)**
- **File:** `10_day10_bots/day10_hyperliquid/10_bollinger_bot.py`
- **Strategy:** Enters trades when Bollinger Bands are tight
- **Requirements:** HyperLiquid account + `dontshare.py` configured

#### **Intermediate: Supply & Demand Bot (Day 11)**
- **File:** `11_day11_bots/day11_hyperliquid/11_sdz_bot.py`
- **Strategy:** Trades based on supply/demand zones
- **Requirements:** HyperLiquid account + `dontshare.py` configured

#### **Advanced: VWAP Bot (Day 12)**
- **File:** `12_day12_bots/day12_hyperliquid/12_vwap_bot.py`
- **Strategy:** Volume-weighted average price trading
- **Requirements:** HyperLiquid account + `dontshare.py` configured

---

## ▶️ Step 5: Run Your Bot

### Before Running:

1. **Review the bot settings** in the bot file:
   ```python
   symbol = 'WIF'          # Trading pair
   target = 5              # Take profit (%)
   max_loss = -10          # Stop loss (%)
   leverage = 3            # Leverage multiplier
   size = 1                # Position size
   ```

2. **Start with paper trading or very small sizes!**

3. **Run the bot:**
   ```bash
   # For HyperLiquid bots (Day 10-12)
   python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py
   
   # Or for other bots
   python 11_day11_bots/day11_hyperliquid/11_sdz_bot.py
   ```

4. **The bot will:**
   - Run continuously
   - Check market conditions every 30 seconds
   - Place orders based on your strategy
   - Monitor positions and close them at target/max loss

5. **To stop the bot:** Press `Ctrl+C` in the terminal

---

## 🛠️ Troubleshooting

### TA-Lib Installation Issues

TA-Lib can be tricky to install. Try:

**macOS:**
```bash
brew install ta-lib
pip install TA-Lib
```

**Linux:**
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install TA-Lib
```

**Windows:**
Download the wheel file from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
Then: `pip install TA_Lib‑0.4.28‑cp38‑cp38‑win_amd64.whl`

### Import Errors

If you get `ModuleNotFoundError`:
```bash
# Make sure your environment is activated
conda activate algotrader  # or source algotrader/bin/activate

# Reinstall the package
pip install <package_name>
```

### HyperLiquid Connection Issues

- Verify your private key is correct in `dontshare.py`
- Make sure you have funds in your HyperLiquid account
- Check that the symbol you're trading exists on HyperLiquid

### Phemex Connection Issues

- Verify your API keys in `key_file.py`
- Check API key permissions (trading enabled)
- Ensure you're using the correct API endpoint

---

## 📚 Next Steps

1. **Start with small position sizes** to test
2. **Monitor the bot** closely for the first few hours
3. **Review the logs** to understand what it's doing
4. **Adjust parameters** based on your risk tolerance
5. **Try different strategies** from the bonus algorithms folder

---

## ⚠️ Important Warnings

- **Start with paper trading or very small amounts**
- **Never risk more than you can afford to lose**
- **These bots are for educational purposes**
- **Always test thoroughly before going live**
- **Monitor your bots regularly**
- **Use proper risk management**

---

## 📞 Need Help?

- Check the code comments in each bot file
- Review the `nice_funcs.py` files for function documentation
- Test with small amounts first
- Use the backtesting script (`13_backtesting.py`) to test strategies

---

## 🎓 Learning Path

1. **Days 2-4:** Basics and order execution
2. **Days 5-9:** Indicators and risk management
3. **Days 10-12:** Complete trading bots
4. **Day 13:** Backtesting strategies
5. **Bonus:** Advanced algorithms

Good luck and trade safely! 🚀



