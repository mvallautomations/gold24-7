//+------------------------------------------------------------------+
//|                                  BTCUSD_Pullback_Benchmark_EA.mq5|
//|                 GOLD24-7 Production-Grade Bitcoin Expert Advisor |
//|   Specialized for XM MT5 BTCUSD# / 24/7 Crypto Continuous Market  |
//|   Fixes: Completed-Bar Logic (Shift 1), Full BUY/SELL Symmetry,  |
//|          Relative ATR Filter, Crypto Spread & Dynamic Lot Sizing |
//+------------------------------------------------------------------+
#property copyright "GOLD24-7 Research Stack"
#property link      "https://github.com/mvallautomations/gold24-7"
#property version   "2.00"

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "=== Risk & Execution ==="
input string InpSymbol           = "BTCUSD#"; // Symbol (empty = current chart, default = BTCUSD#)
input double InpRiskPerTrade     = 1.0;       // Risk per trade (% of Balance)
input double InpATRStopMult      = 1.8;       // Stop Loss in ATR multiples (Crypto buffer)
input double InpRewardRatio      = 1.6;       // Take Profit ratio (TP = SL * Ratio)
input ulong  InpMagicNumber      = 240702;    // EA Magic Number (BTCUSD Expert)
input ulong  InpSlippagePoints   = 50;        // Max execution slippage in points

input group "=== Relative Volatility Envelope ==="
input int    InpATRPeriod        = 14;        // ATR Period
input int    InpHistLookback     = 100;       // Historical ATR Distribution Window
input double InpMinATRPercentile = 15.0;      // Minimum ATR Percentile (Avoid dead chop)
input double InpMaxATRPercentile = 88.0;      // Maximum ATR Percentile (Avoid extreme liquidation wicks)
input bool   InpFilterSpread     = true;      // Enable Spread Filter
input int    InpMaxSpreadPoints  = 2500;      // Max allowable spread in points (2500 pts = $25.00 on BTC)

input group "=== Session Filter ==="
input bool   InpFilterSession    = false;     // Restrict sessions (false = 24/7 Crypto continuous)
input int    InpStartHour        = 0;
input int    InpEndHour          = 24;

//--- Global Objects & Handles
CTrade trade;
int    atr_handle = INVALID_HANDLE;
string trade_symbol;
double atr_history[];

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
{
   trade_symbol = (InpSymbol == "") ? _Symbol : InpSymbol;

   if(!SymbolSelect(trade_symbol, true))
   {
      // Fallback search if broker appends/omits suffix
      if(SymbolSelect("BTCUSD#", true))
         trade_symbol = "BTCUSD#";
      else if(SymbolSelect("BTCUSD", true))
         trade_symbol = "BTCUSD";
      else
      {
         Print("[!] Error: Failed to select BTC symbol: ", trade_symbol);
         return(INIT_FAILED);
      }
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(trade_symbol);

   atr_handle = iATR(trade_symbol, PERIOD_M1, InpATRPeriod);
   if(atr_handle == INVALID_HANDLE)
   {
      Print("[!] Error: Failed to create M1 ATR handle for ", trade_symbol);
      return(INIT_FAILED);
   }

   ArraySetAsSeries(atr_history, true);
   ArrayResize(atr_history, InpHistLookback);

   Print("[+] BTCUSD_Pullback_Benchmark_EA initialized successfully on ", trade_symbol);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(atr_handle != INVALID_HANDLE)
      IndicatorRelease(atr_handle);
   Print("[-] BTCUSD_Pullback_Benchmark_EA deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Relative Volatility Assessment                                   |
//+------------------------------------------------------------------+
bool IsVolatilityTradable(double &out_current_atr)
{
   if(atr_handle == INVALID_HANDLE) return(false);

   double buf[];
   ArraySetAsSeries(buf, true);
   int copied = CopyBuffer(atr_handle, 0, 1, InpHistLookback, buf);
   if(copied < InpATRPeriod + 5) return(false);

   out_current_atr = buf[0]; // Completed bar ATR (shift 1)

   // Calculate percentile rank of current ATR
   int count_below = 0;
   for(int i = 0; i < copied; i++)
   {
      if(buf[i] <= out_current_atr)
         count_below++;
   }

   double percentile = ((double)count_below / (double)copied) * 100.0;
   return(percentile >= InpMinATRPercentile && percentile <= InpMaxATRPercentile);
}

//+------------------------------------------------------------------+
//| Spread Verification                                              |
//+------------------------------------------------------------------+
bool SpreadOK()
{
   if(!InpFilterSpread) return(true);
   long spread = SymbolInfoInteger(trade_symbol, SYMBOL_SPREAD);
   return(spread <= InpMaxSpreadPoints);
}

//+------------------------------------------------------------------+
//| Position Guard                                                   |
//+------------------------------------------------------------------+
bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == trade_symbol)
      {
         if(PositionGetInteger(POSITION_MAGIC) == (long)InpMagicNumber)
            return(true);
      }
   }
   return(false);
}

