# Liquidation Infrastructure - Complete Setup

## 🎯 What We Built

### 1. **Liquidation Monitor** (`liquidation_monitor.py`)
- 24/7 WebSocket connection to Hyperliquid
- Captures all BTC liquidations in real-time
- Saves to daily CSV files (`liquidation_data/liquidations_YYYYMMDD.csv`)
- Maintains in-memory buffer of last 1000 liquidations
- Auto-reconnects if connection drops
- Tracks statistics (total, long/short, volume)

**Usage:**
```bash
python3 liquidation_monitor.py
# Runs forever, press Ctrl+C to stop
```

### 2. **Heatmap Visualizer** (`heatmap_visualizer.py`)
- Builds liquidation heatmap from collected data
- Groups liquidations into $100 price buckets
- Identifies significant clusters (intensity-based)
- Shows nearest "magnet zones" above/below price
- ASCII visualization in terminal

**Usage:**
```python
from heatmap_visualizer import visualize_current_heatmap
visualize_current_heatmap(current_price=102000)
```

### 3. **Liquidation Predictor** (`liquidation_predictor.py`)
- Predicts liquidation levels based on leverage (10x, 25x, 50x, 100x)
- Analyzes funding rate for liquidation risk
- Shows where liquidations WILL occur
- Combines with heatmap to find actual clusters

**Usage:**
```python
from liquidation_predictor import LiquidationPredictor
predictor = LiquidationPredictor()
predictor.print_prediction_report()
```

### 4. **Unified Dashboard** (`liquidation_dashboard.py`)
- All-in-one monitoring tool
- Auto-refreshes every 30 seconds
- Shows:
  - Live liquidation feed
  - Current statistics
  - Predicted liquidation levels
  - Heatmap visualization
  - Nearest magnet zones

**Usage:**
```bash
python3 liquidation_dashboard.py
# Auto-refreshing dashboard
```

## 📊 Data Collection

### Directory Structure:
```
V9_LIQUIDATION_EXPERIMENT/
├── liquidation_data/
│   ├── liquidations_20260115.csv
│   ├── liquidations_20260116.csv
│   └── ...
├── liquidation_monitor.py
├── heatmap_visualizer.py
├── liquidation_predictor.py
└── liquidation_dashboard.py
```

### CSV Format:
```csv
timestamp,coin,side,price,size,liquidator,liquidated
2026-01-15T18:00:00,BTC,A,102500.00,0.5000,...,...
2026-01-15T18:01:30,BTC,B,102300.00,1.2000,...,...
```

- **side:** 'A' = Ask (long liquidation), 'B' = Bid (short liquidation)
- **price:** Liquidation price
- **size:** BTC amount liquidated

## 🚀 Getting Started

### Step 1: Start Monitor (Background)
```bash
# Terminal 1: Start collecting data
cd V9_LIQUIDATION_EXPERIMENT
python3 liquidation_monitor.py &

# Let it run for a few hours to collect data
```

### Step 2: View Dashboard
```bash
# Terminal 2: Watch live dashboard
python3 liquidation_dashboard.py
```

### Step 3: Analyze Data
```python
# After collecting data, analyze patterns
from heatmap_visualizer import LiquidationHeatmapVisualizer

viz = LiquidationHeatmapVisualizer()
df_liqs = viz.load_recent_liquidations(hours=24)
print(f"Collected {len(df_liqs)} liquidations in 24h")

# Build heatmap
df_heatmap = viz.build_heatmap(df_liqs)
print(df_heatmap.head(10))
```

## 🎯 Next Steps

### Phase 1: Data Collection (NOW - Next 24-48 hours)
- ✅ Monitor running 24/7
- ✅ Collecting all liquidations
- ✅ Building historical dataset

### Phase 2: Strategy Development (After data collection)
- Analyze liquidation patterns
- Identify reliable magnet zones
- Backtest magnet strategy
- Compare vs V8 baseline

### Phase 3: Integration (If successful)
- Add liquidation signals to V8
- Create hybrid strategy
- Deploy to production

## 📈 Expected Data Volume

**Quiet market:** 10-50 liquidations/hour
**Normal market:** 50-200 liquidations/hour  
**Volatile market:** 200-1000+ liquidations/hour

**24 hours:** ~1,000-5,000 liquidations
**1 week:** ~7,000-35,000 liquidations

## 🔧 Troubleshooting

**No liquidations appearing?**
- Market might be quiet (normal)
- Check WebSocket connection
- Verify Hyperliquid API is up

**Monitor keeps disconnecting?**
- Auto-reconnects after 5s
- Check internet connection
- Verify firewall allows WebSocket

**Dashboard not updating?**
- Check if monitor is running
- Verify data files exist in `liquidation_data/`
- Try refreshing manually

## 💡 Pro Tips

1. **Run monitor 24/7** - More data = better heatmaps
2. **Check during volatile periods** - Most liquidations happen then
3. **Compare with price action** - See if price moves to clusters
4. **Track funding rate** - Predicts liquidation direction
5. **Use with V8 signals** - Combine for best results

---

**Status:** Infrastructure complete, ready for data collection
**Next:** Let monitor run, collect data, analyze patterns
