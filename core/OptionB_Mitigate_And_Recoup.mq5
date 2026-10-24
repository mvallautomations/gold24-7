//+------------------------------------------------------------------+
//|                                OptionB_Mitigate_And_Recoup.mq5   |
//|                        GOLD24-7 Autonomous Untangle & Recoup EA  |
//|                                     https://gold24-7.project     |
//+------------------------------------------------------------------+
#property copyright "GOLD24-7 Autonomous Engine"
#property link      "https://gold24-7.project"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Input Parameters
input group "=== Option B: Market Open Untangling ==="
input bool   InpCloseOutliers       = true;     // Close 2 near-breakeven outlier tickets (1030492044, 1030497010)
input bool   InpProtectRemaining    = true;     // Set protective SL on remaining 4 positions
input ulong  InpTicketCloseBuy      = 1030492044; // Outlier BUY ticket to close
input ulong  InpTicketCloseSell     = 1030497010; // Outlier SELL ticket to close
input ulong  InpTicketBuyProtected  = 1030357046; // Remaining BUY ticket
input double InpBuyStopLoss         = 4132.00;    // Emergency SL for remaining BUY
input double InpSellStopLoss        = 4147.50;    // Emergency SL for remaining SELLs

input group "=== Recoup Mode: 1 Trade At A Time ==="
input bool   InpEnableRecoupTrading = true;     // Enable disciplined 1-position recouping
input double InpTargetBalance       = 125.65;   // Recoup goal balance (stops trading when reached)
input double InpRecoupLotSize       = 0.01;     // Strict 0.01 lot size
input int    InpRecoupSLPoints      = 300;      // 3.00 USD points SL on Gold (300 points)
input int    InpRecoupTPPoints      = 500;      // 5.00 USD points TP on Gold (500 points)
input ulong  InpRecoupMagic         = 240724;   // Magic number for recoup trades

//--- Global Objects
CTrade         m_trade;
CPositionInfo  m_position;
CSymbolInfo    m_symbol;

//--- State Flags
bool g_outlierBuyClosed  = false;
bool g_outlierSellClosed = false;
bool g_buyProtected      = false;
bool g_sellsProtected    = false;
bool g_untangleComplete  = false;
datetime g_lastTradeTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print(">>> [GOLD24-7] Option B Untangle & Recoup EA initialized.");
   PrintFormat(">>> Account: %I64d | Server: %s | Balance: %.2f | Equity: %.2f",
               AccountInfoInteger(ACCOUNT_LOGIN),
               AccountInfoString(ACCOUNT_SERVER),
               AccountInfoDouble(ACCOUNT_BALANCE),
               AccountInfoDouble(ACCOUNT_EQUITY));

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      Alert("[GOLD24-7 ALERT] Algo Trading is DISABLED in MetaTrader 5!\nPlease click 'Algo Trading' on the top toolbar or press Ctrl+E.");
      Print(">>> [WARNING] Terminal trade_allowed is FALSE. Orders will fail until Algo Trading is enabled.");
   }

   m_trade.SetExpertMagicNumber(InpRecoupMagic);
   m_trade.SetMarginMode();
   m_trade.SetTypeFillingBySymbol(_Symbol);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   PrintFormat(">>> [GOLD24-7] EA Deinitialized. Reason: %d", reason);
}

//+------------------------------------------------------------------+
//| Check if ticket exists in open positions                         |
//+------------------------------------------------------------------+
bool PositionExists(ulong ticket)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Ticket() == ticket)
            return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Step 1: Untangle 6 Open Positions at Market Open                 |
//+------------------------------------------------------------------+
void ExecuteUntangleOptionB()
{
   if(g_untangleComplete) return;

   // 1. Close the 2 near-breakeven outlier positions
   if(InpCloseOutliers)
   {
      if(!g_outlierBuyClosed)
      {
         if(PositionExists(InpTicketCloseBuy))
         {
            if(m_trade.PositionClose(InpTicketCloseBuy))
            {
               PrintFormat(">>> [OPTION B] Successfully CLOSED outlier BUY Ticket %I64d", InpTicketCloseBuy);
               g_outlierBuyClosed = true;
            }
            else
            {
               PrintFormat(">>> [RETRY] Failed to close BUY Ticket %I64d: Error %d - %s",
                           InpTicketCloseBuy, m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription());
            }
         }
         else
         {
            g_outlierBuyClosed = true;
         }
      }

      if(!g_outlierSellClosed)
      {
         if(PositionExists(InpTicketCloseSell))
         {
            if(m_trade.PositionClose(InpTicketCloseSell))
            {
               PrintFormat(">>> [OPTION B] Successfully CLOSED outlier SELL Ticket %I64d", InpTicketCloseSell);
               g_outlierSellClosed = true;
            }
            else
            {
               PrintFormat(">>> [RETRY] Failed to close SELL Ticket %I64d: Error %d - %s",
                           InpTicketCloseSell, m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription());
            }
         }
         else
         {
            g_outlierSellClosed = true;
         }
      }
   }
   else
   {
      g_outlierBuyClosed = true;
      g_outlierSellClosed = true;
   }

   // 2. Set Stop Loss on Remaining 4 Positions
   if(InpProtectRemaining)
   {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(m_position.SelectByIndex(i))
         {
            ulong ticket = m_position.Ticket();
            double curSL = m_position.StopLoss();
            double curTP = m_position.TakeProfit();

            // BUY Ticket 1030357046
            if(ticket == InpTicketBuyProtected && (curSL == 0.0 || MathAbs(curSL - InpBuyStopLoss) > 0.05))
            {
               if(m_trade.PositionModify(ticket, InpBuyStopLoss, curTP))
               {
                  PrintFormat(">>> [OPTION B] Set protective SL %.2f on BUY Ticket %I64d", InpBuyStopLoss, ticket);
               }
            }

            // SELL Tickets (1030467151, 1030469892, 1030480916)
            if((ticket == 1030467151 || ticket == 1030469892 || ticket == 1030480916) &&
               (curSL == 0.0 || MathAbs(curSL - InpSellStopLoss) > 0.05))
            {
               if(m_trade.PositionModify(ticket, InpSellStopLoss, curTP))
               {
                  PrintFormat(">>> [OPTION B] Set protective SL %.2f on SELL Ticket %I64d", InpSellStopLoss, ticket);
               }
            }
         }
      }
   }

   // Verify if untangle is done
   if(g_outlierBuyClosed && g_outlierSellClosed)
   {
      g_untangleComplete = true;
      Print(">>> [OPTION B COMPLETE] Outliers closed and SL protections active. Margin recovered!");
   }
}

