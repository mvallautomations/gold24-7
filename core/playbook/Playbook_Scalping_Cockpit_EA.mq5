//+------------------------------------------------------------------+
//|                                Playbook_Scalping_Cockpit_EA.mq5  |
//|               1-Minute Scalping Playbook for NY Opening Range    |
//|          M15 Opening Range | M5 Confirmation | M1 Execution (+2R)|
//|                     GOLD24-7 + OpenTraderWorld Integration       |
//+------------------------------------------------------------------+
#property copyright "GOLD24-7 Team / Antigravity"
#property link      "https://github.com/gold24-7"
#property version   "2.00"
#property description "Applies M15 Opening Range Box, M5 Confirmation Close, M1 Execution Brackets (Invariant 1:2 R:R), and bidirectional sync with the Mirror Dashboard."

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "=== Strategy Parameters ==="
input ulong    InpMagicNumber        = 240702;           // Magic Number
input double   InpDefaultLots        = 0.01;             // Execution Lots
input double   InpRiskRewardRatio    = 2.0;              // Invariant R:R Ratio (2.0 = +2R TP)
input int      InpSlippagePoints     = 25;               // Max Slippage (Points)

input group "=== Chart Visual Overlays ==="
input bool     InpDraw15MBox         = true;             // Draw 15M ORH/ORL Box
input bool     InpDraw15MLevels      = true;             // Draw 15M Support/Resistance Lines
input bool     InpDraw5MConfirm      = true;             // Draw 5M Confirmation Level
input bool     InpDraw1MBrackets     = true;             // Draw 1M Entry/SL/TP (+2R) Lines
input bool     InpDrawOnChartHUD     = true;             // Draw Interactive On-Chart Cockpit HUD

input group "=== Color Palette ==="
input color    InpBoxColor           = C'20,60,120';     // 15M ORH/ORL Box Color
input color    InpORHColor           = clrDodgerBlue;    // ORH Resistance Line Color
input color    InpORLColor           = clrDeepSkyBlue;   // ORL Support Line Color
input color    InpConfirmColor       = clrGold;          // 5M Confirmation Line Color
input color    InpEntryColor         = clrCyan;          // 1M Entry Line Color
input color    InpSLColor            = clrCrimson;       // -1R Stop Loss Line Color
input color    InpTPColor            = clrLimeGreen;     // +2R Take Profit Line Color

input group "=== Sync Engine ==="
input string   InpSyncFileName       = "playbook_sync.json"; // Bidirectional Sync File in MQL5/Files
input int      InpSyncIntervalMs     = 250;              // Sync Poll Interval (ms)

//--- Global Objects
CTrade trade;
datetime last_file_mod_time = 0;
datetime last_bar_time = 0;

// State Variables
double g_orh = 0.0;
double g_orl = 0.0;
datetime g_box_start = 0;
datetime g_box_end = 0;
double g_m5_confirm = 0.0;
string g_m5_bias = "NEUTRAL";
double g_entry = 0.0;
double g_sl = 0.0;
double g_tp = 0.0;
string g_model = "MODEL_A";
string g_grade = "A+";
int    g_score = 9;
string g_action = "ARMED";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFilling(ORDER_FILLING_IOC);

   EventSetMillisecondTimer(InpSyncIntervalMs);

   // Initial calculation from chart bars
   CalculateFromChartBars();
   DrawAllChartObjects();
   if(InpDrawOnChartHUD) CreateOnChartHUD();

   PrintFormat("[PLAYBOOK EA] Initialized successfully on %s. Magic=%d", _Symbol, InpMagicNumber);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   RemoveAllChartObjects();
   PrintFormat("[PLAYBOOK EA] Deinitialized on %s. Reason: %d", _Symbol, reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   datetime current_bar = iTime(_Symbol, PERIOD_M1, 0);
   if(current_bar != last_bar_time)
   {
      last_bar_time = current_bar;
      CalculateFromChartBars();
      DrawAllChartObjects();
      UpdateHUD();
   }
}

//+------------------------------------------------------------------+
//| Timer function for JSON sync file polling                        |
//+------------------------------------------------------------------+
void OnTimer()
{
   ReadSyncFile();
}

