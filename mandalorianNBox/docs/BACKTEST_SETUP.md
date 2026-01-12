# 🧪 Backtesting Setup - Get Testing Live NOW

**Quick guide to get backtesting running on your local machine immediately.**

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Activate Environment
```bash
cd "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025"
source activate_env.sh
```

### Step 2: Install Backtesting Dependencies
```bash
pip install backtrader matplotlib pandas numpy
```

### Step 3: Test Backtesting Setup
```bash
python test_backtest.py
```

### Step 4: Run Your First Backtest
```bash
python 13_backtesting.py
```

**Done!** You should see backtest results.

---

## 📊 Available Backtest Files

### 1. **Basic SMA Backtest** (`13_backtesting.py`)
- Simple Moving Average crossover strategy
- Uses BTC historical data
- Shows Sharpe ratio, transactions, final value

### 2. **Custom Strategy Backtests**
- You can modify `13_backtesting.py` to test any strategy
- Add your own indicators
- Test different timeframes

---

## 🎯 Test Your Setup Right Now

### Quick Test Script

I've created `test_backtest.py` - run it to verify everything works:

```bash
python test_backtest.py
```

This will:
- ✅ Check if backtrader is installed
- ✅ Test data loading
- ✅ Run a simple backtest
- ✅ Show results

---

## 📈 Run Your First Backtest

### Option 1: Use Existing Backtest
```bash
python 13_backtesting.py
```

### Option 2: Create Custom Backtest

Edit `13_backtesting.py` and modify the strategy, then run:
```bash
python 13_backtesting.py
```

---

## 📁 Historical Data Available

You have BTC data in `datasets/`:
- `BTCUSD-1d-1000wks-data.csv` - Daily data (1000 weeks)
- `BTCUSD-1h-500wks-data.csv` - Hourly data (500 weeks)
- `BTCUSD-6h-500wks-data.csv` - 6-hour data (500 weeks)

---

## 🔧 Next Steps After Setup

1. **Test basic backtest** - Run `13_backtesting.py`
2. **Modify strategy** - Edit the SMA strategy
3. **Add indicators** - RSI, VWAP, Bollinger Bands
4. **Test different timeframes** - Daily, hourly, etc.
5. **Compare strategies** - Test multiple approaches

---

## ⚠️ Common Issues

### "ModuleNotFoundError: backtrader"
**Fix:** `pip install backtrader`

### "File not found" error
**Fix:** Check the data file path in the script

### "No data" error
**Fix:** Make sure CSV files are in the `datasets/` folder

---

**Ready?** Run `python test_backtest.py` now!

