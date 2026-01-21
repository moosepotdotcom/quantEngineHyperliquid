# V9 Liquidation-Based Strategy - Research Plan

## Hypothesis
**"There's a huge correlation between price movement and liquidations"**

This is a STRONG hypothesis backed by market microstructure theory:
- Liquidations create forced buying/selling
- Cascading liquidations cause rapid price moves
- Smart money hunts liquidation clusters

---

## Data Sources to Collect

### 1. Liquidation Data
**Primary Sources:**
- **Hyperliquid API** - Real-time liquidations
- **Coinglass API** - Aggregated liquidation data across exchanges
- **CryptoQuant** - Liquidation heatmaps
- **Glassnode** - On-chain liquidation metrics

**Data Points:**
- Liquidation volume (long vs short)
- Liquidation price levels
- Liquidation cascades (clusters)
- Time-series of liquidations

### 2. Funding Rates
**Why:** Indicates market sentiment and potential squeeze setups
- Positive funding = longs pay shorts (bullish bias)
- Negative funding = shorts pay longs (bearish bias)
- Extreme funding = potential reversal

**Sources:**
- Hyperliquid API
- Binance API
- Bybit API

### 3. Open Interest
**Why:** Shows total market exposure
- Rising OI + rising price = strong trend
- Rising OI + falling price = potential reversal
- Falling OI = position unwinding

**Sources:**
- Hyperliquid API
- Coinglass

### 4. Order Book Imbalance
**Why:** Shows supply/demand pressure
- Bid/ask ratio
- Large order walls
- Depth imbalance

**Sources:**
- Hyperliquid L2 orderbook
- Real-time websocket feeds

### 5. CVD (Cumulative Volume Delta)
**Already have this!** - It's in our current model
- Tracks aggressive buying vs selling
- Complements liquidation data

---

## Strategy Ideas

### Liquidation Hunt Strategy
1. **Identify liquidation clusters** (where stops are)
2. **Wait for price to approach** cluster
3. **Enter when liquidations trigger** (momentum)
4. **Exit before next cluster**

### Funding Rate Arbitrage
1. **Detect extreme funding** (>0.1% or <-0.1%)
2. **Fade the crowd** when funding is extreme
3. **Ride the squeeze** as positions unwind

### OI Divergence
1. **Price up + OI down** = weak rally (short)
2. **Price down + OI up** = accumulation (long)

### Combined Signal
- Liquidation spike + CVD alignment + Funding extreme = HIGH CONVICTION

---

## Implementation Plan

### Phase 1: Data Collection (NOW)
- [ ] Download Hyperliquid liquidation data (Jan 2026)
- [ ] Fetch funding rate history
- [ ] Get open interest data
- [ ] Collect order book snapshots

### Phase 2: Feature Engineering
- [ ] Liquidation volume (1m, 5m, 15m windows)
- [ ] Liquidation direction (long vs short)
- [ ] Funding rate (current + change)
- [ ] OI change rate
- [ ] Order book imbalance

### Phase 3: Correlation Analysis
- [ ] Liquidation → Price movement (lag analysis)
- [ ] Funding → Reversal timing
- [ ] OI → Trend strength

### Phase 4: Strategy Development
- [ ] Create liquidation-based labels
- [ ] Train V9 model with new features
- [ ] Backtest on Jan 2026
- [ ] Compare vs V8 (83.82% WR baseline)

### Phase 5: Validation
- [ ] Out-of-sample test
- [ ] Fee analysis
- [ ] Risk metrics

---

## Expected Improvements

**If hypothesis is correct:**
- Win rate: 83.82% → 90%+ (liquidation signals are strong)
- Trade frequency: 4.8/day → 8-10/day (more signals)
- Drawdown: Lower (better entries at liquidation levels)

**Key Advantage:**
Liquidation data is NOT in our current model - this is NEW alpha!

---

## Next Steps

1. ✅ Create experimental workspace (V9_LIQUIDATION_EXPERIMENT/)
2. 🔄 Download liquidation data
3. 🔄 Fetch funding rates
4. 🔄 Get open interest
5. 📊 Analyze correlations
6. 🎯 Build V9 strategy

Let's start with data collection!
