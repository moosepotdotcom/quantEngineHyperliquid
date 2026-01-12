# New Strategies Added to Dashboard

The following strategies have been added to the dashboard strategy library. You can now use them in the **Backtest** tab to test their performance.

## 1. Nadarya-Watson Envelope
**Type**: Mean Reversion
**Description**: Uses a Kernel Regression Envelope (estimated via Weighted Moving Averages) to identify overextended price deviations.
- **Buy**: When price drops below the lower envelope band.
- **Sell**: When price rises above the upper envelope band.
- **Configuration**:
  - `bandwidth`: Controls the smoothness of the envelope.
  - `mult`: Multiplier for the envelope width (similar to Bollinger Bands).

## 2. Market Maker Grid
**Type**: Liquidity Provision / Grid
**Description**: Places a grid of limit orders on both sides of the current price. Be careful with this strategy in trending markets.
- **logic**: Places buy orders below price and sell orders above price at fixed percentage intervals.
- **Configuration**:
  - `grid_levels`: Number of levels on each side (default: 5).
  - `grid_spacing_pct`: Percentage spacing between levels (default: 0.5%).

## 3. Mean Reversion
**Type**: Statistical
**Description**: Standard Mean Reversion logic.
- **Buy**: Price < Lower Band (SMA - 2*StdDev)
- **Sell**: Price > Upper Band (SMA + 2*StdDev)

## How to Test
1. Run `./START_DASHBOARD.sh`
2. Open the dashboard in your browser (usually `http://127.0.0.1:5000`).
3. Go to the **Backtest** tab.
4. Select one of the new strategies from the dropdown.
5. Choose a data file (e.g. BTC) and click **Run Backtest**.

## Live Deployment Note
For "Live Test" deployment:
- The dashboard generates a bot template in the `live_bots` folder.
- **Important**: The generated bot is a skeleton. For complex strategies like Nadarya-Watson, you may need to copy the specific logic from the `Bonus_algos_6ofthem` folder into the generated file's loop.
- The default template uses Hyperliquid. If you wish to use Phemex/CCXT (as in the original Bonus Algos), verify the `live_bots` code imports the correct library.
