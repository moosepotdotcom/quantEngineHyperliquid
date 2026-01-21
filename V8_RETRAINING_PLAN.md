# V8 Unified Strategy - Complete Retraining Plan

## What We've Learned (The Winning Formula)

### 1. Volatility Prediction (V6)
- **84% accuracy** predicting High/Low volatility
- Features: CVD, Volume Delta, MTF Trend, ATR
- Result: Grid strategy +2.46% in 14 days

### 2. Directional Signals (V7)
- **Decision Tree Rules** for direction during high volatility
- Key predictors: EMA_50_15m, RSI_15m, RSI_1h
- Result: +7.07% → +9.22% (optimized) in 14 days

### 3. The Missing Filter (Deep Analysis)
- **CVD Alignment:** +110 difference between wins/losses
- **Volume Delta:** +41 difference
- Result: Win rate 30% → 40%

## V8 Strategy: Unified Multi-Class Model

### Concept
Instead of separate models for volatility and direction, train ONE model to predict:
- **Class 0:** Low Volatility → Deploy Grid
- **Class 1:** High Vol + Bullish Setup → Long (0.5% target)
- **Class 2:** High Vol + Bearish Setup → Short (0.5% target)
- **Class 3:** High Vol + Uncertain → Neutral (sit out)

### Training Labels
For each 5m candle, label based on:
1. **Volatility:** Next 2h ATR
2. **Direction:** Price move in next 4h
3. **CVD/Volume Delta:** Alignment check
4. **Outcome:** TP/SL hit within 48 candles

### Feature Set (Complete)
**Multi-Timeframe:**
- EMA 50/200 (5m, 15m, 1h)
- RSI (5m, 15m, 1h)
- ADX (5m, 15m, 1h)
- ATR (5m, 15m, 1h)

**Order Flow:**
- Volume Delta (5m)
- CVD (1h, 4h)
- Taker Buy/Sell Ratio
- Flow Imbalance (15m)

**Volatility:**
- ATR % (5m, 15m, 1h)
- Bollinger Band Width
- Recent Range

### Expected Performance
- **Grid Trades:** 25/day @ 0.1% = +2.5%
- **Sniper Trades:** 0.7/day @ 0.5% (40% WR) = +1.1%
- **Total:** ~3.6% / 2 weeks unleveraged
- **At 27x:** ~97% return in 2 weeks

## Implementation Steps
1. Generate comprehensive labels (4 classes)
2. Train XGBoost multi-class classifier
3. Validate on Jan 2026 (out-of-sample)
4. Backtest full strategy
5. Deploy unified engine

## Files to Create
- `training/train_v8_unified.py`
- `training/generate_v8_labels.py`
- `model_engines/v8_unified/engine.py`
- `backtest_v8_unified.py`