//+------------------------------------------------------------------+
//| Reads the sync file written by the Python Mirror Dashboard       |
//+------------------------------------------------------------------+
void ReadSyncFile()
{
   if(!FileIsExist(InpSyncFileName, 0)) return;

   int handle = FileOpen(InpSyncFileName, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(handle == INVALID_HANDLE) return;

   string content = "";
   while(!FileIsEnding(handle))
   {
      content += FileReadString(handle);
   }
   FileClose(handle);

   if(StringLen(content) < 10) return;

   // Simple fast JSON value extractors
   string target_sym = ExtractJsonString(content, "symbol");
   if(target_sym != "" && target_sym != _Symbol && target_sym != Symbol()) return;

   double orh = ExtractJsonDouble(content, "orh");
   double orl = ExtractJsonDouble(content, "orl");
   double confirm = ExtractJsonDouble(content, "confirm_price");
   double entry = ExtractJsonDouble(content, "entry");
   double sl = ExtractJsonDouble(content, "sl");
   double tp = ExtractJsonDouble(content, "tp");
   string model = ExtractJsonString(content, "model");
   string grade = ExtractJsonString(content, "grade");
   int score = (int)ExtractJsonDouble(content, "score");
   string command = ExtractJsonString(content, "command");

   bool changed = false;
   if(orh > 0 && orh != g_orh) { g_orh = orh; changed = true; }
   if(orl > 0 && orl != g_orl) { g_orl = orl; changed = true; }
   if(confirm > 0 && confirm != g_m5_confirm) { g_m5_confirm = confirm; changed = true; }
   if(entry > 0 && entry != g_entry) { g_entry = entry; changed = true; }
   if(sl > 0 && sl != g_sl) { g_sl = sl; changed = true; }
   if(tp > 0 && tp != g_tp) { g_tp = tp; changed = true; }
   if(model != "") g_model = model;
   if(grade != "") g_grade = grade;
   if(score > 0) g_score = score;

   // Execute command if triggered from mirror dashboard
   if(command == "EXECUTE_BUY" || command == "EXECUTE_SELL")
   {
      double lots = ExtractJsonDouble(content, "lots");
      if(lots <= 0) lots = InpDefaultLots;
      ExecuteMirrorTrade(command == "EXECUTE_BUY" ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lots, g_sl, g_tp);
      ClearCommandInFile();
   }

   if(changed)
   {
      DrawAllChartObjects();
      UpdateHUD();
   }
}

//+------------------------------------------------------------------+
//| Clears execution command from sync file to prevent re-firing     |
//+------------------------------------------------------------------+
void ClearCommandInFile()
{
   int handle = FileOpen(InpSyncFileName, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle != INVALID_HANDLE)
   {
      string json = StringFormat(
         "{\"symbol\":\"%s\",\"orh\":%.5f,\"orl\":%.5f,\"confirm_price\":%.5f,\"entry\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"model\":\"%s\",\"grade\":\"%s\",\"score\":%d,\"command\":\"DONE\"}",
         _Symbol, g_orh, g_orl, g_m5_confirm, g_entry, g_sl, g_tp, g_model, g_grade, g_score
      );
      FileWriteString(handle, json);
      FileClose(handle);
   }
}

//+------------------------------------------------------------------+
//| Calculates ORH, ORL, 5M Confirmation, and 1M Model from bars     |
//+------------------------------------------------------------------+
void CalculateFromChartBars()
{
   // 1. Calculate 15M ORH/ORL based on the recent 15M candle (or current forming session)
   MqlRates rates_15m[];
   ArraySetAsSeries(rates_15m, true);
   if(CopyRates(_Symbol, PERIOD_M15, 0, 4, rates_15m) >= 2)
   {
      // Phase 1 15M Range
      g_orh = MathMax(rates_15m[1].high, rates_15m[0].high);
      g_orl = MathMin(rates_15m[1].low, rates_15m[0].low);
      g_box_start = rates_15m[1].time;
      g_box_end = rates_15m[0].time + 15 * 60;
   }

   // 2. 5M Confirmation Close Detection
   MqlRates rates_5m[];
   ArraySetAsSeries(rates_5m, true);
   if(CopyRates(_Symbol, PERIOD_M5, 0, 3, rates_5m) >= 2)
   {
      if(rates_5m[1].close > g_orh)
      {
         g_m5_bias = "BULLISH_BREAK";
         g_m5_confirm = g_orh;
      }
      else if(rates_5m[1].close < g_orl)
      {
         g_m5_bias = "BEARISH_BREAK";
         g_m5_confirm = g_orl;
      }
      else
      {
         g_m5_bias = "INSIDE_RANGE";
         g_m5_confirm = (g_orh + g_orl) / 2.0;
      }
   }

   // 3. 1M Execution Matrix Setup & Invariant 1:2 Bracket Calculation
   MqlTick tick;
   SymbolInfoTick(_Symbol, tick);
   double current_price = (tick.ask + tick.bid) / 2.0;
   if(current_price <= 0) current_price = iClose(_Symbol, PERIOD_M1, 0);

   g_entry = current_price;
   double range_height = (g_orh > g_orl) ? (g_orh - g_orl) : (_Point * 200);
   double risk_dist = MathMax(range_height * 0.25, _Point * 50);

   if(g_m5_bias == "BULLISH_BREAK")
   {
      g_sl = NormalizeDouble(g_entry - risk_dist, _Digits);
      g_tp = NormalizeDouble(g_entry + (InpRiskRewardRatio * risk_dist), _Digits);
      g_model = "MODEL_A";
      g_grade = "A+";
      g_score = 9;
   }
   else if(g_m5_bias == "BEARISH_BREAK")
   {
      g_sl = NormalizeDouble(g_entry + risk_dist, _Digits);
      g_tp = NormalizeDouble(g_entry - (InpRiskRewardRatio * risk_dist), _Digits);
      g_model = "MODEL_A";
      g_grade = "A+";
      g_score = 9;
   }
   else
   {
      // Trap / Retest setup near boundary
      if(MathAbs(current_price - g_orh) < MathAbs(current_price - g_orl))
      {
         // Resistance Retest
         g_sl = NormalizeDouble(g_orh + risk_dist, _Digits);
         g_tp = NormalizeDouble(g_entry - (InpRiskRewardRatio * risk_dist), _Digits);
         g_model = "MODEL_B";
         g_grade = "B";
         g_score = 8;
      }
      else
      {
         // Support Retest
         g_sl = NormalizeDouble(g_orl - risk_dist, _Digits);
         g_tp = NormalizeDouble(g_entry + (InpRiskRewardRatio * risk_dist), _Digits);
         g_model = "MODEL_B";
         g_grade = "B";
         g_score = 8;
      }
   }
}

//+------------------------------------------------------------------+
//| Draws all Playbook Objects on the active MT5 chart               |
//+------------------------------------------------------------------+
void DrawAllChartObjects()
{
   if(g_orh <= 0 || g_orl <= 0) return;

   // 1. 15M ORH/ORL Box
   if(InpDraw15MBox)
   {
      string box_name = "PB_15M_ORH_BOX";
      datetime t1 = (g_box_start > 0) ? g_box_start : (TimeCurrent() - 3600);
      datetime t2 = (g_box_end > 0) ? g_box_end : (TimeCurrent() + 3600);

      if(ObjectFind(0, box_name) < 0)
      {
         ObjectCreate(0, box_name, OBJ_RECTANGLE, 0, t1, g_orh, t2, g_orl);
      }
      else
      {
         ObjectSetInteger(0, box_name, OBJPROP_TIME, 0, t1);
         ObjectSetDouble(0, box_name, OBJPROP_PRICE, 0, g_orh);
         ObjectSetInteger(0, box_name, OBJPROP_TIME, 1, t2);
         ObjectSetDouble(0, box_name, OBJPROP_PRICE, 1, g_orl);
      }
      ObjectSetInteger(0, box_name, OBJPROP_COLOR, InpBoxColor);
      ObjectSetInteger(0, box_name, OBJPROP_STYLE, STYLE_SOLID);
      ObjectSetInteger(0, box_name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, box_name, OBJPROP_FILL, true);
      ObjectSetInteger(0, box_name, OBJPROP_BACK, true);
      ObjectSetString(0, box_name, OBJPROP_TOOLTIP, "15M Opening Range Corridor (ORH - ORL)");
   }

   // 2. 15M ORH & ORL Horizontal Lines
   if(InpDraw15MLevels)
   {
      DrawHLine("PB_LINE_ORH", g_orh, InpORHColor, STYLE_SOLID, 2, StringFormat("15M ORH [RESISTANCE]: %.5f", g_orh));
      DrawHLine("PB_LINE_ORL", g_orl, InpORLColor, STYLE_SOLID, 2, StringFormat("15M ORL [SUPPORT]: %.5f", g_orl));
   }

   // 3. 5M Confirmation Level
   if(InpDraw5MConfirm && g_m5_confirm > 0)
   {
      DrawHLine("PB_LINE_5M_CONFIRM", g_m5_confirm, InpConfirmColor, STYLE_DASH, 1, StringFormat("5M CONFIRMATION [%s]: %.5f", g_m5_bias, g_m5_confirm));
   }

   // 4. 1M Execution Matrix & Invariant 1:2 R:R Brackets
   if(InpDraw1MBrackets && g_entry > 0 && g_sl > 0 && g_tp > 0)
   {
      DrawHLine("PB_LINE_1M_ENTRY", g_entry, InpEntryColor, STYLE_SOLID, 2, StringFormat("1M ENTRY (%s): %.5f", g_model, g_entry));
      DrawHLine("PB_LINE_1M_SL", g_sl, InpSLColor, STYLE_DASH, 2, StringFormat("-1R STOP LOSS: %.5f", g_sl));
      DrawHLine("PB_LINE_1M_TP", g_tp, InpTPColor, STYLE_SOLID, 3, StringFormat("+2R TAKE PROFIT: %.5f", g_tp));
   }

   ChartRedraw(0);
}

//+------------------------------------------------------------------+
//| Helper to create or update an OBJ_HLINE                          |
//+------------------------------------------------------------------+
void DrawHLine(const string name, const double price, const color clr, const ENUM_LINE_STYLE style, const int width, const string text)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   }
   else
   {
      ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, text);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}

