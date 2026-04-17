import os
import sys
import time
import json
import traceback

safe_script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.api.mt5_v2_services import BrainManager, PredictionService

def main():
    print("🚀 Đang khởi tạo mô hình AI để xuất Dữ liệu Lịch sử liên tục...")
    
    main_config = os.path.join(safe_script_dir, "data", "bot_config_xau_asian_v2_1.json")
    schedule = os.path.join(safe_script_dir, "data", "bot_v2_brain_schedule.json")
    
    brain_mgr = BrainManager(main_config, schedule)
    brain_mgr.load_brains()
    
    try:
        with open(schedule, "r", encoding="utf-8-sig") as f:
            mt5_path = json.load(f).get("mt5_path", "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe")
    except:
        mt5_path = ""
        
    pred_svc = PredictionService(brain_mgr, mt5_config=mt5_path)
    
    target_dir = "C:/argo"
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, "predictions.csv")
    
    # Cố gắng lưu thêm 1 bản vào Common Files của MT5 để Indicator đọc dễ dàng mà không bị Sandbox cản
    mt5_common_dir = os.path.join(os.environ.get("APPDATA", ""), "MetaQuotes", "Terminal", "Common", "Files")
    os.makedirs(mt5_common_dir, exist_ok=True)
    mt5_common_file = os.path.join(mt5_common_dir, "ai_predictions.csv")
    
    print(f"🔥 Sẵn sàng. Bắt đầu vòng lặp xuất 2500 nến ra file mỗi phút (CHỈ VẼ TRONG KHUNG NY SESSION).")
    print(f"📁 File chính: {target_file}")
    print(f"📁 File MT5 Common (Dễ đọc): {mt5_common_file}")
    
    while True:
        try:
            history = pred_svc.get_prediction_history_for_session(
                symbol="XAUUSDm", 
                timeframe="M1", 
                limit=2500, 
                target_session="asian",
                target_hours=(0, 7)  # UTC 00:00-07:00 = Asian session
            )
            
            if history:
                csv_lines = [f"{t},{prob:.4f}" for t, prob in history]
                csv_text = "\n".join(csv_lines)
                
                # Ghi vào Argo
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(csv_text)
                    
                # Ghi vào MT5 Common Files
                with open(mt5_common_file, "w", encoding="utf-8") as f:
                    f.write(csv_text)
                    
                print(f"[{time.strftime('%H:%M:%S')}] ✅ Đã xuất thành công {len(history)} dòng ra file.")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ API trả về rỗng, đang đợi chu kỳ sau...")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ Lỗi xuất file: {e}")
            traceback.print_exc()
            
        time.sleep(60) # Cứ 1 phút (1 nến) làm mới lại file 1 lần

if __name__ == "__main__":
    main()
