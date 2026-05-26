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
    
    while True:
        # 1 & 2 & 3: AI phân tích và xác định chiến lược
        decision = get_ai_decision()
        if not decision:
            print("AI không đưa ra quyết định hợp lệ, mặc định chạy 'asian' để an toàn.")
            target_session = "asian"
            updates = {}
        else:
            target_session = decision.get("target_session", "asian").lower()
            updates = decision.get("config_updates", {})
            
        print(f"\n🎯 QUYẾT ĐỊNH ĐÀO TẠO TIẾP THEO: {target_session.upper()}")
        print(f"🔧 Cập nhật cấu hình: {updates}")
        
        # 4: Thay đổi thiết lập cấu hình
        print(f"\n--- [4] CẬP NHẬT CONFIG CHO PHIÊN {target_session.upper()} ---")
        config_src = update_config(target_session, updates)
        
        # Setup run folder
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

        # 5: Lấy dữ liệu
        print(f"\n--- [5] LẤY DỮ LIỆU (PREPARE DATASET): {target_session.upper()} ---")
        log_prep = os.path.join(new_run_dir, 'prepare_dataset.log')
        with open(log_prep, 'w', encoding='utf-8') as f_log:
            sp1 = subprocess.run(
                [sys.executable, 'scripts/prepare_v6_dataset.py', '--config', config_dst, '--no-upload'],
                env=env, stdout=f_log, stderr=subprocess.STDOUT
            )
        if sp1.returncode != 0:
            print(f"Error preparing dataset. Lỗi sẽ được gửi qua Tele. Khởi động lại vòng lặp sau 60s...")
            time.sleep(60)
            continue

        # 6: Đào tạo
        print(f"\n--- [6] ĐÀO TẠO (TRAIN_V6): {target_session.upper()} ---")
        log_train = os.path.join(new_run_dir, 'train_v6.log')
        with open(log_train, 'w', encoding='utf-8') as f_log:
            sp2 = subprocess.run(
                [sys.executable, '-u', 'src/training_v6/train_v6.py', config_dst, '--run-id', run_id, '--scratch', '--session', target_session],
                env=env,
                stdout=f_log,
                stderr=subprocess.STDOUT
            )
        
        print(f"\n--- [7] HOÀN TẤT PHIÊN {target_session.upper()} ---")
        subprocess.run([sys.executable, ".agent/notify_done.py", "ltc_v6_training_done"], env=env)
        
        print("Đợi 10 giây trước khi bắt đầu vòng lặp mới...")
        time.sleep(10)

if __name__ == "__main__":
    run_training_loop()
