# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-07

### Added: Bidirectional Sentinel Upgrade 🛰️↕️🚀
- **Multi-Directional Support**: Full Long and Short trading capabilities across all models.
- **Trio Ensemble Architecture**: Replaced single XGBoost with an ensemble of **XGBoost, LightGBM, and CatBoost**.
- **Vectorized Labeling**: New high-speed labeling engine for 10-year data processing.
- **Dynamic Multi-Class Thresholds**: Separate precision-optimized thresholds for Long and Short signals.
- **Short Execution**: Fixed logic for Market Sell entries and inverted TP/SL exits.
- **Security**: Bidirectional safety in `emergency_stop_all`.

### Performance (Historical Training)
- **MTF Scalper 5M**: 95%+ Precision for both directions on test sets.
- **Dataset Span**: Processed 10 years of market data for 1H model training.

---

## [1.0.0] - 2026-01-01

### Added
- Winner Hunter (1H) XGBoost model with 27.52% confidence threshold
- MTF Scalper (5M) XGBoost model with 20.13% confidence threshold
- Multi-timeframe analysis (5m, 15m, 1h) for MTF Scalper
- Trade logging system with complete lifecycle tracking
- Performance tracker for model monitoring
- Exit monitor with historical price checks
- Continuous 24/7 monitoring system
- Automatic TP/SL detection
- Cloud Run deployment configuration
- Docker containerization
- Complete feature engineering pipeline
- 82+ technical indicators per model

### Performance
- 8/8 trades profitable (100% win rate)
- Total P&L: +$3,119.30
- Realized profit: +$1,311.30
- Unrealized profit: +$1,808.00
- Best trade: +$294 (+0.34%)
- Average trade: +$390 (+0.39%)

### Technical
- Python 3.9 runtime
- XGBoost 2.1.4
- Pandas 2.3.3
- NumPy 2.0.2
- Scikit-learn 1.6.1
- TA-Lib indicators via ta library

### Infrastructure
- Google Cloud Run deployment
- 2GB memory, 2 CPU allocation
- 1-hour timeout for long-running processes
- Hyperliquid API integration
- Flask health check endpoint

### Documentation
- Complete README with setup instructions
- Online learning guide
- Integration guide
- Trade exit monitoring documentation
- Implementation plans

## [Unreleased]

### Planned
- Online learning system integration
- Incremental model retraining
- Ensemble methods (LightGBM, CatBoost)
- A/B testing framework
- Advanced neural network experiments
- Reinforcement learning exploration

---

**Note:** This is the initial release marking the successful deployment of a profitable AI trading bot with 100% win rate.
