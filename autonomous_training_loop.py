import subprocess
import os
import sys
import time
from datetime import datetime
import json
import importlib.util

# 1. Update strategy prompt to ask for JSON output
prompt_path = os.path.join(".agent", "strategy_prompt_LTC.md")
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

def get_ai_decision():
    print("--- [1] TỔNG HỢP BÁO CÁO VÀ GỌI AI ---")
    # Run skill_training_report.py to get the report
    try:
        report_output = subprocess.check_output(
            [sys.executable, ".agent/skill_training_report.py", "--prompt-file", prompt_path, "--symbol", "LTC"],
            env=os.environ,
            text=True,
            encoding="utf-8"
        )
    except subprocess.CalledProcessError as e:
        print("Lỗi khi gọi AI:", e.output)
        return None
    
    print(report_output)
    
    # Parse JSON from AI output
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

def update_config(session_name, updates):
    config_file = f"bot_config_v6_ltc_{session_name}.json"
    if not os.path.exists(config_file):
        print(f"Không tìm thấy file config {config_file}")
        return config_file
        
    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    for k, v in updates.items():
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

def run_training_loop():
    env = dict(os.environ,
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
        PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:32",
        FORCE_CPU="0"
    )
    
    # --- KHỞI TẠO VÒNG LẶP ĐẦU TIÊN ---
    decision = get_ai_decision()
    if not decision:
        print("AI không đưa ra quyết định hợp lệ, mặc định chạy 'asian' để an toàn.")
        target_session = "asian"
        updates = {}
    else:
        target_session = decision.get("target_session", "asian").lower()
        updates = decision.get("config_updates", {})
        
    print(f"\n🎯 QUYẾT ĐỊNH ĐÀO TẠO ĐẦU TIÊN: {target_session.upper()}")
    print(f"🔧 Cập nhật cấu hình: {updates}")
    
    config_src = update_config(target_session, updates)
    workspace = f"workspaces/CFG_LTC_{target_session.upper()}_V6"
    run_id = datetime.now().strftime(f"run_%Y%m%d_%H%M%S_v6_{target_session}")
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
            [sys.executable, 'scripts/prepare_v6_dataset.py', '--config', config_dst, '--no-upload'],
            env=env, stdout=f_log, stderr=subprocess.STDOUT
        )

    # VÒNG LẶP CHÍNH
    while True:
        # Bắt đầu training cho phiên hiện tại (chạy ngầm background process)
        print(f"\n--- [6] ĐÀO TẠO (TRAIN_V6): {target_session.upper()} ---")
        log_train = os.path.join(new_run_dir, 'train_v6.log')
        f_train_log = open(log_train, 'w', encoding='utf-8')
        train_process = subprocess.Popen(
            [sys.executable, '-u', 'src/training_v6/train_v6.py', config_dst, '--run-id', run_id, '--scratch', '--session', target_session],
            env=env,
            stdout=f_train_log,
            stderr=subprocess.STDOUT
        )

        # TRONG KHI ĐANG TRAINING: Phân tích AI và chuẩn bị dữ liệu cho phiên TIẾP THEO
        print(f"\n--- [PRE-FETCH] AI ĐANG PHÂN TÍCH VÀ CHUẨN BỊ CHO PHIÊN TIẾP THEO TRONG KHI ĐANG TRAIN ---")
        next_decision = get_ai_decision()
        if not next_decision:
            print("AI không đưa ra quyết định hợp lệ, mặc định chạy 'asian' để an toàn.")
            next_target_session = "asian"
            next_updates = {}
        else:
            next_target_session = next_decision.get("target_session", "asian").lower()
            next_updates = next_decision.get("config_updates", {})
            
        print(f"\n🎯 QUYẾT ĐỊNH ĐÀO TẠO TIẾP THEO SẼ LÀ: {next_target_session.upper()}")
        print(f"🔧 Cập nhật cấu hình: {next_updates}")
        
        next_config_src = update_config(next_target_session, next_updates)
        next_workspace = f"workspaces/CFG_LTC_{next_target_session.upper()}_V6"
        next_run_id = datetime.now().strftime(f"run_%Y%m%d_%H%M%S_v6_{next_target_session}")
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
        with open(next_log_prep, 'w', encoding='utf-8') as f_prep_log:
            subprocess.run(
                [sys.executable, 'scripts/prepare_v6_dataset.py', '--config', next_config_dst, '--no-upload'],
                env=env, stdout=f_prep_log, stderr=subprocess.STDOUT
            )
        print("--- [PRE-FETCH] CHUẨN BỊ XONG. ĐỢI TIẾN TRÌNH TRAIN HIỆN TẠI KẾT THÚC ---")

        # Đợi training hiện tại hoàn tất
        train_process.wait()
        f_train_log.close()
        
        print(f"\n--- [7] HOÀN TẤT PHIÊN {target_session.upper()} ---")
        subprocess.run([sys.executable, ".agent/notify_done.py", "ltc_v6_training_done"], env=env)
        
        # Chuyển đổi trạng thái: dữ liệu tiếp theo trở thành dữ liệu hiện tại
        target_session = next_target_session
        updates = next_updates
        config_src = next_config_src
        run_id = next_run_id
        new_run_dir = next_new_run_dir
        config_dst = next_config_dst

        print("Đợi 10 giây trước khi bắt đầu vòng lặp mới...")
        time.sleep(10)

if __name__ == "__main__":
    run_training_loop()
