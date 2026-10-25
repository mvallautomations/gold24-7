//+------------------------------------------------------------------+
//|                         Playbook_15M_OpeningRange_Indicator.mq5   |
//|               1-Minute Scalping Playbook: 15M Opening Objects    |
//|          M15 Opening Range | M5 Confirmation | M1 Execution (+2R)|
//|                     GOLD24-7 + OpenTraderWorld Integration       |
//+------------------------------------------------------------------+
#property copyright   "GOLD24-7 Team / Antigravity"
#property link        "https://github.com/gold24-7"
#property version     "1.00"
#property description "Object indicators for the 15M Opening Entry Timeframe: 15M ORH/ORL Box, Equilibrium 50%, Expansion Targets (+1R/+2R), and Price Tags."
#property indicator_chart_window
#property indicator_plots 0

//--- Input Parameters
input group "=== Session Timing ==="
input bool     InpAutoDetect15MBar   = true;             // Auto-detect completed 15M Candle (Shift 1)
input int      InpOpenHourEST        = 9;                // NY Open Hour EST (e.g. 9 for 09:30)
input int      InpOpenMinuteEST      = 30;               // NY Open Minute EST (30)
input double   InpExecutionWindowHrs = 2.0;              // Execution Window Duration (Hours)

input group "=== 15M Visual Object Indicators ==="
input bool     InpDraw15MBox         = true;             // Draw 15M ORH/ORL Shaded Box (OBJ_RECTANGLE)
input bool     InpDrawORHLines       = true;             // Draw 15M ORH & ORL Boundary Lines
input bool     InpDrawEquilibrium    = true;             // Draw 50% Equilibrium Median Line
input bool     InpDrawExpansionProjections = true;       // Draw +1R / +2R Institutional Targets
input bool     InpDrawPriceLabels    = true;             // Draw Text Price Tags on Lines
input bool     InpDrawHUDCard        = true;             // Draw On-Chart HUD Badge

input group "=== Color Palette ==="
input color    InpBoxFillColor       = C'15,35,75';      // Box Shading Color
input color    InpORHColor           = clrDodgerBlue;    // 15M ORH (Liquidity High)
input color    InpORLColor           = clrDeepSkyBlue;   // 15M ORL (Liquidity Low)
input color    InpEQColor            = clrGold;          // 50% Equilibrium Line
input color    InpTargetBullColor    = clrLimeGreen;     // +2R Bullish Target
input color    InpTargetBearColor    = clrCrimson;       // -2R Bearish Target
input color    InpTextColor          = clrWhite;         // Text Labels Color

//--- Object Name Prefix
#define OBJ_PREFIX "PB_M15_"