//+------------------------------------------------------------------+
//| Symmetrical Signal Detection on Completed Candles (Shift 1 & 2)  |
//+------------------------------------------------------------------+
int CheckSymmetricalSetup(double current_atr)
{
   // Strictly inspect completed candles:
   // Bar 1 = Most recently closed candle
   // Bar 2 = Impulse candle before bar 1
   double c1 = iClose(trade_symbol, PERIOD_M1, 1);
   double o1 = iOpen(trade_symbol, PERIOD_M1, 1);
   double h1 = iHigh(trade_symbol, PERIOD_M1, 1);
   double l1 = iLow(trade_symbol, PERIOD_M1, 1);

   double c2 = iClose(trade_symbol, PERIOD_M1, 2);
   double o2 = iOpen(trade_symbol, PERIOD_M1, 2);
   double h2 = iHigh(trade_symbol, PERIOD_M1, 2);
   double l2 = iLow(trade_symbol, PERIOD_M1, 2);

   double mid2 = (h2 + l2) / 2.0;

   // 1. Bullish Setup: Bar 2 was bullish impulse, Bar 1 is shallow pullback into upper half
   bool impulse_up = (c2 > o2) && ((c2 - o2) > (current_atr * 0.45));
   bool pullback_shallow_up = (c1 < c2) && (c1 > mid2) && (l1 > l2);
   if(impulse_up && pullback_shallow_up)
      return(1); // BUY

   // 2. Bearish Setup: Bar 2 was bearish impulse, Bar 1 is shallow pullback into lower half
   bool impulse_down = (c2 < o2) && ((o2 - c2) > (current_atr * 0.45));
   bool pullback_shallow_down = (c1 > c2) && (c1 < mid2) && (h1 < h2);
   if(impulse_down && pullback_shallow_down)
      return(-1); // SELL

   return(0); // NONE
}

//+------------------------------------------------------------------+
//| Dynamic Lot Size Calculation based on Stop Distance Price        |
//+------------------------------------------------------------------+
double CalculateLotSize(double stop_distance_price)
{
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_money = balance * (InpRiskPerTrade / 100.0);

   double tick_size  = SymbolInfoDouble(trade_symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(trade_symbol, SYMBOL_TRADE_TICK_VALUE);

   if(tick_size <= 0 || tick_value <= 0 || stop_distance_price <= 0)
      return(SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MIN));

   double risk_per_lot = (stop_distance_price / tick_size) * tick_value;
   if(risk_per_lot <= 0) return(SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MIN));

   double raw_lot = risk_money / risk_per_lot;

   double min_lot  = SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MIN);
   double max_lot  = SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_STEP);

   double lot = MathFloor(raw_lot / lot_step) * lot_step;
   if(lot < min_lot) lot = min_lot;
   if(lot > max_lot) lot = max_lot;

   return(NormalizeDouble(lot, 2));
}

//+------------------------------------------------------------------+
//| OnTick Event Handler                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check bar arrival: Only run execution on arrival of a new M1 bar
   static datetime last_bar_time = 0;
   datetime current_bar_time = iTime(trade_symbol, PERIOD_M1, 0);

   if(current_bar_time == last_bar_time) return; // Wait for new candle
   last_bar_time = current_bar_time;

   // 1. Guard against multiple simultaneous positions
   if(HasOpenPosition()) return;

   // 2. Spread filter
   if(!SpreadOK()) return;

   // 3. Volatility filter
   double current_atr = 0.0;
   if(!IsVolatilityTradable(current_atr)) return;

   // 4. Symmetrical Setup Detection on completed candles (shift 1 & 2)
   int signal = CheckSymmetricalSetup(current_atr);
   if(signal == 0) return;

   // 5. Order execution
   double ask = SymbolInfoDouble(trade_symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(trade_symbol, SYMBOL_BID);
   int digits = (int)SymbolInfoInteger(trade_symbol, SYMBOL_DIGITS);

   double sl_distance = current_atr * InpATRStopMult;
   double tp_distance = sl_distance * InpRewardRatio;
   double lot_size = CalculateLotSize(sl_distance);

   if(signal == 1) // BUY
   {
      double sl = NormalizeDouble(ask - sl_distance, digits);
      double tp = NormalizeDouble(ask + tp_distance, digits);
      trade.Buy(lot_size, trade_symbol, ask, sl, tp, "BTCUSD# Benchmark Buy");
   }
   else if(signal == -1) // SELL
   {
      double sl = NormalizeDouble(bid + sl_distance, digits);
      double tp = NormalizeDouble(bid - tp_distance, digits);
      trade.Sell(lot_size, trade_symbol, bid, sl, tp, "BTCUSD# Benchmark Sell");
   }
}
//+------------------------------------------------------------------+
