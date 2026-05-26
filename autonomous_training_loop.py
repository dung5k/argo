import subprocess
import os
import sys
import time
import shutil
import glob
from datetime import datetime
import json
import importlib.util
import argparse

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def setup_prompt(prompt_path):
    if not os.path.exists(prompt_path):
        return
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    if "json" not in prompt_text.lower():
        prompt_text += """\n\nBẮT BUỘC: Phần cuối cùng của câu trả lời của bạn PHẢI chứa một khối JSON (nằm trong ```json ... ```) với định dạng sau để hệ thống tự động thiết lập cấu hình:
```json
{
  "target_session": "asian", // "asian", "london", hoặc "ny"
  "reason": "Lý do chọn phiên này và thay đổi cấu hình",
  "config_updates": {
    "TRAIN.LR_INIT": 0.0001,
    "FEATURE_ENGINEERING.TP_PCT": 0.003,
    "FEATURE_ENGINEERING.SL_PCT": 0.002
  }
}
```
Lưu ý: Chỉ cập nhật các tham số bạn cho là cần thiết (Explore). Nếu không cần đổi gì (Exploit), để config_updates rỗng {}.
"""
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt_text)

def get_ai_decision(prompt_path, symbol):
    print("--- [1] TỔNG HỢP BÁO CÁO VÀ GỌI AI ---")
    try:
        report_output = subprocess.check_output(
            [sys.executable, "scripts/skill_training_report.py", "--prompt-file", prompt_path, "--symbol", symbol],
            env=os.environ,
            text=True,
            encoding="utf-8"
        )
    except subprocess.CalledProcessError as e:
        print("Lỗi khi gọi AI:", e.output)
        return None
    
    print(report_output)
    
    import re
    match = re.search(r"```json\n(.*?)\n```", report_output, re.DOTALL)
    if not match:
        print("Không tìm thấy JSON trong phản hồi của AI!")
        return None
        
    try:
        decision = json.loads(match.group(1))
        return decision
    except json.JSONDecodeError as e:
        print("Lỗi parse JSON:", e)
        return None

def cleanup_old_runs(symbol, version, exclude_runs=None, keep_top_n=2):
    """Dọn dẹp các run cũ, chỉ giữ lại top N run tốt nhất cho mỗi phiên."""
    if exclude_runs is None:
        exclude_runs = []
    
    sessions = ["asian", "london", "ny", "weekend"]
    total_deleted = 0
    
    for session in sessions:
        workspace = f"workspaces/CFG_{symbol}_{session.upper()}_{version}"
        runs_dir = os.path.join(workspace, "runs")
        if not os.path.exists(runs_dir):
            continue
        
        # Thu thập metrics của tất cả các run
        scored_runs = []
        unscored_runs = []
        
        for run_name in os.listdir(runs_dir):
            if run_name in exclude_runs:
                continue
            run_path = os.path.join(runs_dir, run_name)
            if not os.path.isdir(run_path):
                continue
            
            metrics_path = os.path.join(run_path, "results", "training_metrics_v3.json")
            if os.path.exists(metrics_path):
                try:
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    best_score = 0
                    for sess_data in m.get("sessions", {}).values():
                        best = sess_data.get("BEST_VLOSS", {})
                        score = best.get("composite_score", 0)
                        if score > best_score:
                            best_score = score
                    scored_runs.append((run_name, best_score))
                except Exception:
                    unscored_runs.append(run_name)
            else:
                unscored_runs.append(run_name)
        
        # Sắp xếp theo score giảm dần
        scored_runs.sort(key=lambda x: x[1], reverse=True)
        
        # Giữ lại top N run có score
        runs_to_keep = set(r[0] for r in scored_runs[:keep_top_n])
        runs_to_delete = [r[0] for r in scored_runs[keep_top_n:]] + unscored_runs
        
        for run_name in runs_to_delete:
            run_path = os.path.join(runs_dir, run_name)
            try:
                shutil.rmtree(run_path)
                total_deleted += 1
                print(f"  🗑️ Đã xóa: {run_path}")
            except Exception as e:
                print(f"  ⚠️ Lỗi xóa {run_path}: {e}")
        
        if runs_to_keep:
            print(f"  ✅ {session.upper()}: Giữ lại {len(runs_to_keep)} run tốt nhất, xóa {len(runs_to_delete)} run cũ.")
    
    if total_deleted > 0:
        print(f"\n🧹 TỔNG DỌN DẸP: Đã xóa {total_deleted} run cũ.")
    return total_deleted