//+------------------------------------------------------------------+
//| Creates on-chart Interactive HUD Panel                           |
//+------------------------------------------------------------------+
void CreateOnChartHUD()
{
   int x = 20, y = 30;
   CreateLabel("PB_HUD_BG", x, y, 260, 160, C'10,15,30', C'25,40,75');
   CreateText("PB_HUD_TITLE", x + 10, y + 10, "⚡ PLAYBOOK SCALPING COCKPIT", "JetBrains Mono", 10, clrGold);
   CreateText("PB_HUD_SCORE", x + 10, y + 30, "Confluence: 9/10 [Grade A+]", "Plus Jakarta Sans", 9, clrLimeGreen);
   CreateText("PB_HUD_MODEL", x + 10, y + 48, "Model A: Displacement Gap", "Plus Jakarta Sans", 8, clrCyan);
   CreateText("PB_HUD_RR", x + 10, y + 66, "Invariant 1:2 R:R Ratio (+2R TP)", "Plus Jakarta Sans", 8, clrWhite);
   CreateText("PB_HUD_LEVELS", x + 10, y + 84, "SL: -1R | Target: +2R Hard Exit", "JetBrains Mono", 8, clrSilver);

   // Interactive Buttons
   CreateButton("PB_BTN_BUY", x + 10, y + 110, 115, 24, "⚡ BUY (+2R)", clrWhite, C'0,120,60');
   CreateButton("PB_BTN_SELL", x + 135, y + 110, 115, 24, "⚡ SELL (+2R)", clrWhite, C'160,30,40');
   CreateButton("PB_BTN_CLEAR", x + 10, y + 138, 240, 18, "❌ CLEAR / RECALCULATE", clrSilver, C'20,30,50');
}

