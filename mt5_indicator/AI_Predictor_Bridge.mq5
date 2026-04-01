//+------------------------------------------------------------------+
//|                                           AI_Predictor_Bridge.mq5 |
//|                                                Antigravity Agent |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Antigravity Agent"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property description "Cầu Nối Đón Data Tín Hiệu PyTorch Bắn Qua API"

input string   InpApiUrl = "http://127.0.0.1:5050/api/"; 
input int      InpHistoryLimit = 1000;

int OnInit()
  {
   Print("🚀 Khởi động Cầu Nối AI Bridge... Đang gọi API Lịch Sử...");
   
   // 1. Tải Lịch sử 1 Lần và Ghi vào File cho Indicator lấy
   string cookie=NULL,headers;
   char post[],result[];
   
   string url = InpApiUrl + "history?limit=" + IntegerToString(InpHistoryLimit);
   int res = WebRequest("GET", url, cookie, NULL, 5000, post, 0, result, headers);
   
   if(res == 200)
     {
      string text = CharArrayToString(result);
      int handle = FileOpen("AI_Predictor_History.csv", FILE_WRITE|FILE_CSV|FILE_ANSI);
      if(handle != INVALID_HANDLE)
        {
         FileWriteString(handle, text);
         FileClose(handle);
         Print("✅ Đã lưu " + IntegerToString(InpHistoryLimit) + " Nến Ký Ức vào AI_Predictor_History.csv");
        }
     }
   else
     {
      Print("❌ Lỗi Tải History: Hãy Thêm 'http://127.0.0.1:5050' vào MT5 Options -> Expert Advisors -> Allow WebRequest!");
     }
     
   // Báo cho Indicator biết History đã load xong
   GlobalVariableSet("AI_History_Ready", 1.0);
     
   // 2. Kích hoạt Gọi API Live mỗi giây
   EventSetTimer(1);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   GlobalVariableDel("AI_Live_Score");
   GlobalVariableDel("AI_History_Ready");
  }

void OnTimer()
  {
   string cookie=NULL,headers;
   char post[],result[];
   string url = InpApiUrl + "live";
   
   int res = WebRequest("GET", url, cookie, NULL, 1000, post, 0, result, headers);
   if(res == 200)
     {
      string text = CharArrayToString(result);
      string parts[];
      if(StringSplit(text, ',', parts) == 2)
        {
         double score = StringToDouble(parts[1]);
         GlobalVariableSet("AI_Live_Score", score);
        }
     }
  }
//+------------------------------------------------------------------+
