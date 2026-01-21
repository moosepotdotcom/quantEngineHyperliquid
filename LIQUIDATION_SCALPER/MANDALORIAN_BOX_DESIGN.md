# 🛡️ MandalorianBox: Terminal Command Center

## Concept
A high-performance, immersive Terminal User Interface (TUI) for monitoring the Hyperliquid data stream.
"This is the Way."

## 🎨 Aesthetics & Theme
- **Style:** Cyberpunk / Sci-Fi / Mandalorian.
- **Colors:**
    - **Beskar Silver (White/Grey):** UI Frames & Headers.
    - **Laser Green:** Buy Orders / Profit.
    - **Blaster Red:** Sell Orders / Loss.
    - **Deep Space Black:** Background.
- **Typography:** ASCII Art headers, monospaced clean data.

## 🖥️ UI Layout (Curses Based)
The terminal will be divided into 4 active zones:

```text
+---------------------------------------------------------------+
|  🛡️ MANDALORIAN BOX  |  BTC: $95,780  |  STATUS: HUNTING      |
+---------------------------+-----------------------------------+
|  📊 MARKET INTEL          |  🐋 WHALE RADAR (Orders > $50k)   |
|  -----------------------  |  -------------------------------  |
|  Vol (1m): $2.4M          |  00:50:04 SELL $478k @ 95783      |
|  Trend: ⬇️ BEARISH        |  00:50:04 SELL $304k @ 95783      |
|  Sentiment: Fear          |  00:49:55 BUY  $102k @ 95790      |
|                           |  00:49:12 BUY  $55k  @ 95792      |
|                           |                                   |
+---------------------------+-----------------------------------+
|  📜 THE TAPE (Live Stream)                                    |
|  -----------------------------------------------------------  |
|  95780.0  |  0.021 BTC  |  BUY   |  0x89...29 (Smart Money)   |
|  95779.5  |  0.500 BTC  |  SELL  |  0xd4...1d (Whale)        |
|  ... (Scrolling at 100ms) ...                                 |
+---------------------------------------------------------------+
|  🤖 SYSTEM LOGS: Active Short | PnL: +$201 (0.21%) | TP HIT 🏆|
+---------------------------------------------------------------+
```

## 🚀 Features & Recommendations

### 1. "The Guild" (Smart Money Tracker)
- **Idea:** The logs contain `users` (wallet addresses).
- **Feature:** We can track specific addresses. If address `0x...A` wins often, tag them as "Mandalorian". If they lose, tag as "Stormtrooper".
- **Implementation:** Maintain a dynamic leaderboard in memory.

### 2. "Beskar Shield" (Risk Viz)
- **Idea:** Visual bar showing distance to Liquidation or Stop Loss.
- **Feature:** As price moves closer to SL, the shield bar depletes (turns red).

### 3. "Whistling Birds" (Multi-Whale Alert)
- **Idea:** Detect coordinated attacks.
- **Feature:** If >3 Whales execute in <1 second (like we saw), flash the screen or play a beep.

### 4. "Grogu" Mode (Idle)
- **Idea:** When volatility is low, show a resting animation. When vol spikes, wake up.

## 🛠️ Technical Stack
- **Language:** Python 3.9+
- **Library:** `curses` (Standard Lib) - No pip install needed. FAST.
- **Data Source:** `logs/collector_debug.log` (Tail).
- **Architecture:** Async IO (Threaded Reader + Main UI Loop).
