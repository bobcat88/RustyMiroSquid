# Resume: Trading Strategies for AI Agents in RustyMiroSquid

## Overview
This resume outlines the key elements to implement in **RustyMiroSquid's AI Agents**, based on the analysis of modern **SMC (Smart Money Concepts)** and **Claude 3.5 Sonnet** trading logic.

### 1- Strategic Pillars (What to Build)

#### **A. Perception Layer: The Multi-Pair Scanner**
- **Breadth Advantage**: Unlike humans, the AI should monitor 50+ pairs simultaneously for "Liquidity Sweeps" of multi-day highs/lows.
- **Fair Value Gaps (FVG)**: Automated detection of "Liquidity Voids" where price is 80% likely to return.
- **Order Block (OB) Identification**: Mapping zones where volume and spread indicates institutional entry.
- **Sentiment & "Market Color" (OVTLYR Logic)**: Behavioral analysis to track **Fear / Greed**. Detect "Sentiment Extremes" where a reversal is imminent.

#### **B. Reasoning Layer: The "Claude-Like" Logic**
- **Contextual Validation**: Every trade must pass a 3-step check:
    1. **Trend Alignment**: Is the H1/H4 structure bullish or bearish?
    2. **Liquidity Sweep**: Has "Retail" liquidity been cleared?
    3. **Structure Shift (MSS)**: Has price shifted direction on a lower timeframe (M1/M5)?
- **Trading Plan Selection**: Selecting the right plan based on "Market Color":
    - **Plan A (Aggressive)**: High-momentum individual stocks.
    - **Plan ETF (Defensive)**: Index-based strategy focused on Breadth.
    - **SICADFU (Sit In Cash And Don't F*ck Up)**: Forced 100% cash when sentiment is too extreme or choppy.

#### **C. Execution Layer: Dynamic Trading**
- **Kill Zone Timing**: Restrict high-frequency entries to London/New York Open overlaps (08:00-10:00 & 14:00-16:00 UTC).
- **Pine Script V5 Generation**: The agent should output a `V5 Pine Script` indicator for every trade, allowing the user to visually verify the reasoning on TradingView.
- **Dynamic Risk Management**: 
    - **R:R Ratio**: Minimum 1:3 for general setups; 1:5+ for "Sniper" entries inside institutional zones.
    - **Risk per Trade**: Strict 0.5% - 1% of total account balance.
    - **Protective Stops**: Move Stop Loss to Break Even (BE) after the first 1:1 displacement or Market Structure Shift.
    - **Scaling Out**: Take 50% partial profits at 1:2 R:R to secure the "Running Free" portion.

### 2- Assets & Scanning Filters

| **Asset Type** | **Recommended Symbols** | **Selection Logic** |
| :--- | :--- | :--- |
| **Indices / ETFs** | **SPY, QQQ, TQQQ, DAX 40** | Highest liquidity; perfect institutional "footprints." |
| **Stocks** | **NVDA, APPL, MSFT, TSLA** | Massive volume, respect for FVGs and Order Blocks. |
| **Scanner Signals** | **Buy: Sweep + MSS + FVG** | Only trade when retail is "swept" and structure shifts. |
| **Exit Signal** | **Opposite Liquidity / Fixed R:R** | Close at equal highs or fixed 1:3/1:5 ratio. |

### 3- Critical "Do's & Don'ts" for the Agent

| **DO** | **DON'T** |
| :--- | :--- |
| **Implement Multi-Timeframe (MTF) analysis**: M1 entries must align with H1/H4 structure. | **Don't use retail indicators**: Zero reliance on RSI, MACD, or EMA crossovers as primary triggers. |
| **Force "Logic" output**: The agent must explain *why* it's taking a trade in plain text. | **Don't ignore News Volatility**: Implement an "Economic Calendar" filter to stop trading during CPI/FOMC. |
| **Automate Backtesting**: Use the RustyMiroSquid engine to validate SMC setups on historical data. | **Don't trade the "Middle of the Range"**: Only act at the Extremes (Liquidity Pools). |

### 3- Roadmap for RustyMiroSquid Implementation

1. **Phase 1: The Scanner (Rust backend)**: Implement high-performance data processing to find FVGs and OBs across all pairs.
2. **Phase 2: The LLM Brain (Python API)**: Connect Claude 3.5 Sonnet to evaluate the "Scanner" outputs and provide the MSS validation.
3. **Phase 3: Transparency UI (Vite frontend)**: Create a dashboard that shows the "Scanner" detections and the AI's "Reasoning" in real-time.
4. **Phase 4: Auto-Pine Script**: Add a feature to "Copy to TradingView" for any AI-identified zone.

---
*Targeted Architecture for RustyMiroSquid v1.2+*

### Sources
1. **YouTube Analysis (Kasper - SMC & Claude 3.5)**: 
    - [Analysis-RCej60ozIDQ.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/docs/analysis/Analysis-RCej60ozIDQ.md)
    - [Analysis-j9Fg3PaqVmk.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/docs/analysis/Analysis-j9Fg3PaqVmk.md)
    - [Analysis-sLmUHb4WloQ.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/docs/analysis/Analysis-sLmUHb4WloQ.md)
2. **Trader/Fund Manager Plans (OVTLYR)**:
    - [OVTLYR-Fund-Manager-Plans.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/docs/analysis/OVTLYR-Fund-Manager-Plans.md)
    - Internal Document: *OVTLYR Trading Plans A, M, ETF & SICADFU.pptx*
