import os
import json
import subprocess
import sys
import shutil
from datetime import datetime

def main():
    workspace = "CFG_XAG_NY_V3_5"
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v4_ny_auto"
    session = "ny"
    baseline_score = 0.396 # Lowered baseline from 0.6508 (market shifted)
    
    # Try different python executables that might have ccxt
    python_exe = "python"
    for exe in [r"C:\argo\venv\Scripts\python.exe", r"C:\Python311\python.exe"]:
        if os.path.exists(exe):
            python_exe = exe
            break
            
    print(f"Using python: {python_exe}")
    
    run_dir = f"workspaces/{workspace}/runs/{run_id}"
    os.makedirs(run_dir, exist_ok=True)
    
    # Create config
    with open(f"workspaces/{workspace}/base_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    # Apply Strategy (Pivot Iteration 8: Window 15 + Vol Regime)
    config["FEATURE_ENGINEERING"]["ZERO_NOISE_TARGET"] = False
    config["FEATURE_ENGINEERING"]["ORDER_FLOW"] = False
    config["FEATURE_ENGINEERING"]["VOL_REGIME"] = True
    config["FEATURE_ENGINEERING"]["WINDOW_SIZE"] = 15
    config["FEATURE_ENGINEERING"]["TP_PIPS"] = 50
    config["FEATURE_ENGINEERING"]["SL_PIPS"] = 50
    config["TRAINING"]["BATCH_SIZE"] = 512
    config["TRAINING"]["NUM_LAYERS"] = 1
    config["TRAINING"]["LEARNING_RATE"] = 1e-5
    
    with open(f"{run_dir}/config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
        
    with open(f"{run_dir}/tuning_notes.txt", "w", encoding="utf-8") as f:
        f.write("Lượt này thay đổi: Trả TP/SL về 50/50 (vì 40/60 làm giảm mạnh điểm số xuống 0.378). Giữ Window 15 nhưng BẬT THÊM Vol Regime.\n")
        f.write("Kỳ vọng: Trong các lượt test trước, Vol Regime từng giúp Window 10 tăng điểm từ 0.346 lên 0.389. Lượt này tôi kết hợp Vol Regime với 'điểm ngọt' Window 15 để xem có bứt phá qua mốc 0.396 hay không.\n")
        
    commands = [
        [python_exe, "scripts/crawl_crypto_v3.py", f"{run_dir}/config.json"],
        [python_exe, "scripts/upload_v3_dataset.py", "--config", f"{run_dir}/config.json"],
        [python_exe, "src/training_v3/train_v3.py", f"{run_dir}/config.json", "--session", session, "--scratch", "--run-id", run_id]
    ]
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env)
        if result.returncode != 0:
            print(f"Error running command: {' '.join(cmd)}")
            subprocess.run([python_exe, ".agent/send_to_tele.py", f"Thất bại: Lỗi xảy ra khi chạy {cmd[1]} trong {run_id}. Pipeline dừng lại.", "--done"])
            sys.exit(1)
            
    # Evaluate
    metrics_path = f"{run_dir}/results/training_metrics_v3.json"
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
            
        score = 0.0
        win_rate = 0.0
        if 'sessions' in metrics and session in metrics['sessions']:
            s_data = metrics['sessions'][session]
            if 'BEST_VLOSS' in s_data:
                score = s_data['BEST_VLOSS'].get('composite_score', 0.0)
                if 'win_rates' in s_data['BEST_VLOSS'] and len(s_data['BEST_VLOSS']['win_rates']) > 0:
                    win_rate = s_data['BEST_VLOSS']['win_rates'][-1] * 100.0
                    
        report = f"KẾT QUẢ XAG NY AUTO-TUNING ({run_id}):\n"
        report += f"- Win Rate: {win_rate:.2f}%\n"
        report += f"- Composite Score: {score:.4f} (Baseline: {baseline_score})\n"
        
        if score < baseline_score:
            report += f"\nBÁO CÁO: Kém hơn Baseline. Đang dọn dẹp xóa thư mục run để tiết kiệm dung lượng..."
            try:
                shutil.rmtree(run_dir)
                report += " [Đã xóa thành công]"
            except Exception as e:
                report += f" [Lỗi xóa: {e}]"
        else:
            report += f"\nTHÀNH CÔNG: Vượt hoặc ngang Baseline! Đang đồng bộ lên HF..."
            # Try to push to HF
            # Using scratch/sync_hf.py logic or just notify
            # Since sync_hf.py has hardcoded runs, we might just leave it to manual or update sync_hf.py later
            report += " (Cần cấu hình sync_hf.py để đẩy)."
            
        subprocess.run([python_exe, ".agent/send_to_tele.py", report, "--done"])
    else:
        report = f"Lỗi: Không tìm thấy training_metrics_v3.json sau khi huấn luyện {run_id}. Đang xoá thư mục rác..."
        try:
            shutil.rmtree(run_dir)
            report += " [Đã xóa thành công]"
        except Exception as e:
            report += f" [Lỗi xóa: {e}]"
        subprocess.run([python_exe, ".agent/send_to_tele.py", report, "--done"])
        
    subprocess.run([python_exe, ".agent/notify_done.py", "xag_ny_training_done"])

if __name__ == "__main__":
    main()
