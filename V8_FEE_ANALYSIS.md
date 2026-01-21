# V8 Strategy Fee Analysis - CRITICAL FINDINGS

## Problem Discovered

The V8 Unified Strategy is **NOT PROFITABLE** with Hyperliquid fees.

### Numbers
- **Gross PnL:** +$1,661 (+16.61%)
- **Hyperliquid Fees:** -$13,180 (-131.80%)
- **Net PnL:** **-$11,640 (-116.40%)**

### Why It Fails
- **Trades:** 1,318 over 14 days (94/day)
- **Fee per trade:** $10 (0.05% entry + 0.05% exit on $10k position)
- **Profit per trade:** $1.26 average
- **Net per trade:** **-$8.83 LOSS**

### Root Cause
The 0.1% grid spacing is too tight for the 0.1% round-trip fee structure.

## Viable Alternatives

### Option 1: V7 Sniper Strategy (RECOMMENDED)
- **Target:** 0.5% (5x larger than V8 grid)
- **Trades:** 10 over 14 days (0.7/day)
- **Gross PnL:** +$110
- **Estimated Fees:** ~$100
- **Net PnL:** **Still positive** ✅

### Option 2: Widen V8 Grid
- Increase spacing to 0.3-0.5%
- Reduce trade frequency to ~10-20/day
- Fees become manageable

### Option 3: Maker-Only Orders
- Use limit orders (0.02% fee instead of 0.05%)
- Reduces fees by 60%
- Requires more sophisticated order management

## Recommendation

**Deploy V7 Sniper Strategy** with:
- 0.5% target, 0.15% stop
- CVD alignment filter
- High volatility regime detection
- ~10 high-conviction trades per 2 weeks
- **Profitable after fees**
