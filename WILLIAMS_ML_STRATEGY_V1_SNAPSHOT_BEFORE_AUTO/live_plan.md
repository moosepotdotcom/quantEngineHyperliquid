
# 🪵 The $53 "Seed" Growth Plan
*Systematic approach to growing a small account specific to Williams V1 Strategy.*

## Core Principles
1.  **Survival First:** With $53, a string of 5 losses can wipe out 15% of your equity. We must prevent this.
2.  **Aggressive but Capped:** We use leverage to make the wins meaningful, but cap the *Risk Per Trade* to <2%.
3.  **Compound Wins:** We reinvest profits immediately.

---

## 🚦 Phase 1: "The Sprout" ($53 ➔ $100)
**Goal:** Double the account.
**Mode:** Strict Discipline.

-   **Leverage:** **3x** (Effective Position Size: ~$150 USD).
-   **Risk Per Trade:**
    -   Stop Loss: 1.5%.
    -   Loss Amount: $150 * 1.5% = **$2.25** (4.2% of account).
    -   *Note: This is high, but necessary for a small account. Do not exceed 3x.*
-   **Take Profit:** 0.7% (~$1.05 per win).
-   **Daily Stop:** If you lose **$5** in a day (2 trades), **STOP**.

### Instructions
1.  Run `live_trader.py`.
2.  When it finds a signal (🔥), it will tell you to BUY or SELL $150 worth of the coin.
3.  **Manually** place this trade on Hyperliquid (or verify the bot does it).
4.  **IMMEDIATELY** set the TP and SL.
    -   *The bot calculates these for you.*

---

## 🌿 Phase 2: "The Sapling" ($100 ➔ $500)
**Goal:** Establish a buffer.
**Mode:** Conservative Growth.

-   **Leverage:** **Reduce to 2x** (Effective Size: ~$200-$1000).
-   **Why Lower Leverage?** You have more to lose now. Protect the seed.
-   **Risk Per Trade:**
    -   Position: 2x Balance.
    -   Loss: 1.5% of Position = 3% of Balance.
-   **Daily Stop:** 5% of Balance.

---

## 🌳 Phase 3: "The Tree" ($500+)
**Goal:** Income Generation.
**Mode:** Portfolio Scaling.

-   **Leverage:** **1x - 2x** (Variable).
-   **Diversification:** Split size across 2-3 simultaneous trades (e.g., BTC + SOL).
-   **Automation:** Fully trust the `live_trader.py` auto-execution.

---

## ⚠️ Critical Rules (Do Not Break)
1.  **NEVER Move the Stop Loss:** If the bot says SL is at 95.50, it stays at 95.50.
2.  **NO FOMO:** If you missed the entry by 5 minutes, **skip it**.
3.  **Check Funding:** Don't hold Shorts if funding is extremely negative (paying -0.1%/hour).