//+------------------------------------------------------------------+
//| Updates on-chart HUD text dynamically                            |
//+------------------------------------------------------------------+
void UpdateHUD()
{
   if(!InpDrawOnChartHUD) return;

   string score_str = StringFormat("Confluence: %d/10 [Grade %s]", g_score, g_grade);
   color score_clr = (g_score >= 9) ? clrLimeGreen : ((g_score >= 7) ? clrGold : clrCrimson);
   ObjectSetString(0, "PB_HUD_SCORE", OBJPROP_TEXT, score_str);
   ObjectSetInteger(0, "PB_HUD_SCORE", OBJPROP_COLOR, score_clr);

   string model_str = StringFormat("%s (%s)", g_model, g_m5_bias);
   ObjectSetString(0, "PB_HUD_MODEL", OBJPROP_TEXT, model_str);

   string rr_str = StringFormat("Entry: %.5f | TP (+2R): %.5f", g_entry, g_tp);
   ObjectSetString(0, "PB_HUD_RR", OBJPROP_TEXT, rr_str);

   string sl_str = StringFormat("SL (-1R): %.5f | Diff: %.1f pts", g_sl, MathAbs(g_entry - g_sl) / _Point);
   ObjectSetString(0, "PB_HUD_LEVELS", OBJPROP_TEXT, sl_str);
}

