import os
import sys

safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
import uvicorn
from pydantic import BaseModel
import traceback
import json

from src.api.mt5_v2_services import BrainManager, PredictionService

app = FastAPI(title="MT5 AI Predictor Bridge V2")

# Global instances
brain_mgr = None
pred_svc = None

@app.on_event("startup")
async def startup_event():
    global brain_mgr, pred_svc
    
    # Init config and schedule from data/
    main_config = os.path.join(safe_script_dir, "data", "bot_config_xau_london_v2_1.json")
    schedule = os.path.join(safe_script_dir, "data", "bot_v2_brain_schedule.json")
    
    brain_mgr = BrainManager(main_config, schedule)
    brain_mgr.load_brains()
    
    # Read mt5 path from schedule globally
    try:
        with open(schedule, "r", encoding="utf-8-sig") as f:
            mt5_path = json.load(f).get("mt5_path", "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe")
    except:
        mt5_path = ""
        
    pred_svc = PredictionService(brain_mgr, mt5_config=mt5_path)
    print("🚀 [FastAPI] Backend V2 đã sẵn sàng nhận tín hiệu từ MT5!")


@app.get("/api/v2/history", response_class=PlainTextResponse)
async def get_history(symbol: str = "XAUUSDm", limit: int = 300):
    """
    Trả về Csv Lịch sử: `timestamp,prob_up` để Indicator vẽ lại biểu đồ.
    Limit mặc định là 300 thay vì 1000 để chống Lag.
    """
    try:
        history = pred_svc.get_prediction_history(symbol=symbol, timeframe="M1", limit=limit)
        if not history:
            return ""
            
        csv_lines = [f"{t},{prob:.4f}" for t, prob in history]
        return "\n".join(csv_lines)
    except Exception as e:
        print(traceback.format_exc())
        return f"ERROR,{e}"


@app.get("/api/v2/predict", response_class=PlainTextResponse)
async def get_predict(symbol: str = "XAUUSDm"):
    """
    Trả về Live Tick: `timestamp,prob_up`
    Note: Hiện tại ta chọc thẳng vào DB MT5Data nên không cần MQL5 truyền time, tuy nhiên nếu MQL5 
    có độ trễ, nó lấy Time() trên cây nến báo về thì Python cũng chủ động load tới giờ đó.
    Tạm thời để đơn giản, gọi pull_data live luôn.
    """
    try:
        res = pred_svc.get_live_prediction(symbol=symbol)
        if not res:
            return "0,0.5" # Fallback
            
        return f"{res['timestamp']},{res['prob_up']:.4f}"
    except Exception as e:
        print(traceback.format_exc())
        return "0,0.5"

if __name__ == "__main__":
    uvicorn.run("src.api.mt5_v2_api:app", host="127.0.0.1", port=5050, reload=False, log_level="info")
