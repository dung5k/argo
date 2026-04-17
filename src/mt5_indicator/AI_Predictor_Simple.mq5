//+------------------------------------------------------------------+
//|                                       AI_Predictor_Simple.mq5 |
//|                                                Antigravity Agent |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Antigravity Agent"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property description "Chỉ Báo AI Đọc Trọn Gói File CSV (Không qua API)"
#property indicator_separate_window
#property indicator_buffers 1
#property indicator_plots   1

// Định dạng Đồ thị
#property indicator_label1  "Xác Suất Bò (AI Prob UP)"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrSpringGreen
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2

#property indicator_minimum 0.0
#property indicator_maximum 1.0

#property indicator_level1  0.5
#property indicator_levelcolor clrDimGray
#property indicator_levelstyle STYLE_DOT

double         AISignalBuffer[];

int OnInit()
  {
   SetIndexBuffer(0, AISignalBuffer, INDICATOR_DATA);
   ArraySetAsSeries(AISignalBuffer, true); 
   IndicatorSetString(INDICATOR_SHORTNAME, "AI Python Brain (File Reader)");
   EventSetTimer(60); // Đọc lại file mỗi phút 1 lần
   LoadHistoryFromFile();
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

void OnTimer()
  {
   LoadHistoryFromFile();
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
   // Tự thân OnCalculate không làm gì vì Graphic đã chốt bởi OnTimer.
   // Ta chỉ cần trả về rates_total để Indicator hoạt động.
   return(rates_total);
  }

void LoadHistoryFromFile()
{
   // Mở file từ thư mục Terminal/Common/Files để Python dễ dàng ghi vào mà không bị kẹt Sandbox MQL5
   int handle = FileOpen("ai_predictions.csv", FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, '\n');
   if(handle != INVALID_HANDLE)
     {
      int count = 0;
      
      // Reset mảng vẽ để không bị nhiễu do nến M1 sinh thêm
      ArrayInitialize(AISignalBuffer, EMPTY_VALUE);
      
      while(!FileIsEnding(handle))
        {
         string line = FileReadString(handle);
         string parts[];
         if(StringSplit(line, ',', parts) == 2)
           {
            datetime dt = (datetime)StringToInteger(parts[0]);
            double score = StringToDouble(parts[1]);
            
            // iBarShift tìm chỉ mục Index nến thông qua Thời gian Timestamp
            int shift = iBarShift(_Symbol, _Period, dt, false);
            if(shift >= 0 && shift < ArraySize(AISignalBuffer))
              {
               AISignalBuffer[shift] = score;
               count++;
              }
           }
        }
      FileClose(handle);
      Print("✅ [AI Indicator] Đã cập nhật lại đồ thị: vẽ ", count, " điểm nến từ file CSV.");
     }
   else
     {
      Print("❌ [AI Indicator] Không thấy file ai_predictions.csv ở thư mục MetaQuotes\\Terminal\\Common\\Files !");
     }
}
