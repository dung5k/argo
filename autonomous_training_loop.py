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
import platform
import requests

def run_and_tee(cmd, log_path, env):
    with open(log_path, 'wb') as f_log:
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            chunk = process.stdout.read1(1024) if hasattr(process.stdout, 'read1') else process.stdout.read(1)
            if not chunk:
                break
            f_log.write(chunk)
            f_log.flush()
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        process.wait()
        return process.returncode

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

_global_lock_file = None

def check_single_instance(symbol):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lock_dir_path = os.path.join(script_dir, f"autonomous_training_{symbol.lower()}.lockdir")
    pid_file_path = os.path.join(lock_dir_path, "pid.txt")
    
    try:
        # os.mkdir là hoạt động nguyên tử cấp độ OS chống Race Condition
        os.mkdir(lock_dir_path)
        with open(pid_file_path, "w") as f:
            f.write(str(os.getpid()))
            
        import atexit
        def cleanup_lock():
            try:
                if os.path.exists(pid_file_path):
                    os.remove(pid_file_path)
                os.rmdir(lock_dir_path)
            except Exception:
                pass
        atexit.register(cleanup_lock)
        
    except FileExistsError:
        # Nếu thư mục lock tồn tại, kiểm tra xem tiến trình cũ có thực sự đang chạy
        if os.path.exists(pid_file_path):
            try:
                with open(pid_file_path, "r") as f:
                    old_pid = int(f.read().strip())
                # Kiểm tra trạng thái PID trên Windows
                output = subprocess.check_output(f'tasklist /FI "PID eq {old_pid}" /FO CSV', shell=True).decode('utf-8')
                if str(old_pid) in output:
                    print(f"[LOCK] Khong the lay lock cho {symbol.upper()}. Tien trinh khac dang chay voi PID={old_pid}. Tu dong thoat!", flush=True)
                    sys.exit(0)
            except Exception:
                pass
        
        # Nếu tiến trình cũ đã chết (orphan lock), dọn dẹp và lấy lại lock
        try:
            if os.path.exists(pid_file_path):
                os.remove(pid_file_path)
            if os.path.exists(lock_dir_path):
                os.rmdir(lock_dir_path)
            
            os.mkdir(lock_dir_path)
            with open(pid_file_path, "w") as f:
                f.write(str(os.getpid()))
                
            import atexit
            def cleanup_lock():
                try:
                    if os.path.exists(pid_file_path):
                        os.remove(pid_file_path)
                    os.rmdir(lock_dir_path)
                except Exception:
                    pass
            atexit.register(cleanup_lock)
        except Exception:
            print(f"[LOCK] Khong the lay lock cho {symbol.upper()}. Tu dong thoat!", flush=True)
            sys.exit(0)

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
        # Luu lich su quyet dinh
        import datetime
        history_file = os.path.join("workspaces", f"ai_decision_history_{symbol}.json")
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                pass
        
        decision_record = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "decision": decision
        }
        history.append(decision_record)
        # Giu lai toi da 10 quyet dinh gan nhat de prompt khong qua dai
        history = history[-10:]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
            
        return decision
    except json.JSONDecodeError as e:
        print("Lỗi parse JSON:", e)
        return None