//--- Global State
datetime g_box_start = 0;
datetime g_box_end = 0;
double   g_orh = 0.0;
double   g_orl = 0.0;
double   g_eq = 0.0;
double   g_exp_p1r = 0.0;
double   g_exp_p2r = 0.0;
double   g_exp_m1r = 0.0;
double   g_exp_m2r = 0.0;
double   g_range = 0.0;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   Calculate15MOpeningRange();
   RenderAllObjects();
   PrintFormat("[PLAYBOOK M15 INDICATOR] Initialized on %s (%s). ORH=%.2f, ORL=%.2f, Range=%.2f",
               _Symbol, EnumToString(Period()), g_orh, g_orl, g_range);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   RemoveAllObjects();
   PrintFormat("[PLAYBOOK M15 INDICATOR] Deinitialized on %s. Objects cleaned up.", _Symbol);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   if(rates_total < 5) return(0);

   static datetime last_calc_time = 0;
   datetime current_m15 = iTime(_Symbol, PERIOD_M15, 0);

   if(current_m15 != last_calc_time)
   {
      last_calc_time = current_m15;
      Calculate15MOpeningRange();
      RenderAllObjects();
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Calculate 15M Opening Range geometry and expansion levels        |
//+------------------------------------------------------------------+
void Calculate15MOpeningRange()
{
   // Query completed 15M candle (Shift 1) as the reference boundary
   // This guarantees that 5M and 1M bars can cleanly diagnose true breakouts outside the range
   int shift = 1;
   datetime bar_time = iTime(_Symbol, PERIOD_M15, shift);
   double bar_high   = iHigh(_Symbol, PERIOD_M15, shift);
   double bar_low    = iLow(_Symbol, PERIOD_M15, shift);

   if(bar_high <= 0 || bar_low <= 0)
   {
      // Fallback to shift 0 if shift 1 not ready
      shift = 0;
      bar_time = iTime(_Symbol, PERIOD_M15, shift);
      bar_high = iHigh(_Symbol, PERIOD_M15, shift);
      bar_low  = iLow(_Symbol, PERIOD_M15, shift);
   }

   g_orh = NormalizeDouble(bar_high, _Digits);
   g_orl = NormalizeDouble(bar_low, _Digits);
   g_range = NormalizeDouble(g_orh - g_orl, _Digits);
   g_eq = NormalizeDouble((g_orh + g_orl) / 2.0, _Digits);

   // Multi-target Institutional Expansion levels (+1R, +2R, -1R, -2R)
   g_exp_p1r = NormalizeDouble(g_orh + g_range, _Digits);
   g_exp_p2r = NormalizeDouble(g_orh + (2.0 * g_range), _Digits);
   g_exp_m1r = NormalizeDouble(g_orl - g_range, _Digits);
   g_exp_m2r = NormalizeDouble(g_orl - (2.0 * g_range), _Digits);

   // Time bounds
   g_box_start = bar_time;
   // Project across 2-hour execution window (8 x 15M candles = 7200 seconds)
   g_box_end = bar_time + (int)(InpExecutionWindowHrs * 3600);
}

//+------------------------------------------------------------------+
//| Renders all object indicators onto the chart window              |
//+------------------------------------------------------------------+
void RenderAllObjects()
{
   if(g_orh <= 0 || g_orl <= 0) return;

   // 1. 15M ORH/ORL Box (OBJ_RECTANGLE)
   if(InpDraw15MBox)
   {
      string name = OBJ_PREFIX + "BOX";
      if(ObjectFind(0, name) < 0)
      {
         ObjectCreate(0, name, OBJ_RECTANGLE, 0, g_box_start, g_orh, g_box_end, g_orl);
      }
      else
      {
         ObjectSetInteger(0, name, OBJPROP_TIME, 0, g_box_start);
         ObjectSetDouble(0, name, OBJPROP_PRICE, 0, g_orh);
         ObjectSetInteger(0, name, OBJPROP_TIME, 1, g_box_end);
         ObjectSetDouble(0, name, OBJPROP_PRICE, 1, g_orl);
      }
      ObjectSetInteger(0, name, OBJPROP_COLOR, InpBoxFillColor);
      ObjectSetInteger(0, name, OBJPROP_FILL, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, StringFormat("15M Opening Range Corridor: %.2f - %.2f (%.2f pts)", g_orl, g_orh, g_range));
   }

   // 2. 15M Upper Boundary: ORH (Resistance / Liquidity High)
   if(InpDrawORHLines)
   {
      DrawTrendRay(OBJ_PREFIX + "ORH_LINE", g_box_start, g_orh, g_box_end, g_orh, InpORHColor, STYLE_SOLID, 2, "15M ORH [Liquidity High]");
      DrawTrendRay(OBJ_PREFIX + "ORL_LINE", g_box_start, g_orl, g_box_end, g_orl, InpORLColor, STYLE_SOLID, 2, "15M ORL [Liquidity Low]");
   }

   // 3. 50% Equilibrium Median Line
   if(InpDrawEquilibrium)
   {
      DrawTrendRay(OBJ_PREFIX + "EQ_LINE", g_box_start, g_eq, g_box_end, g_eq, InpEQColor, STYLE_DASH, 1, "50% Equilibrium (Median)");
   }

   // 4. Institutional Expansion Targets (+1R / +2R and -1R / -2R)
   if(InpDrawExpansionProjections)
   {
      DrawTrendRay(OBJ_PREFIX + "EXP_P1R", g_box_start, g_exp_p1r, g_box_end, g_exp_p1r, InpTargetBullColor, STYLE_DOT, 1, "+1R Expansion");
      DrawTrendRay(OBJ_PREFIX + "EXP_P2R", g_box_start, g_exp_p2r, g_box_end, g_exp_p2r, InpTargetBullColor, STYLE_SOLID, 2, "+2R Target (+2R TP)");
      DrawTrendRay(OBJ_PREFIX + "EXP_M1R", g_box_start, g_exp_m1r, g_box_end, g_exp_m1r, InpTargetBearColor, STYLE_DOT, 1, "-1R Expansion");
      DrawTrendRay(OBJ_PREFIX + "EXP_M2R", g_box_start, g_exp_m2r, g_box_end, g_exp_m2r, InpTargetBearColor, STYLE_SOLID, 2, "-2R Target (+2R Short TP)");
   }

   // 5. On-Chart Floating Labels on Boundary Lines
   if(InpDrawPriceLabels)
   {
      DrawTextLabel(OBJ_PREFIX + "TXT_ORH", g_box_end, g_orh, StringFormat("  15M ORH: %.2f  ", g_orh), InpORHColor);
      DrawTextLabel(OBJ_PREFIX + "TXT_ORL", g_box_end, g_orl, StringFormat("  15M ORL: %.2f  ", g_orl), InpORLColor);
      DrawTextLabel(OBJ_PREFIX + "TXT_EQ",  g_box_end, g_eq,  StringFormat("  50%% EQ: %.2f  ", g_eq),  InpEQColor);
      if(InpDrawExpansionProjections)
      {
         DrawTextLabel(OBJ_PREFIX + "TXT_P2R", g_box_end, g_exp_p2r, StringFormat("  +2R TARGET: %.2f  ", g_exp_p2r), InpTargetBullColor);
         DrawTextLabel(OBJ_PREFIX + "TXT_M2R", g_box_end, g_exp_m2r, StringFormat("  -2R TARGET: %.2f  ", g_exp_m2r), InpTargetBearColor);
      }
   }

   // 6. Interactive On-Chart Status Badge
   if(InpDrawHUDCard)
   {
      DrawHUDCard();
   }

   ChartRedraw(0);
}

//+------------------------------------------------------------------+
//| Helper to draw a trend ray line object                           |
//+------------------------------------------------------------------+
void DrawTrendRay(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
                  const color clr, const ENUM_LINE_STYLE style, const int width, const string tooltip)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
   }
   else
   {
      ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
      ObjectSetDouble(0, name, OBJPROP_PRICE, 0, p1);
      ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
      ObjectSetDouble(0, name, OBJPROP_PRICE, 1, p2);
   }
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tooltip);
}

