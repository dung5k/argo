import os
import sys
import json
import argparse
import subprocess
import re
from datetime import datetime, timedelta

# Ngưỡng (Thresholds)
VAL_LOSS_THRESHOLD = 0.50
WIN_RATE_THRESHOLD = 0.45  # 45%
SIGNALS_PER_DAY_THRESHOLD = 5

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=str, required=True, help="Đường dẫn tới thư mục run (chứa results/training_metrics_vX.json)")
    parser.add_argument("--session", type=str, required=True, help="asian, london, hoặc ny")
    parser.add_argument("--symbol", type=str, required=True, help="XAG, LTC, etc.")
    parser.add_argument("--version", type=str, required=True, help="v3, v5, v6, etc.")
    return parser.parse_args()

def check_thresholds(run_dir, session_name, version):
    metrics_path = os.path.join(run_dir, "results", f"training_metrics_{version.lower()}.json")
    if not os.path.exists(metrics_path):
        print(f"Không tìm thấy file metrics: {metrics_path}")
        return False, "Không tìm thấy metrics"

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        sess_data = data.get("sessions", {}).get(session_name.lower(), {})
        best_vloss = sess_data.get("BEST_VLOSS", {})
        val_loss = best_vloss.get("val_loss", 999.0)
        
        threshold_metrics = best_vloss.get("threshold_metrics", [])
        if not threshold_metrics:
            return False, "Không có threshold metrics"
            
        # Chọn threshold metric có ev_score cao nhất
        best_metric = max(threshold_metrics, key=lambda x: x.get("ev_score", -999))
        win_rate = best_metric.get("win_rate", 0)
        total_signals = best_metric.get("total_signals", 0)
        
        print(f"Kiểm tra ngưỡng:")
        print(f"  - Val Loss: {val_loss:.4f} (Cần <= {VAL_LOSS_THRESHOLD})")
        print(f"  - Win Rate: {win_rate*100:.2f}% (Cần >= {WIN_RATE_THRESHOLD*100}%)")
        print(f"  - Total Signals: {total_signals} (Cần >= {SIGNALS_PER_DAY_THRESHOLD})")
        
        if val_loss <= VAL_LOSS_THRESHOLD and win_rate >= WIN_RATE_THRESHOLD and total_signals >= SIGNALS_PER_DAY_THRESHOLD:
            return True, f"Pass (ValLoss={val_loss:.3f}, WR={win_rate*100:.1f}%, Sigs={total_signals})"
        else:
            return False, f"Failed thresholds"
    except Exception as e:
        print(f"Lỗi khi kiểm tra metrics: {e}")
        return False, f"Lỗi đọc metrics: {e}"

def run_simulator(run_dir, session_name, symbol, version):
    # Tìm model .pth mới nhất trong brains/
    brains_dir = os.path.join(run_dir, "brains")
    if not os.path.exists(brains_dir):
        print("Không tìm thấy thư mục brains/")
        return None
        
    model_files = [os.path.join(brains_dir, f) for f in os.listdir(brains_dir) if f.endswith(".pth")]
    if not model_files:
        print("Không có file .pth nào trong thư mục brains/")
        return None
        
    latest_model = max(model_files, key=os.path.getmtime)
    config_file = f"data/bot_config_{symbol.lower()}_{session_name.lower()}_{version.lower()}.json"
    
    start_date = datetime(2026, 5, 1)
    end_date = datetime.now()
    
    total_pnl = 0.0
    total_win = 0
    total_loss = 0
    total_signals = 0
    
    current_date = start_date
    print(f"\n🚀 BẮT ĐẦU CHẠY SIMULATOR TỪ 01/05 ĐẾN NAY CHO {session_name.upper()}")
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"  -> Simulating {date_str}...")
        
        cmd = [
            sys.executable,
            "scripts/run_simulator.py",
            "--config", config_file,
            "--date", date_str,
            "--session", session_name.lower(),
            "--model", latest_model
        ]
        
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        out_file = f"temp/sim_{session_name}_{date_str}.txt"
        
        try:
            with open(out_file, "w", encoding="utf-8") as f_out:
                subprocess.run(cmd, stdout=f_out, stderr=subprocess.STDOUT, check=False, env=env)
                
            with open(out_file, "r", encoding="utf-8") as f_read:
                output = f_read.read()
                
            pnl_match = re.search(r"P&L \(\$\)\s*:\s*(.*?)$", output, re.MULTILINE)
            win_loss_match = re.search(r"Lệnh đóng \(W/L\)\s*:\s*(.*?\))", output)
            sigs_match = re.search(r"Tín hiệu BUY / SELL\s*:\s*(.*?)\s*/\s*(.*?)$", output, re.MULTILINE)
            
            if pnl_match:
                pnl = float(pnl_match.group(1).strip().replace("+", ""))
                total_pnl += pnl
            if win_loss_match:
                wl_str = win_loss_match.group(1) # e.g. "2W/1L"
                w_m = re.search(r"(\d+)W", wl_str)
                l_m = re.search(r"(\d+)L", wl_str)
                if w_m: total_win += int(w_m.group(1))
                if l_m: total_loss += int(l_m.group(1))
            if sigs_match:
                total_signals += int(sigs_match.group(1)) + int(sigs_match.group(2))
                
        except Exception as e:
            print(f"Lỗi khi chạy simulator ngày {date_str}: {e}")
            
        current_date += timedelta(days=1)
        
    return {
        "pnl": total_pnl,
        "win": total_win,
        "loss": total_loss,
        "signals": total_signals,
        "model": os.path.basename(latest_model)
    }

