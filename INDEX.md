# 📚 Documentation Index

## 🎯 Start Here

**New to this project?** Read in this order:

1. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Overview of what this does and why
2. **[BACKTEST_RESULTS.md](BACKTEST_RESULTS.md)** - Performance metrics and trade data
3. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Commands and troubleshooting
4. **[README.md](README.md)** - Technical details and structure

---

## 📄 Documentation Files

### PROJECT_SUMMARY.md
**What:** Complete project overview  
**Contains:**
- What the project does
- Key performance metrics (100% win rate!)
- Technical stack
- How it works
- Current status
- Deployment instructions

**Read this if:** You want to understand the entire project quickly

---

### BACKTEST_RESULTS.md
**What:** Detailed backtest performance data  
**Contains:**
- Winner Hunter: 82 trades, 2.73/day, 100% WR
- MTF Scalper: 15 trades, 15/day, 100% WR
- Combined performance: ~$14k/day potential
- Market conditions for trades
- Multi-timeframe feature details
- Hyperliquid API performance

**Read this if:** You want to see the actual numbers and proof of performance

---

### QUICK_REFERENCE.md
**What:** Quick commands and troubleshooting  
**Contains:**
- File structure
- Quick commands (deploy, test, logs)
- Model configuration
- Feature engineering details
- Troubleshooting guide
- Monitoring tips

**Read this if:** You need to deploy, test, or fix something quickly

---

### README.md
**What:** Project overview and setup  
**Contains:**
- Models description
- Features list
- Why Hyperliquid
- Project structure
- Status

**Read this if:** You want a concise technical overview

---

## 🤖 Code Files

### quant_engine.py (15KB)
**Main trading engine**
- Loads both models (Winner Hunter, MTF Scalper)
- Fetches data from Hyperliquid
- Generates features (77 for WH, 236 for MTF)
- Runs predictions every 60 seconds
- Displays confidence and trade signals

### cloud_runner.py (929B)
**Flask wrapper for Cloud Run**
- Provides HTTP health endpoint
- Runs quant_engine in background thread
- Required for Cloud Run deployment

### quant_engine_backup.py (12KB)
**Backup of working version**
- Keep this as reference
- Don't modify

---

## 🚀 Deployment Files

### deploy.sh (260B)
**One-command deployment**
```bash
./deploy.sh
```
Builds and deploys to Cloud Run automatically

### Dockerfile (617B)
**Container configuration**
- Python 3.9 slim base
- Installs dependencies
- Copies models and utils
- Runs cloud_runner.py

### cloudbuild.yaml (194B)
**Cloud Build configuration**
- Builds Docker image with --no-cache
- Pushes to Google Container Registry

### requirements.txt (52B)
**Python dependencies**
- pandas, numpy, xgboost
- scikit-learn, ta, requests, flask

---

## 📊 Data Files

### models/
- `winner_hunter_1h.json` - 1H swing trading model
- `mtf_scalper_5m.json` - 5M scalping model

### utils/
- `feature_engineer.py` - 77 technical indicators
- `mtf_scalper_5m.py` - Multi-timeframe feature merger

---

## 🎯 Quick Actions

### Want to deploy?
→ Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md#quick-commands)

### Want to see performance?
→ Read [BACKTEST_RESULTS.md](BACKTEST_RESULTS.md)

### Want to understand the project?
→ Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

### Want to troubleshoot?
→ Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md#troubleshooting)

---

## 📈 Key Numbers to Remember

- **100% Win Rate** (97 backtest trades)
- **17-18 trades/day** (during favorable markets)
- **~$14,000/day** potential profit
- **95% confidence** minimum threshold
- **236 features** (MTF Scalper)
- **77 features** (Winner Hunter)

---

**Last Updated:** Dec 28, 2025  
**Total Documentation:** 4 markdown files  
**Total Code Files:** 3 Python files  
**Status:** ✅ Complete and ready for deployment
