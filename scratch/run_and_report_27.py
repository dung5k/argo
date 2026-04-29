import os
import json
import subprocess
import sys

def main():
    workspace = "CFG_XAG_LDN_V3_5"
    run_id = "run_20260427_202037_v4_ldn_27"
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
                    
        report = f"KẾT QUẢ CHIẾN LƯỢC 4 (Vòng Lặp 2 - Smart Money Micro-Scalping):\n"
        report += f"- Win Rate: {win_rate:.2f}%\n"
        report += f"- Composite Score: {score:.4f}\n"
        
        if score < 0.65 or win_rate < 80.0:
            report += f"\nBÁO CÁO THẤT BẠI: Mô hình tiếp tục không đạt chuẩn an toàn. "
            report += f"Mặc dù đã bổ sung Order Flow để AI đánh Scalp chính xác hơn, tỷ lệ Win Rate và Composite Score ({score:.4f}) vẫn không đủ để vượt qua thử thách của Spread. "
            report += f"Cả 4 chiến lược ở Vòng 1 và Vòng 2 đều THẤT BẠI thảm hại. Phiên London thực sự quá nhiễu đối với bộ Features hiện tại. Hệ thống sẽ tạm dừng luân phiên để yêu cầu Kỹ sư xem xét lại nền tảng dữ liệu hoặc sáp nhập phiên."
        else:
            report += f"\nTHÀNH CÔNG: Đã tìm ra Chén Thánh cho phiên London! Mô hình đạt chuẩn an toàn. Composite Score {score:.4f} >= 0.65 và Win Rate > 80%."
            
        subprocess.run([python_exe, ".agent/send_to_tele.py", report, "--done"])
    else:
        subprocess.run([python_exe, ".agent/send_to_tele.py", f"Lỗi: Không tìm thấy training_metrics_v3.json sau khi huấn luyện {run_id}.", "--done"])
        
    subprocess.run([python_exe, ".agent/notify_done.py", "xag_london_v3_training_done"])

if __name__ == "__main__":
    main()
