import os
import json
import subprocess
import sys

def main():
    workspace = "CFG_XAG_LDN_V3_5"
    run_id = "run_20260427_200719_v4_ldn_25"
    session = "ldn"
    
    python_exe = r"C:\Python311\python.exe"
    
    commands = [
        [python_exe, "scripts/crawl_crypto_v3.py", f"workspaces/{workspace}/runs/{run_id}/config.json"],
        [python_exe, "scripts/upload_v3_dataset.py", "--config", f"workspaces/{workspace}/runs/{run_id}/config.json"],
        [python_exe, "src/training_v3/train_v3.py", f"workspaces/{workspace}/runs/{run_id}/config.json", "--session", session, "--scratch", "--run-id", run_id]
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
            
    # Đọc metrics
    metrics_path = f"workspaces/{workspace}/runs/{run_id}/results/training_metrics_v3.json"
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
                    
        report = f"KẾT QUẢ CHIẾN LƯỢC 2 (Vòng Lặp 2 - Mean Reversion Khắt Khe):\n"
        report += f"- Win Rate: {win_rate:.2f}%\n"
        report += f"- Composite Score: {score:.4f}\n"
        
        if score < 0.65 or win_rate < 80.0:
            report += f"\nBÁO CÁO THẤT BẠI: Mô hình không đạt chuẩn. "
            report += f"Mặc dù đã nới rộng biên độ TP/SL lên 40/40 pips và mở rộng góc nhìn (Window=20), kết quả (Composite: {score:.4f}) vẫn không đủ để bù đắp rủi ro thực chiến. "
            report += f"Điều này chứng tỏ thị trường XAG London hiện tại không chạy theo xu hướng Mean Reversion chuẩn mực, hoặc các Leader DXYm/XAUUSDm không cung cấp tín hiệu cạn kiệt đáng tin cậy. Sẽ luân phiên tiếp sang Vòng lặp 2 của Chiến lược 3."
        else:
            report += f"\nTHÀNH CÔNG: Mô hình đạt chuẩn an toàn. Composite Score {score:.4f} >= 0.65 và Win Rate > 80%."
            
        subprocess.run([python_exe, ".agent/send_to_tele.py", report, "--done"])
    else:
        subprocess.run([python_exe, ".agent/send_to_tele.py", f"Lỗi: Không tìm thấy training_metrics_v3.json sau khi huấn luyện {run_id}.", "--done"])
        
    subprocess.run([python_exe, ".agent/notify_done.py", "xag_london_v3_training_done"])

if __name__ == "__main__":
    main()
