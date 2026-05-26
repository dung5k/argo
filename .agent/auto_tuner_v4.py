import os
import json
import subprocess
import time
import shutil
from datetime import datetime

def send_telegram(msg, done=False):
    cmd = ["python", ".agent/send_to_tele.py", msg]
    if done:
        cmd.append("--done")
    subprocess.run(cmd)

def check_score(run_dir):
    metrics = os.path.join(run_dir, "results", "training_metrics_v3.json")
    if os.path.exists(metrics):
        try:
            with open(metrics, "r") as f:
                data = json.load(f)
                return data["sessions"]["london"]["BEST_VLOSS"]["composite_score"]
        except:
            return 0
    return None

def run_training_loop():
    base_config = "workspaces/CFG_LTC_LONDON_V3_5/base_config.json"
    
    # Wait for run 40 to finish if it's running
    run_40_dir = "workspaces/CFG_LTC_LONDON_V3_5/runs/run_20260427_102339_v4_ldn_40"
    if os.path.exists(run_40_dir):
        send_telegram("Auto-tuner đang giám sát Run 40...")
        while True:
            score = check_score(run_40_dir)
            if score is not None:
                if score >= 0.65:
                    send_telegram(f"Thành công! Run 40 đạt Composite Score: {score:.4f} >= 0.65", done=True)
                    return
                else:
                    send_telegram(f"Run 40 thất bại (Score: {score:.4f}). Auto-tuner sẽ tạo run mới...")
                    break
            time.sleep(30)
            
    # Loop for new runs
    hyperparams = [
        {"WINDOW_SIZE": 15, "D_MODEL": 64, "NUM_LAYERS": 1, "DROPOUT": 0.45, "N_HEAD": 4},
        {"WINDOW_SIZE": 30, "D_MODEL": 16, "NUM_LAYERS": 2, "DROPOUT": 0.35, "N_HEAD": 4},
        {"WINDOW_SIZE": 15, "D_MODEL": 32, "NUM_LAYERS": 2, "DROPOUT": 0.40, "N_HEAD": 4},
        {"WINDOW_SIZE": 30, "D_MODEL": 64, "NUM_LAYERS": 2, "DROPOUT": 0.50, "N_HEAD": 4}
    ]
    
    for hp in hyperparams:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S_v4_ldn_auto")
        run_dir = os.path.join("workspaces/CFG_LTC_LONDON_V3_5/runs", run_id)
        os.makedirs(run_dir, exist_ok=True)
        
        with open(base_config, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        config["RUN_ID"] = run_id
        config["FEATURE_ENGINEERING"]["WINDOW_SIZE"] = hp["WINDOW_SIZE"]
        config["FEATURE_ENGINEERING"]["VOL_REGIME"] = True
        config["FEATURE_ENGINEERING"]["ORDER_FLOW"] = True
        config["FEATURE_ENGINEERING"]["MTF_WINDOWS"] = [15, 60]
        if "MACRO_FEATURES" not in config["FEATURE_ENGINEERING"]:
            config["FEATURE_ENGINEERING"]["MACRO_FEATURES"] = {}
        config["FEATURE_ENGINEERING"]["MACRO_FEATURES"]["BTCUSDT"] = ["log_ret", "bb_width", "volume", "corr_60", "spread_ret", "relative_strength"]
        config["FEATURE_ENGINEERING"]["MACRO_FEATURES"]["ETHUSDT"] = ["log_ret", "volume", "spread_ret", "relative_strength"]
        
        config["TRAINING"]["D_MODEL"] = hp["D_MODEL"]
        config["TRAINING"]["NUM_LAYERS"] = hp["NUM_LAYERS"]
        config["TRAINING"]["DROPOUT"] = hp["DROPOUT"]
        config["TRAINING"]["N_HEAD"] = hp["N_HEAD"]
        
        with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        send_telegram(f"Khởi chạy auto run: {run_id} với HP: {hp}")
        
        cmd = f"python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_LONDON_V3_5/runs/{run_id}/config.json --no-push && python src/training_v3/train_v3.py workspaces/CFG_LTC_LONDON_V3_5/runs/{run_id}/config.json --session london --scratch --run-id {run_id}"
        subprocess.run(cmd, shell=True)
        
        score = check_score(run_dir)
        if score and score >= 0.65:
            send_telegram(f"🎉 Auto-tuner THÀNH CÔNG! Run {run_id} đạt Composite Score: {score:.4f}", done=True)
            return
        else:
            send_telegram(f"Auto-tuner: Run {run_id} chưa đạt (Score: {score}). Chuyển sang config tiếp theo...")

    send_telegram("Auto-tuner đã hết config thử nghiệm mà vẫn chưa đạt 0.65.", done=True)

if __name__ == "__main__":
    run_training_loop()
