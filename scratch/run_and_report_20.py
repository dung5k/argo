import os
import json
import subprocess
import sys

def main():
    workspace = "CFG_XAG_LDN_V3_5"
    run_id = "run_20260427_190222_v4_ldn_20"
    session = "ldn"
    
    python_exe = r"C:\Python311\python.exe"
    
    commands = [
        [python_exe, "scripts/crawl_crypto_v3.py", f"workspaces/{workspace}/runs/{run_id}/config.json"],
        [python_exe, "scripts/upload_v3_dataset.py", "--config", f"workspaces/{workspace}/runs/{run_id}/config.json"],
        [python_exe, "src/training_v3/train_v3.py", f"workspaces/{workspace}/runs/{run_id}/config.json", "--session", session, "--scratch", "--run-id", run_id]
    ]
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Error running command: {' '.join(cmd)}")
            subprocess.run([python_exe, ".agent/send_to_tele.py", f"Thất bại: Lỗi xảy ra khi chạy {cmd[1]} trong {run_id}. Pipeline dừng lại.", "--done"])
            sys.exit(1)
            
    # Đọc metrics.json
    metrics_path = f"workspaces/{workspace}/runs/{run_id}/metrics.json"
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
            
        win_rate = metrics.get('win_rate', 0.0)
        composite_score = metrics.get('composite_score', 0.0)
        expectancy = metrics.get('expectancy', 0.0)
        
        report = f"KẾT QUẢ CHIẾN LƯỢC 1 (London Open Breakout):\n"
        report += f"- Win Rate: {win_rate:.2f}%\n"
        report += f"- Composite Score: {composite_score:.4f}\n"
        report += f"- Expectancy: {expectancy:.4f}\n"
        
        if composite_score < 0.65 or win_rate < 80.0 or expectancy < 0:
            report += f"\nBÁO CÁO THẤT BẠI: Mô hình không đạt chuẩn. "
            report += f"Với Win Rate {win_rate:.2f}% và Composite {composite_score:.4f}, mang mô hình này ra thực chiến CHẮC CHẮN SẼ CHÁY TÀI KHOẢN do Spread và Slippage. "
            report += f"Dữ liệu US10Y và VIX khung 1M có vẻ quá nhiễu hoặc không đủ khả năng giải thích tín hiệu bắt đỉnh đáy phiên Á. Cần xem xét phẫu thuật tận gốc hoặc chuyển sang Chiến lược 2 (Mean Reversion)."
        else:
            report += f"\nTHÀNH CÔNG: Mô hình đạt chuẩn an toàn. Composite Score {composite_score:.4f} >= 0.65 và Win Rate > 80%."
            
        subprocess.run([python_exe, ".agent/send_to_tele.py", report, "--done"])
    else:
        subprocess.run([python_exe, ".agent/send_to_tele.py", f"Lỗi: Không tìm thấy metrics.json sau khi huấn luyện {run_id}.", "--done"])
        
    subprocess.run([python_exe, ".agent/notify_done.py", "xag_london_v3_training_done"])

if __name__ == "__main__":
    main()