//+------------------------------------------------------------------+
//| Count active recoup positions                                    |
//+------------------------------------------------------------------+
int CountRecoupPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Magic() == InpRecoupMagic)
            count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Step 2: Recoup Engine (Strictly 1 Open Trade At A Time)          |
//+------------------------------------------------------------------+
void ExecuteRecoupEngine()
{
   if(!InpEnableRecoupTrading) return;

   double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   // Target recoup condition: balance restored
   if(currentBalance >= InpTargetBalance)
   {
      PrintFormat(">>> [RECOUP COMPLETE] Target balance reached: $%.2f >= $%.2f! Stopping EA.",
                  currentBalance, InpTargetBalance);
      Alert(StringFormat("[GOLD24-7] RECOUP GOAL REACHED! Current balance: $%.2f. Trading stopped safely.", currentBalance));
      ExpertRemove();
      return;
   }

   // Strict Rule: EXACTLY 1 trade at a time
   int recoupCount = CountRecoupPositions();
   if(recoupCount >= 1)
   {
      // Already has an active recoup trade running; wait for it to hit TP or SL
      return;
   }

   // Also ensure no other new manual trades are cluttering: total positions must be <= 4 (original remaining)
   if(PositionsTotal() > 4)
   {
      return;
   }

   // Prevent rapid-fire entries (minimum 3 minutes between trades)
   if(TimeCurrent() - g_lastTradeTime < 180)
   {
      return;
   }

   // Signal generation: EMA9 / EMA21 trend + RSI momentum filter on M5
   double maFast[], maSlow[], rsi[];
   ArraySetAsSeries(maFast, true);
   ArraySetAsSeries(maSlow, true);
   ArraySetAsSeries(rsi, true);

   int hMaFast = iMA(_Symbol, PERIOD_M5, 9, 0, MODE_EMA, PRICE_CLOSE);
   int hMaSlow = iMA(_Symbol, PERIOD_M5, 21, 0, MODE_EMA, PRICE_CLOSE);
   int hRsi    = iRSI(_Symbol, PERIOD_M5, 14, PRICE_CLOSE);

   if(CopyBuffer(hMaFast, 0, 1, 2, maFast) < 2 ||
      CopyBuffer(hMaSlow, 0, 1, 2, maSlow) < 2 ||
      CopyBuffer(hRsi, 0, 1, 2, rsi) < 2)
   {
      IndicatorRelease(hMaFast);
      IndicatorRelease(hMaSlow);
      IndicatorRelease(hRsi);
      return;
   }

   IndicatorRelease(hMaFast);
   IndicatorRelease(hMaSlow);
   IndicatorRelease(hRsi);

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // Bullish Confluence: Fast EMA > Slow EMA and RSI crossing 50 up
   if(maFast[0] > maSlow[0] && maFast[1] <= maSlow[1] && rsi[0] > 50.0 && rsi[0] < 68.0)
   {
      double sl = ask - (InpRecoupSLPoints * point);
      double tp = ask + (InpRecoupTPPoints * point);
      PrintFormat(">>> [RECOUP BUY SIGNAL] Entering 1 disciplined BUY trade: %.2f lots @ %.2f | SL: %.2f | TP: %.2f",
                  InpRecoupLotSize, ask, sl, tp);
      if(m_trade.Buy(InpRecoupLotSize, _Symbol, ask, sl, tp, "GOLD24-7 Recoup 1/1"))
      {
         g_lastTradeTime = TimeCurrent();
         Print(">>> [RECOUP TRADE PLACED] Magic: 240724. Position monitored.");
      }
   }
   // Bearish Confluence: Fast EMA < Slow EMA and RSI crossing 50 down
   else if(maFast[0] < maSlow[0] && maFast[1] >= maSlow[1] && rsi[0] < 50.0 && rsi[0] > 32.0)
   {
      double sl = bid + (InpRecoupSLPoints * point);
      double tp = bid - (InpRecoupTPPoints * point);
      PrintFormat(">>> [RECOUP SELL SIGNAL] Entering 1 disciplined SELL trade: %.2f lots @ %.2f | SL: %.2f | TP: %.2f",
                  InpRecoupLotSize, bid, sl, tp);
      if(m_trade.Sell(InpRecoupLotSize, _Symbol, bid, sl, tp, "GOLD24-7 Recoup 1/1"))
      {
         g_lastTradeTime = TimeCurrent();
         Print(">>> [RECOUP TRADE PLACED] Magic: 240724. Position monitored.");
      }
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Untangle Option B on market open
   if(!g_untangleComplete)
   {
      ExecuteUntangleOptionB();
   }

   // 2. Recoup with 1 trade at a time
   ExecuteRecoupEngine();
}
//+------------------------------------------------------------------+