def update_config(session_name, updates, symbol, version, start_date, end_date, custom_params_dict):
    config_file = f"bot_config_{version.lower()}_{symbol.lower()}_{session_name}.json"
    if not os.path.exists(config_file):
        print(f"Không tìm thấy file config {config_file}")
        return config_file
        
    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    # Áp dụng các thay đổi từ AI
    all_updates = updates.copy()
    
    # Ghi đè bằng custom_params từ CLI (nếu có)
    if custom_params_dict:
        all_updates.update(custom_params_dict)
        
    # Ghi đè bằng start_date và end_date từ CLI (nếu có)
    if start_date:
        all_updates["TRAIN.TRAIN_START"] = start_date
    if end_date:
        all_updates["TRAIN.TRAIN_END"] = end_date

    for k, v in all_updates.items():
        parts = k.split('.')
        current = cfg
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = v
        print(f"  -> Cập nhật config: {k} = {v}")
        
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
        
    return config_file

def run_training_loop(args):
    symbol = args.symbol.upper()
    version = args.version.upper()
    prompt_path = args.prompt_file or os.path.join(".agent", f"strategy_prompt_{symbol}.md")
    
    custom_params = {}
    if args.custom_params:
        try:
            custom_params = json.loads(args.custom_params)
        except json.JSONDecodeError as e:
            print("Lỗi parse JSON cho --custom-params:", e)
            sys.exit(1)
            
    setup_prompt(prompt_path)
    
    try:
        start_msg = f"🚀 **HỆ THỐNG AUTO-TRAINING {version.upper()} KHỞI ĐỘNG** 🚀\n- Mã giao dịch: {symbol}\n- Bắt đầu tiến hành phân tích lịch sử để đưa ra quyết định vòng lặp đầu tiên..."
        subprocess.run([sys.executable, ".agent/send_to_tele.py", start_msg], check=False)
    except Exception as e:
        print(f"Lỗi gửi thông báo khởi động: {e}")
    
    env = dict(os.environ,
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
        PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:32"
    )
    
    decision = get_ai_decision(prompt_path, symbol)
    if not decision:
        print("AI không đưa ra quyết định hợp lệ, mặc định chạy 'asian' để an toàn.")
        target_session = "asian"
        updates = {}
    else:
        target_session = decision.get("target_session", "asian").lower()
        updates = decision.get("config_updates", {})
        
    print(f"\n🎯 QUYẾT ĐỊNH ĐÀO TẠO ĐẦU TIÊN: {target_session.upper()}")
    print(f"🔧 Cập nhật cấu hình: {updates}")
    
    config_src = update_config(target_session, updates, symbol, version, args.start_date, args.end_date, custom_params)
    workspace = f"workspaces/CFG_{symbol}_{target_session.upper()}_{version}"
    run_id = datetime.now().strftime(f"run_%Y%m%d_%H%M%S_{version.lower()}_{target_session}")
    runs_dir = os.path.join(workspace, 'runs')
    os.makedirs(runs_dir, exist_ok=True)
    new_run_dir = os.path.join(runs_dir, run_id)
    os.makedirs(new_run_dir, exist_ok=True)
    config_dst = os.path.join(new_run_dir, 'config.json')

    with open(config_src, 'r', encoding='utf-8') as f:
        config = json.load(f)
    config['HF_RUN_ID'] = run_id
    with open(config_dst, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

    print(f"\n--- [5] LẤY DỮ LIỆU ĐẦU TIÊN (PREPARE DATASET): {target_session.upper()} ---")
    log_prep = os.path.join(new_run_dir, 'prepare_dataset.log')
    with open(log_prep, 'w', encoding='utf-8') as f_log:
        subprocess.run(
            [sys.executable, f'scripts/prepare_{version.lower()}_dataset.py', '--config', config_dst, '--no-upload'],
            env=env, stdout=f_log, stderr=subprocess.STDOUT
        )

    while True:
        print(f"\n--- [6] ĐÀO TẠO (TRAIN_{version}): {target_session.upper()} ---")
        try:
            train_msg = f"🔥 **BẮT ĐẦU HUẤN LUYỆN (TRAIN)** 🔥\n- Phiên: {target_session.upper()}\n- Version: {version}\n- Đã chuẩn bị Data xong, quá trình ép xung nơ-ron chính thức bắt đầu!"
            subprocess.run([sys.executable, ".agent/send_to_tele.py", train_msg], check=False)
        except Exception as e:
            pass
            
        log_train = os.path.join(new_run_dir, f'train_{version.lower()}.log')
        
        train_cmd = [sys.executable, '-u', f'src/training_{version.lower()}/train_{version.lower()}.py', config_dst, '--run-id', run_id, '--scratch', '--session', target_session]
        with open(log_train, 'w', encoding='utf-8') as f_log:
            train_process = subprocess.Popen(train_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
            for line in train_process.stdout:
                f_log.write(line)
                if "Epoch" in line or "[Warm-up]" in line or "[Best]" in line or "composite_score" in line:
                    print(f"  -> [Train Monitor] {line.strip()}")
            train_process.wait()

        print(f"\n--- [NEXT STEP] AI ĐANG PHÂN TÍCH VÀ CHUẨN BỊ CHO PHIÊN TIẾP THEO ---")
        next_decision = get_ai_decision(prompt_path, symbol)
        if not next_decision:
            print("AI không đưa ra quyết định hợp lệ, mặc định chạy 'asian' để an toàn.")
            next_target_session = "asian"
            next_updates = {}
        else:
            next_target_session = next_decision.get("target_session", "asian").lower()
            next_updates = next_decision.get("config_updates", {})
            
        print(f"\n🎯 QUYẾT ĐỊNH ĐÀO TẠO TIẾP THEO SẼ LÀ: {next_target_session.upper()}")
        print(f"🔧 Cập nhật cấu hình: {next_updates}")
        
        next_config_src = update_config(next_target_session, next_updates, symbol, version, args.start_date, args.end_date, custom_params)
        next_workspace = f"workspaces/CFG_{symbol}_{next_target_session.upper()}_{version}"
        import time
        time.sleep(1)
        next_run_id = datetime.now().strftime(f"run_%Y%m%d_%H%M%S_{version.lower()}_{next_target_session}")
        next_runs_dir = os.path.join(next_workspace, 'runs')
        os.makedirs(next_runs_dir, exist_ok=True)
        next_new_run_dir = os.path.join(next_runs_dir, next_run_id)
        os.makedirs(next_new_run_dir, exist_ok=True)
        next_config_dst = os.path.join(next_new_run_dir, 'config.json')

        with open(next_config_src, 'r', encoding='utf-8') as f:
            next_config = json.load(f)
        next_config['HF_RUN_ID'] = next_run_id
        with open(next_config_dst, 'w', encoding='utf-8') as f:
            json.dump(next_config, f, indent=4)

        print(f"\n--- [PRE-FETCH] LẤY DỮ LIỆU: {next_target_session.upper()} ---")
        next_log_prep = os.path.join(next_new_run_dir, 'prepare_dataset.log')
        
        prep_cmd = [sys.executable, f'scripts/prepare_{version.lower()}_dataset.py', '--config', next_config_dst, '--no-upload']
        with open(next_log_prep, 'w', encoding='utf-8') as f_log:
            prep_process = subprocess.Popen(prep_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
            for line in prep_process.stdout:
                f_log.write(line)
                if "Ráp Tensor" in line or "100%" in line:
                    print(f"  -> [Prep Monitor] {line.strip()}")
            prep_process.wait()
        
        print("--- [PRE-FETCH] CHUẨN BỊ XONG. TIẾP TỤC VÒNG LẶP ---")
        
        print(f"\n--- [7] HOÀN TẤT PHIÊN {target_session.upper()} ---")
        subprocess.run([sys.executable, ".agent/notify_done.py", f"{symbol.lower()}_{version.lower()}_training_done"], env=env)
        
        print(f"\n--- [8] DỌN DẸP CÁC RUN CŨ ---")
        cleanup_old_runs(symbol, version, exclude_runs=[run_id, next_run_id], keep_top_n=2)
        
        target_session = next_target_session
        updates = next_updates
        config_src = next_config_src
        run_id = next_run_id
        new_run_dir = next_new_run_dir
        config_dst = next_config_dst

        print("Đợi 10 giây trước khi bắt đầu vòng lặp mới...")
        time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Training Loop")
    parser.add_argument("--symbol", type=str, default="LTC", help="Mã giao dịch (VD: LTC, XAG)")
    parser.add_argument("--version", type=str, default="v6", help="Phiên bản kiến trúc (VD: v6, v5)")
    parser.add_argument("--prompt-file", type=str, default=None, help="Đường dẫn đến file prompt strategy")
    parser.add_argument("--start-date", type=str, default=None, help="Ngày bắt đầu training (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="Ngày kết thúc training (YYYY-MM-DD)")
    parser.add_argument("--custom-params", type=str, default=None, help="JSON chứa các tham số config cần ghi đè")
    
    args = parser.parse_args()
    run_training_loop(args)