//+------------------------------------------------------------------+
//| Helper to draw an on-chart price text callout                    |
//+------------------------------------------------------------------+
void DrawTextLabel(const string name, const datetime t, const double p, const string text, const color clr)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   }
   else
   {
      ObjectSetInteger(0, name, OBJPROP_TIME, t);
      ObjectSetDouble(0, name, OBJPROP_PRICE, p);
   }
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetString(0, name, OBJPROP_FONT, "Lucida Console");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}

//+------------------------------------------------------------------+
//| Draws the sleek on-chart HUD summary card                        |
//+------------------------------------------------------------------+
void DrawHUDCard()
{
   string bg_name = OBJ_PREFIX + "HUD_BG";
   if(ObjectFind(0, bg_name) < 0)
   {
      ObjectCreate(0, bg_name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   }
   ObjectSetInteger(0, bg_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg_name, OBJPROP_XDISTANCE, 15);
   ObjectSetInteger(0, bg_name, OBJPROP_YDISTANCE, 25);
   ObjectSetInteger(0, bg_name, OBJPROP_XSIZE, 310);
   ObjectSetInteger(0, bg_name, OBJPROP_YSIZE, 95);
   ObjectSetInteger(0, bg_name, OBJPROP_BGCOLOR, C'10,18,32');
   ObjectSetInteger(0, bg_name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bg_name, OBJPROP_COLOR, C'30,70,140');
   ObjectSetInteger(0, bg_name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, bg_name, OBJPROP_BACK, false);

   // Title Label
   CreateScreenLabel(OBJ_PREFIX + "HUD_T1", 25, 33, "15M OPENING ENTRY TIMEFRAME", clrDodgerBlue, "Arial Bold", 10);

   // Range metrics
   string m_str = StringFormat("15M ORH: %.2f | ORL: %.2f", g_orh, g_orl);
   CreateScreenLabel(OBJ_PREFIX + "HUD_T2", 25, 52, m_str, clrWhite, "Lucida Console", 9);

   string r_str = StringFormat("Spread Range: %.2f pts | 50%% EQ: %.2f", g_range, g_eq);
   CreateScreenLabel(OBJ_PREFIX + "HUD_T3", 25, 70, r_str, clrGold, "Lucida Console", 9);

   // Current bias
   double current_bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   string bias_str = "Status: INSIDE 15M RANGE";
   color bias_clr = clrCyan;
   if(current_bid > g_orh)
   {
      bias_str = StringFormat("Status: BULLISH BREAKOUT (+%.2f pts)", current_bid - g_orh);
      bias_clr = clrLimeGreen;
   }
   else if(current_bid < g_orl)
   {
      bias_str = StringFormat("Status: BEARISH BREAKOUT (-%.2f pts)", g_orl - current_bid);
      bias_clr = clrCrimson;
   }
   CreateScreenLabel(OBJ_PREFIX + "HUD_T4", 25, 88, bias_str, bias_clr, "Lucida Console", 9);
}

//+------------------------------------------------------------------+
//| Screen label helper                                              |
//+------------------------------------------------------------------+
void CreateScreenLabel(const string name, const int x, const int y, const string text, const color clr, const string font, const int size)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   }
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, font);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}

//+------------------------------------------------------------------+
//| Deletes all chart objects created by this indicator              |
//+------------------------------------------------------------------+
void RemoveAllObjects()
{
   for(int i = ObjectsTotal(0, 0, -1) - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i, 0, -1);
      if(StringFind(name, OBJ_PREFIX) == 0)
      {
         ObjectDelete(0, name);
      }
   }
   ChartRedraw(0);
}
//+------------------------------------------------------------------+