def main():
    args = parse_args()
    os.makedirs("temp", exist_ok=True)
    
    passed, reason = check_thresholds(args.run_dir, args.session, args.version)
    if not passed:
        print(f"Mô hình không đạt ngưỡng chạy Simulator: {reason}")
        return
        
    print(f"Mô hình ĐẠT NGƯỠNG! ({reason})")
    subprocess.run([sys.executable, ".agent/send_to_tele.py", f"🌟 Đạt ngưỡng chất lượng: {reason}. Bắt đầu chạy Simulator tự động từ 1/5 cho phiên {args.session.upper()}...", "--channel", "1816854047"])
    
    # Run Simulator
    res = run_simulator(args.run_dir, args.session, args.symbol, args.version)
    if not res:
        return
        
    total_trades = res["win"] + res["loss"]
    wr = (res["win"] / total_trades * 100) if total_trades > 0 else 0
    
    report = (
        f"📊 **KẾT QUẢ SIMULATOR (TỪ 01/05 ĐẾN NAY)** 📊\n"
        f"- Phiên: {args.session.upper()} ({args.version.upper()})\n"
        f"- Model: {res['model']}\n\n"
        f"🔹 **Tổng P&L**: ${res['pnl']:+.2f}\n"
        f"🔹 **Win Rate**: {wr:.1f}%\n"
        f"🔹 **Tổng lệnh đóng**: {total_trades} ({res['win']}W / {res['loss']}L)\n"
        f"🔹 **Tổng tín hiệu**: {res['signals']}\n"
    )
    
    # Gọi Agent Review Code / Strategy 
    print("Gọi Agent Review...")
    prompt_msg = (
        f"Hãy review nhanh cấu trúc code và chiến lược cho {args.session} version {args.version}. "
        f"Hiệu suất từ 1/5: PnL {res['pnl']:+.2f}, WinRate {wr:.1f}%. Hãy đưa ra đánh giá ngắn gọn."
    )
    
    review_output = ""
    try:
        # Ở đây ta có thể gọi một script AI cụ thể. Tạm thời mô phỏng một lệnh gọi.
        # Hoặc dùng skill_training_report.py
        review_output = "\n\n🤖 **Agent Review**: "
        ai_res = subprocess.check_output(
            [sys.executable, "scripts/skill_training_report.py", "--prompt", prompt_msg, "--symbol", args.symbol],
            text=True, encoding="utf-8"
        )
        # Lấy phần chữ, bỏ JSON
        text_only = re.sub(r"```json.*?```", "", ai_res, flags=re.DOTALL)
        review_output += text_only[:500] + "...\n(Xem thêm trên IDE)"
    except Exception:
        review_output += "Lỗi khi gọi Agent Review, vui lòng check log."

    full_report = report + review_output
    subprocess.run([sys.executable, ".agent/send_to_tele.py", full_report, "--channel", "1816854047"])
    print("Hoàn tất!")

if __name__ == "__main__":
    main()