def update_config(session_name, updates, symbol, version, start_date, end_date, custom_params_dict):
    # Support both root config format (v6) and data/ format (v5)
    config_file_v6 = f"bot_config_{version.lower()}_{symbol.lower()}_{session_name}.json"
    config_file_v5 = f"data/bot_config_{symbol.lower()}_{session_name}_{version.lower()}.json"
    
    config_file = config_file_v6
    if os.path.exists(config_file_v6):
        config_file = config_file_v6
    elif os.path.exists(config_file_v5):
        config_file = config_file_v5
        
    if not os.path.exists(config_file):
        print(f"Không tìm thấy file config nào (đã check {config_file_v6} và {config_file_v5})")
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
    check_single_instance(symbol)
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
    prep_script = f"scripts/prepare_{version.lower()}_dataset.py"
    if not os.path.exists(prep_script) and version.lower() == "v5":
        prep_script = "scripts/upload_v3_dataset.py"
    prep_args = [sys.executable, prep_script, '--config', config_dst]
    if version.lower() == "v5":
        prep_args.extend(['--no-push', '--run-id', run_id])
    else:
        prep_args.extend(['--no-upload', '--weekly-split'])
    ret_prep = run_and_tee(prep_args, log_prep, env)
    if ret_prep != 0:
        err_msg = f"❌ **LỖI NGHIÊM TRỌNG** ❌\n- Mã giao dịch: {symbol}\n- Quá trình chuẩn bị dữ liệu (Prepare Dataset) thất bại. Bot tạm dừng để kiểm tra!"
        subprocess.run([sys.executable, ".agent/send_to_tele.py", err_msg], check=False)
        sys.exit(ret_prep)

    while True:
        print(f"\n--- [6] ĐÀO TẠO (TRAIN_{version}): {target_session.upper()} ---")
        try:
            train_msg = f"🔥 **BẮT ĐẦU HUẤN LUYỆN (TRAIN)** 🔥\n- Phiên: {target_session.upper()}\n- Version: {version}\n- Đã chuẩn bị Data xong, quá trình ép xung nơ-ron chính thức bắt đầu!"
            subprocess.run([sys.executable, ".agent/send_to_tele.py", train_msg], check=False)
        except Exception as e:
            pass
            
        log_train = os.path.join(new_run_dir, f'train_{version.lower()}.log')
        # Gọi hệ thống train
        train_script = f"src/training_{version.lower()}/train_{version.lower()}.py"
        if not os.path.exists(train_script) and version.lower() == "v5":
            train_script = "src/training_v3/train_v3.py"
            
        train_cmd = [sys.executable, '-u', train_script, config_dst, '--run-id', run_id, '--scratch', '--session', target_session]
        ret_train = run_and_tee(train_cmd, log_train, env)
        if ret_train != 0:
            err_msg = f"❌ **LỖI NGHIÊM TRỌNG** ❌\n- Mã giao dịch: {symbol}\n- Quá trình huấn luyện (Train) thất bại. Bot tạm dừng để kiểm tra!"
            subprocess.run([sys.executable, ".agent/send_to_tele.py", err_msg], check=False)
            sys.exit(ret_train)

        print(f"\n--- [EVALUATE & SIMULATE] KIỂM TRA NGƯỠNG CHO {target_session.upper()} ---")
        try:
            eval_cmd = [
                sys.executable, f"scripts/simulate_{symbol.lower()}.py",
                "--config", config_dst,
                "--symbol", symbol,
                "--force-cpu",
                "--run-id", run_id
            ]
            log_eval = os.path.join(new_run_dir, 'evaluate.log')
            run_and_tee(eval_cmd, log_eval, env)
        except Exception as e:
            print(f"Lỗi khi chạy Evaluate & Simulate: {e}")

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
        
        prep_script = f"scripts/prepare_{version.lower()}_dataset.py"
        if not os.path.exists(prep_script) and version.lower() == "v5":
            prep_script = "scripts/upload_v3_dataset.py"
        prep_args = [sys.executable, prep_script, '--config', next_config_dst]
        if version.lower() == "v5":
            prep_args.extend(['--no-push', '--run-id', f"{run_id}_next"])
        else:
            prep_args.extend(['--no-upload', '--weekly-split'])
        ret_next_prep = run_and_tee(prep_args, next_log_prep, env)
        if ret_next_prep != 0:
            err_msg = f"❌ **LỖI NGHIÊM TRỌNG** ❌\n- Mã giao dịch: {symbol}\n- Quá trình chuẩn bị dữ liệu (Pre-fetch) thất bại. Bot tạm dừng để kiểm tra!"
            subprocess.run([sys.executable, ".agent/send_to_tele.py", err_msg], check=False)
            sys.exit(ret_next_prep)
        
        print("--- [PRE-FETCH] CHUẨN BỊ XONG. TIẾP TỤC VÒNG LẶP ---")
        
        print(f"\n--- [7] HOÀN TẤT PHIÊN {target_session.upper()} ---")
        subprocess.run([sys.executable, ".agent/notify_done.py", f"{symbol.lower()}_{version.lower()}_training_done"], env=env)
        
        print(f"\n--- [8] DỌN DẸP CÁC RUN CŨ ---")
        # cleanup_old_runs(symbol, version, exclude_runs=[run_id, next_run_id], keep_top_n=2)
        print("Đã tắt dọn dẹp theo yêu cầu để giữ lại toàn bộ tiến trình đào tạo.")
        
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
