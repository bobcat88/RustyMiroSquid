# Strategy Guide: Risk Management, R:R & Asset Selection

## 1. Risk-to-Reward (R:R) Strategies

The strategies observed in the **SMC (Smart Money Concepts)** and **Claude 3.5** videos revolve around a "Precision Entry" model that maximizes R:R while strictly limiting risk.

### The "Gold Standard" R:R Ratio
- **Minimum 1:3**: A 1:3 ratio is considered the baseline. With this ratio, an AI agent only needs a **33% win rate** to break even. Any win rate above 40% (achievable with SMC precision) leads to high profitability.
- **The "Sniper" Goal (1:5 to 1:10)**: By using lower timeframe (M1/M5) confirmation inside higher timeframe (H1/H4) zones, traders target 1:5+ ratios.

### Risk Mitigation Techniques
- **Move to Break Even (BE)**: Move the Stop Loss to the entry price as soon as price achieves a **displacement** (a strong impulsive move) or reaches 1:1 R:R. This creates a "risk-free" trade.
- **Scaling Out (Partial Profits)**: Take 50% of the position at 1:2. Even if the remaining 50% hits BE, the trade is overall profitable and psychologically easier for the user to watch.
- **Risk per Trade**: Never exceed **0.5% to 1%** of the total account balance per trade.

## 2. Recommended Assets for SMC Scanning

SMC and AI-driven strategies work best in **high-liquidity** environments where institutional "footprints" (Order Blocks, Gaps) are clearly visible.

### Best Indices & ETFs (Top Priority)
These provide the clearest market structure and the most reliable "Liquidity Sweeps."
- **SPY (S&P 500 ETF)**: High liquidity, perfect for broad market structure analysis.
- **QQQ (Nasdaq-100 ETF)**: Best for volatility and identifying tech-driven liquidity pools.
- **TQQQ (ProShares UltraPro QQQ)**: A 3x leveraged version for high-conviction intraday setups (use with caution).
- **DIA (Dow Jones ETF)**: Reliable for "Value" based SMC setups.

### Top Individual Stocks
Focus only on **Large-Cap Blue Chips** with massive daily volume:
- **NVDA (Nvidia)**: Currently the most liquid stock for volatility and gap fills.
- **AAPL (Apple)**: Extremely respectful of historical support/resistance and FVGs.
- **TSLA (Tesla)**: Frequent "Liquidity Sweeps" of multi-day highs/lows.
- **MSFT (Microsoft)**: Very clean market structure for trend following.

## 3. Scanning Signals: Implementation for RustyMiroSquid

To automate these strategies, the AI agents should scan for the following specific triggers:

### Buy Signal (Entry Point)
1. **Liquidity Sweep**: Price breaches a previous 24-hour low and quickly rejects it.
2. **MSS (Market Structure Shift)**: On a lower timeframe (M5), the previous high is broken with a strong candle.
3. **Entry Point**: A limit order is placed at the **Fair Value Gap (FVG)** or the **Order Block (OB)** created during the MSS.

### Exit Signal (Take Profit & Protection)
1. **Primary Target**: The opposite Liquidity Pool (the previous session high or equal highs).
2. **Secondary Target**: A fixed R:R of 1:3 or 1:5.
3. **Exit on Invalidation**: If price closes below the "Sweep" wick, the trade logic is invalidated—close immediately to minimize loss.

---
*Developed for the RustyMiroSquid Strategy Engine - 2026*
