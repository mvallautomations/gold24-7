//+------------------------------------------------------------------+
//|                                           NN_Crypto_Scalper.mq5  |
//|                        Corrected & Production-Ready MQL5 Edition |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

//--- Input Parameters
input group "=== Trade Settings ==="
input string InpSymbol           = "";       // Symbol (leave empty for current chart)
input double InpRiskPerTrade     = 1.0;      // Risk per trade (% of Balance)
input double InpFixedStopPoints  = 5000.0;   // Stop Loss in Points (e.g., 5000 = $50 on 2-decimal BTC)
input double InpRewardRatio      = 1.5;      // Take Profit ratio (TP = SL * Ratio)
input ulong  InpMagicNumber      = 261026;   // EA Magic Number

input group "=== Filters & Sessions ==="
input bool   InpFilterSpread     = true;     // Enable Max Spread Filter
input int    InpMaxSpreadPoints  = 2500;     // Max allowable spread in points
input bool   InpFilterSession    = false;    // Restrict to London/NY sessions (false for 24/7 Crypto)
input int    InpLondonStartHour  = 8;        // London Open Server Hour
input int    InpLondonEndHour    = 12;       // London Close Server Hour
input int    InpNYStartHour      = 13;       // NY Open Server Hour
input int    InpNYEndHour        = 17;       // NY Close Server Hour

//--- Global Variables
CTrade trade;
int    atr_handle = INVALID_HANDLE;
string trade_symbol;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Set symbol to current chart if not explicitly specified
   trade_symbol = (InpSymbol == "") ? _Symbol : InpSymbol;

   if(!SymbolSelect(trade_symbol, true))
   {
      Print("[!] Error: Failed to select symbol: ", trade_symbol);
      return(INIT_FAILED);
   }

   // Initialize CTrade with Magic Number and safe execution parameters
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(20);
   trade.SetTypeFillingBySymbol(trade_symbol);

   // Create M5 ATR handle for volatility monitoring
   atr_handle = iATR(trade_symbol, PERIOD_M5, 14);
   if(atr_handle == INVALID_HANDLE)
   {
      Print("[!] Error: Failed to create ATR handle for ", trade_symbol);
      return(INIT_FAILED);
   }

   Print("[+] NN_Crypto_Scalper successfully initialized on ", trade_symbol);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(atr_handle != INVALID_HANDLE)
      IndicatorRelease(atr_handle);

   Print("[-] NN_Crypto_Scalper deinitialized. Reason code: ", reason);
}

//+------------------------------------------------------------------+
//| Spread Verification                                              |
//+------------------------------------------------------------------+
bool SpreadOK()
{
   if(!InpFilterSpread) return(true);

   long spread = SymbolInfoInteger(trade_symbol, SYMBOL_SPREAD);
   if(spread <= InpMaxSpreadPoints) return(true);

   return(false);
}

//+------------------------------------------------------------------+
//| Volatility Verification                                          |
//+------------------------------------------------------------------+
bool VolatilityOK()
{
   if(atr_handle == INVALID_HANDLE) return(false);

   double atr_buf[1];
   // Read completed bar (index 1) for stable reading
   if(CopyBuffer(atr_handle, 0, 1, 1, atr_buf) <= 0) return(false);

   return(atr_buf[0] > 0.0);
}

//+------------------------------------------------------------------+
//| Session Filter                                                   |
//+------------------------------------------------------------------+
bool IsActiveSession()
{
   if(!InpFilterSession) return(true); // Crypto runs 24/7 by default

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int h = dt.hour;

   bool london = (h >= InpLondonStartHour && h < InpLondonEndHour);
   bool ny     = (h >= InpNYStartHour     && h < InpNYEndHour);

   return(london || ny);
}

//+------------------------------------------------------------------+
//| Check if this EA already has an open position on this symbol     |
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
//| Scalping Signal: Impulse followed by shallow pullback            |
//+------------------------------------------------------------------+
bool HasBullScalpSetup()
{
   double c0 = iClose(trade_symbol, PERIOD_M1, 0);
   double c1 = iClose(trade_symbol, PERIOD_M1, 1);
   double c2 = iClose(trade_symbol, PERIOD_M1, 2);

   double h1 = iHigh(trade_symbol, PERIOD_M1, 1);
   double l1 = iLow(trade_symbol, PERIOD_M1, 1);

   bool impulse_up = (c1 > c2);
   double mid1 = (h1 + l1) / 2.0;
   bool pullback_shallow = (c0 < c1 && c0 > mid1);

   return(impulse_up && pullback_shallow);
}

//+------------------------------------------------------------------+
//| Lot Size Calculation with Strict Risk & Broker Constraints       |
//+------------------------------------------------------------------+
double CalculateLotSize(double stop_distance_price)
{
   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_money= balance * (InpRiskPerTrade / 100.0);

   double tick_size = SymbolInfoDouble(trade_symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value= SymbolInfoDouble(trade_symbol, SYMBOL_TRADE_TICK_VALUE);

   if(stop_distance_price <= 0.0 || tick_size <= 0.0 || tick_value <= 0.0)
      return(SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MIN));

   // Calculate value lost per 1 lot over the stop loss distance
   double ticks_at_risk = stop_distance_price / tick_size;
   double loss_per_lot  = ticks_at_risk * tick_value;

   if(loss_per_lot <= 0.0)
      return(SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MIN));

   double lots = risk_money / loss_per_lot;

   // Enforce broker lot step, min, and max limits
   double min_lot = SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_MAX);
   double lot_step= SymbolInfoDouble(trade_symbol, SYMBOL_VOLUME_STEP);

   lots = MathFloor(lots / lot_step) * lot_step;
   lots = MathMax(min_lot, MathMin(lots, max_lot));

   return(NormalizeDouble(lots, 2));
}

//+------------------------------------------------------------------+
//| Main OnTick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Check if filters pass
   if(!SpreadOK())        return;
   if(!VolatilityOK())    return;
   if(!IsActiveSession()) return;

   // 2. Prevent stacking multiple positions on the same pair
   if(HasOpenPosition())  return;

   // 3. Only evaluate once per new candle to prevent rapid tick over-trading
   static datetime last_bar_time = 0;
   datetime current_bar_time = iTime(trade_symbol, PERIOD_M1, 0);
   if(current_bar_time == last_bar_time) return;

   // 4. Check setup condition
   if(HasBullScalpSetup())
   {
      double point = SymbolInfoDouble(trade_symbol, SYMBOL_POINT);
      int digits   = (int)SymbolInfoInteger(trade_symbol, SYMBOL_DIGITS);

      double stop_distance = InpFixedStopPoints * point;
      double lots          = CalculateLotSize(stop_distance);

      double ask_price = SymbolInfoDouble(trade_symbol, SYMBOL_ASK);
      double sl        = NormalizeDouble(ask_price - stop_distance, digits);
      double tp        = NormalizeDouble(ask_price + (stop_distance * InpRewardRatio), digits);

      if(trade.Buy(lots, trade_symbol, ask_price, sl, tp, "NN Scalp Buy"))
      {
         Print("[✓] Trade Opened: BUY ", lots, " lots on ", trade_symbol, " at ", ask_price);
         last_bar_time = current_bar_time; // Lock until next bar
      }
      else
      {
         Print("[!] OrderSend failed. Retcode: ", trade.ResultRetcode(), " | Description: ", trade.ResultRetcodeDescription());
      }
   }
}
//+------------------------------------------------------------------+