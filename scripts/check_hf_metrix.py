from huggingface_hub import HfFileSystem, hf_hub_download
import json
import os
import datetime
import json

with open("tg_config.json", "r") as f:
    cfg = json.load(f)
token = cfg.get("hf_token")

def check_recent_runs():
    fs = HfFileSystem(token=token)
    try:
        runs = fs.ls('datasets/dung5k/argo_data/runs')
        if not runs:
            print("Không tìm thấy dữ liệu runs trên HF.")
            return

        # Sắp xếp để lấy 3 runs gần nhất
        recent_runs = sorted([r['name'] for r in runs], reverse=True)[:3]
        
        print(f"=== BÁO CÁO TIẾN ĐỘ HỌC TẬP TỪ HUGGINGFACE ===")
        for r_path in recent_runs:
            run_id = r_path.split('/')[-1]
            try:
                # Tải file metrix thẳng từ Hub 
                local_path = hf_hub_download(repo_id="dung5k/argo_data", repo_type="dataset", filename=f"runs/{run_id}/training_metrix_v2.json", token=token)
                with open(local_path, 'r', encoding='utf-8') as f:
                    metrix = json.load(f)
                
                epochs = [e for e in metrix.keys() if e.isdigit()]
                epochs.sort(key=int)
                if not epochs:
                    print(f"Run: {run_id} | Chưa có dữ liệu Epoch nào.")
                    continue
                    
                # Lấy 5 epoch cuối
                last_epochs = epochs[-5:]
                print(f"Run: {run_id} | Trạng thái 5 Epoch cuối: {last_epochs}")
                
                # Check VLoss để xem có cải thiện không hay kẹt
                vloss_history = [metrix[e].get("val_loss", 999) for e in last_epochs]
                
                trend = "ĐANG TỐT LÊN" if vloss_history[0] > vloss_history[-1] else "KẸT HOẶC ĐI NGANG"
                
                print(f"> VLoss History: {[round(v, 4) for v in vloss_history]}")
                print(f"> Đánh giá: {trend}\n")
                
            except Exception as e:
                print(f"Run: {run_id} | Chưa có file Metrix hoặc lỗi: {e}")
    except Exception as e:
        print(f"Lỗi truy xuất HF: {e}")

if __name__ == "__main__":
    check_recent_runs()
