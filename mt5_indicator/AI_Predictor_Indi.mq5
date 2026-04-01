//+------------------------------------------------------------------+
//|                                           AI_Predictor_Indi.mq5 |
//|                                                Antigravity Agent |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Antigravity Agent"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property description "Con Mắt AI Tensor - Vẽ Đồ Thị Xác Suất Lên - Xuống"
#property indicator_separate_window
#property indicator_buffers 1
#property indicator_plots   1

//--- Cài đặt Giao diện Đường Line Mềm Mại Xanh Mướt
#property indicator_label1  "Xác Suất Bò (AI Prob UP)"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrSpringGreen // Màu Xanh Neon Cyber
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2

// Biên độ Giới Hạn Cứng từ 0% đến 100%
#property indicator_minimum 0.0
#property indicator_maximum 1.0

#property indicator_level1  0.5
#property indicator_level2  0.7
#property indicator_level3  0.3
#property indicator_levelcolor clrDimGray
#property indicator_levelstyle STYLE_DOT

double         AISignalBuffer[];
bool           history_loaded = false;

int OnInit()
  {
   SetIndexBuffer(0, AISignalBuffer, INDICATOR_DATA);
   ArraySetAsSeries(AISignalBuffer, true); 
   IndicatorSetString(INDICATOR_SHORTNAME, "AI Python Brain");
   return(INIT_SUCCEEDED);
  }

void LoadHistoryFromFile()
{
   int handle = FileOpen("AI_Predictor_History.csv", FILE_READ|FILE_CSV|FILE_ANSI, '\n');
   if(handle != INVALID_HANDLE)
     {
      int count = 0;
      while(!FileIsEnding(handle))
        {
         string line = FileReadString(handle);
         string parts[];
         if(StringSplit(line, ',', parts) == 2)
           {
            datetime dt = (datetime)StringToInteger(parts[0]);
            double score = StringToDouble(parts[1]);
            
            // Ép vào Bộ Đệm (Buffer) dựa vào Trục Thời gian Trùng Nhau
            int shift = iBarShift(_Symbol, _Period, dt, false);
            if(shift >= 0 && shift < ArraySize(AISignalBuffer))
              {
               AISignalBuffer[shift] = score;
               count++;
              }
           }
        }
      FileClose(handle);
      Print("✅ [INDICATOR] Bốc lên Đồ Thị " + IntegerToString(count) + " Điểm Quá Khứ.");
      history_loaded = true;
     }
}

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
   // ArraySetAsSeries mặc định trong MQL5 là False (với Time/Open/High/Close).
   
   // 1. Chờ Bridge Tải Ký Ức Xong Mới Lật Đồ Thị
   if(!history_loaded)
     {
      if(GlobalVariableCheck("AI_History_Ready") && GlobalVariableGet("AI_History_Ready") == 1.0)
        {
         LoadHistoryFromFile();
        }
     }
     
   // 2. Chích Giá Trị Khắc Kỷ Lên Mũi Giáo Của Line (Xác Suất Mới Nhất)
   if(GlobalVariableCheck("AI_Live_Score"))
     {
      double current_score = GlobalVariableGet("AI_Live_Score");
      
      // Vẽ Cây Nến Đang Chạy (Shift = 0)
      if(ArraySize(AISignalBuffer) > 0)
        {
         AISignalBuffer[0] = current_score;
        }
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
