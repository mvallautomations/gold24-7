# Architectural Audit & Benchmark Report: M1 Pullback Baseline EA

**Subject**: `NN_Crypto_Scalper.mq5` (Conceptual Identifier: `M1_Pullback_Baseline_EA`)  
**File Location**: `/mnt/c/Users/Legion/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/NN_Crypto_Scalper.mq5`  
**Classification**: Deterministic M1 Bullish Heuristic (Not a Neural Network)

---

## 1. Executive Summary

`NN_Crypto_Scalper.mq5` serves as the historical baseline for M1 momentum scalping in this repository. Although titled `NN_Crypto_Scalper`, comprehensive static code analysis reveals **zero neural network or machine learning components**. It is a purely heuristic 2-bar price action script.

While it contains sound broker safety boilerplate (Magic numbers, deviation control, spread gating), its mathematical core suffers from five critical structural flaws that invalidate live deployment and skew historical backtesting.

---

## 2. Line-by-Line Breakdown of Structural Flaws

### Flaw 1: Unclosed Forming Bar Lookahead (`shift = 0`)
* **Code Reference** (Lines 136, 145):
  ```mql5
  double c0 = iClose(trade_symbol, PERIOD_M1, 0);
  double c1 = iClose(trade_symbol, PERIOD_M1, 1);
  ...
  bool pullback_shallow = (c0 < c1 && c0 > mid1);
  ```
* **Vulnerability**: `c0` is the price of the *currently forming* M1 candle. In `OnTick()`, when a new minute starts, `c0` is merely the opening tick. If price dips momentarily into the upper half of bar 1 during tick 2, `HasBullScalpSetup()` evaluates to `true` and triggers an immediate market buy. However, by the close of minute 0, the bar may have completely broken below `mid1` or formed a massive bearish engulfing candle.
* **Remedy**: All signal evaluation must be anchored strictly on completed bars:
  `shift = 1` (completed signal bar) and `shift = 2` (completed impulse bar).

---

### Flaw 2: Total Absence of SELL Symmetry
* **Code Reference** (Lines 187–225):
  ```mql5
  if(HasBullScalpSetup())
  {
      ...
      trade.Buy(lots, trade_symbol, ask_price, sl, tp, "NN Scalp Buy");
  }
  ```
* **Vulnerability**: The EA only has `HasBullScalpSetup()`. There is no corresponding `HasBearScalpSetup()` or `trade.Sell()`. In downtrending or mean-reverting regimes, the system suffers severe adverse selection, buying shallow pullbacks directly into aggressive selloffs.
* **Remedy**: Implement symmetrical bearish setup:
  Impulse down (`c2 > c1`), shallow pullback up (`c1 > c2 && c1 < mid2`), selling at completed bar confirmation with stop loss above impulse high.

---

### Flaw 3: Ineffective Volatility Filter (`ATR > 0`)
* **Code Reference** (Lines 87–96):
  ```mql5
  bool VolatilityOK()
  {
     if(atr_handle == INVALID_HANDLE) return(false);
     double atr_buf[1];
     if(CopyBuffer(atr_handle, 0, 1, 1, atr_buf) <= 0) return(false);
     return(atr_buf[0] > 0.0);
  }
  ```
* **Vulnerability**: On any active trading instrument, ATR is mathematically greater than 0 at all times. Checking `atr_buf[0] > 0.0` provides zero filtering against illiquid chop, weekend spreads, or high-impact news spikes.
* **Remedy**: Replace with **Relative ATR** assessment comparing current ATR to rolling historical distribution percentiles (e.g. tradable between 20th and 85th percentiles).

---

### Flaw 4: Hardcoded Fixed Stop Points Across Instruments
* **Code Reference** (Line 11):
  ```mql5
  input double InpFixedStopPoints = 5000.0;
  ```
* **Vulnerability**: 5,000 points on BTCUSD represents $50. On XAUUSD (Gold 2-decimal), 5,000 points is $50.00 (a massive 2% swing). On 3-decimal Gold (GAUUSD), it is $5.00. On EURUSD, 5,000 points is 500 pips! A fixed point setting cannot be transferred between instruments.
* **Remedy**: Anchor Stop Loss dynamically to `ATR(14) * multiplier` (e.g. `1.5 * ATR`).

---

### Flaw 5: Lot Sizing Execution Risk
* **Code Reference** (Lines 153–182):
  `CalculateLotSize()` divides balance risk by `ticks_at_risk * tick_value`. While formulaically valid, in fast-moving markets or gap opens, slippage on M1 can easily exceed the fixed stop distance, causing realized losses to surpass the nominal 1% risk threshold.

---

## 3. Benchmark Status & Role in GOLD24-7

Per project rules:
1. `NN_Crypto_Scalper.mq5` will **NOT be deleted**. It is preserved in its original location and documented as the baseline.
2. An upgraded benchmark EA (`M1_Pullback_Benchmark_EA.mq5`) is authored in `core/` resolving all five flaws.
3. All new strategies in the GOLD24-7 research platform are backtested and evaluated against this baseline.