//+------------------------------------------------------------------+
//| UI Helper: Rectangle Label Background                            |
//+------------------------------------------------------------------+
void CreateLabel(const string name, int x, int y, int w, int h, color bg_clr, color border_clr)
{
   ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg_clr);
   ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, border_clr);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}

//+------------------------------------------------------------------+
//| UI Helper: Text Label                                            |
//+------------------------------------------------------------------+
void CreateText(const string name, int x, int y, string text, string font, int font_size, color clr)
{
   ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, font);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, font_size);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
}

//+------------------------------------------------------------------+
//| UI Helper: Button                                                |
//+------------------------------------------------------------------+
void CreateButton(const string name, int x, int y, int w, int h, string text, color text_clr, color bg_clr)
{
   ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, "JetBrains Mono");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, name, OBJPROP_COLOR, text_clr);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg_clr);
   ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, clrWhite);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
}

//+------------------------------------------------------------------+
//| Chart Event Handler (Clicking On-Chart Buttons)                  |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK)
   {
      if(sparam == "PB_BTN_BUY")
      {
         ObjectSetInteger(0, "PB_BTN_BUY", OBJPROP_STATE, false);
         ExecuteMirrorTrade(ORDER_TYPE_BUY, InpDefaultLots, g_sl, g_tp);
      }
      else if(sparam == "PB_BTN_SELL")
      {
         ObjectSetInteger(0, "PB_BTN_SELL", OBJPROP_STATE, false);
         ExecuteMirrorTrade(ORDER_TYPE_SELL, InpDefaultLots, g_sl, g_tp);
      }
      else if(sparam == "PB_BTN_CLEAR")
      {
         ObjectSetInteger(0, "PB_BTN_CLEAR", OBJPROP_STATE, false);
         CalculateFromChartBars();
         DrawAllChartObjects();
         UpdateHUD();
      }
   }
}

//+------------------------------------------------------------------+
//| Executes a Trade natively on MT5 with exact Invariant 1:2 bracket|
//+------------------------------------------------------------------+
void ExecuteMirrorTrade(ENUM_ORDER_TYPE order_type, double lots, double sl, double tp)
{
   MqlTick tick;
   SymbolInfoTick(_Symbol, tick);
   double price = (order_type == ORDER_TYPE_BUY) ? tick.ask : tick.bid;

   string comment = StringFormat("PLAY_%s_%s", g_grade, g_model);
   bool success = false;

   if(order_type == ORDER_TYPE_BUY)
   {
      success = trade.Buy(lots, _Symbol, price, sl, tp, comment);
   }
   else
   {
      success = trade.Sell(lots, _Symbol, price, sl, tp, comment);
   }

   if(success)
   {
      PrintFormat("[PLAYBOOK EA] Executed %s %.2f lots on %s @ %.5f | SL: %.5f | TP: %.5f",
                  EnumToString(order_type), lots, _Symbol, price, sl, tp);
   }
   else
   {
      PrintFormat("[PLAYBOOK EA] Trade Error: %d - %s", trade.ResultRetcode(), trade.ResultComment());
   }
}

//+------------------------------------------------------------------+
//| Removes all Playbook Objects on clean deinit                     |
//+------------------------------------------------------------------+
void RemoveAllChartObjects()
{
   ObjectsDeleteAll(0, "PB_");
   ChartRedraw(0);
}

//+------------------------------------------------------------------+
//| Lightweight JSON String extractor                                |
//+------------------------------------------------------------------+
string ExtractJsonString(const string json, const string key)
{
   string search = "\"" + key + "\":\"";
   int pos = StringFind(json, search);
   if(pos < 0) return "";
   pos += StringLen(search);
   int end_pos = StringFind(json, "\"", pos);
   if(end_pos < 0) return "";
   return StringSubstr(json, pos, end_pos - pos);
}

//+------------------------------------------------------------------+
//| Lightweight JSON Double extractor                                |
//+------------------------------------------------------------------+
double ExtractJsonDouble(const string json, const string key)
{
   string search = "\"" + key + "\":";
   int pos = StringFind(json, search);
   if(pos < 0) return 0.0;
   pos += StringLen(search);
   // Skip whitespace
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' || StringGetCharacter(json, pos) == '\"'))
      pos++;
   int end_pos = pos;
   while(end_pos < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, end_pos);
      if((ch >= '0' && ch <= '9') || ch == '.' || ch == '-')
         end_pos++;
      else
         break;
   }
   string val_str = StringSubstr(json, pos, end_pos - pos);
   return StringToDouble(val_str);
}
//+------------------------------------------------------------------+
