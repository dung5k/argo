import os
import sys
import json
from datetime import datetime, timezone

# Khai báo đường dẫn root để import src
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.api.mt5_v2_services import BrainManager, PredictionService

def export_indicator_csv(run_id: str):
    print(f"=== BẮT ĐẦU XUẤT DỮ LIỆU INDICATOR ===")
    print(f"Run ID: {run_id}")
    
    # 1. Tạo 1 file schedule giả lập ép buộc BrainManager load ĐÚNG run_id này
    config_id = "CFG_XAU_NY_V2_1"
    if "CFG_XAU_NY" in run_id:
        config_path = os.path.join(_ROOT, "data", "bot_config_xau_ny_v2_1.json")
    else:
        # Fallback (nếu cần đổi config base thì sửa đây)
        config_path = os.path.join(_ROOT, "data", "bot_config_xau_ny_v2.json")
        
    temp_sched_path = os.path.join(_ROOT, "data", "temp_export_schedule.json")
    schedule_data = {
        "schedule": {
            "ny": {
                "active_utc": ["00:00-23:59"], 
                "run_id": run_id,
                "config_id": config_id,
                "weight_file": "xauusd_ny_weights_EV_L3_1.4_L4_1.0.pth"
            }
        }
    }
    
    with open(temp_sched_path, "w", encoding="utf-8") as fs:
        json.dump(schedule_data, fs, indent=4)
        
    print(f"- Đã giả lập Schedule: {temp_sched_path}")
    
    # 2. Khởi tạo BrainManager và Services
    print("- Đang tải BrainManager (Cloud/Model Weights)...")
    try:
        bm = BrainManager(config_path, temp_sched_path)
        ok = bm.load_brains("XAUUSDm")
        # 1.5 Download Scaler từ HuggingFace vào `data/scaler_v2.pkl`
        try:
            from huggingface_hub import hf_hub_download
            import shutil
            # Scaler thư mục trên mây phụ thuộc cấu hình, vì Config là CFG_XAU_NY nên nó nằm ở data/CFG_XAU_NY_V2_1/scaler_...
            print(f"- Đang kéo scaler từ thư mục run {run_id} trên mây...")
            s_path = hf_hub_download(repo_id="dung5k/argo_data", filename=f"runs/{run_id}/scaler_v2.pkl", repo_type="dataset")
            shutil.copy(s_path, os.path.join(_ROOT, "data", "scaler_v2.pkl"))
            print("  => Đã chép Scaler xong.")
        except Exception as e:
            print(f"Cảnh báo tải Scaler: {e}")
            
        print("- Khởi tạo PredictionService (Kết nối MT5)...")
        service = PredictionService(bm, config_path)
        
        # 3. Kéo dữ liệu lịch sử và Tính toán
        # Kéo 10000 nến MT5 tổng (khoảng 1 tuần), sau đó lọc lấy giờ NY
        print(f"- Đang trích xuất lịch sử MT5 & Inference 10000 nến, rồi lọc phiên NY (13h-22h)...")
        history = service.get_prediction_history_for_session(
            "XAUUSDm", "M1", limit=10000, target_session="ny", target_hours=(13, 22)
        )
        
        if not history:
            print("❌ Không kéo được dữ liệu MT5/Predictor cho phiên tương ứng.")
            return
            
        # Chỉ lấy 4 ngày gần nhất (4 ngày * 9 giờ * 60 nến = 2160 nến)
        history = history[-2160:]
        print(f"=> Đã chắt lọc lấy đúng {len(history)} nến của phiên mục tiêu.")
            
        # 4. Ghi CSV cho MT5 Indicator (FILE_COMMON)
        csv_lines = []
        for t, prob in history:
            # t là UNIX timestamp Integer
            csv_lines.append(f"{t},{prob:.4f}")
            
        out_dir = os.path.join(os.environ["APPDATA"], "MetaQuotes", "Terminal", "Common", "Files")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "ai_predictions.csv")
        
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(csv_lines))
            
        print(f"✅ THÀNH CÔNG! Đã dự báo xong {len(csv_lines)} nến.")
        print(f"👉 Đã lưu file: {out_file}")
        print("Mở MT5 và xem Indicator AI_Predictor_Simple.mq5 nhé!")
        
    finally:
        # Xoá dọn dẹp
        if os.path.exists(temp_sched_path):
            os.remove(temp_sched_path)

if __name__ == "__main__":
    import sys
    target_run = "run_20260417_202144_xauusd_CFG_XAU_NY_TRANSFORMER_V2_2"
    if len(sys.argv) > 1:
        target_run = sys.argv[1]
    export_indicator_csv(target_run)
