# -*- coding: utf-8 -*-
"""
V8 AutoML Orchestrator - Trình điều phối chạy liên tục các Option
================================================================
Tự động giao việc cho ARGO1, ARGO2, ARGO3. 
Có cơ chế Early Stopping (trảm option tồi).
"""

import os
import sys
import json
import time
import subprocess
import paramiko
import re
import random

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

TELEGRAM_BOT = ".agent/send_to_tele.py"
CHANNEL_ID = "1816854047"
QUEUE_FILE = "v8_configs/automl_queue.json"

NODES = {
    "ARGO1": {"ip": "LOCAL", "user": "desktop-n67bhmu\\giggaman", "remote_base": "D:/DungLA/client1"},
    "ARGO2": {"ip": "192.168.1.18", "user": "dungla", "remote_base": "D:/DungLA/Argo"},
    "ARGO3": {"ip": "192.168.1.16", "user": "dungla", "remote_base": "D:/DungLA/Argo"}
}

def send_tele(msg):
    subprocess.run([sys.executable, TELEGRAM_BOT, msg, "--channel", CHANNEL_ID])

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def get_active_nodes():
    try:
        with open("v8_configs/v8_training_config.json", "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
            return cfg.get("system", {}).get("active_nodes", ["ARGO1", "ARGO2", "ARGO3"])
    except:
        return list(NODES.keys())

def save_queue(q):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2)

def check_node_running(node):
    """Trả về True nếu python đang chạy script training trên node này, False nếu không, None nếu lỗi kết nối"""
    if node == "ARGO1":
        try:
            res = subprocess.run(
                ['python', '-c', "import psutil; print(any(p.info['name'] and 'python' in p.info['name'].lower() and p.info['cmdline'] and ('v8_training_loop' in ' '.join(p.info['cmdline']) or 'v8_train_full' in ' '.join(p.info['cmdline'])) and '-c' not in p.info['cmdline'] for p in psutil.process_iter(['name', 'cmdline'])))"],
                capture_output=True, text=True, timeout=5
            )
            return "True" in res.stdout
        except:
            return None
    else:
        ip = NODES[node]["ip"]
        user = NODES[node]["user"]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=user, key_filename=os.path.expanduser("~/.ssh/id_rsa"), timeout=5)
            if node == "ARGO2":
                remote_py = "C:/argo/venv/Scripts/python.exe"
            else:
                remote_py = "D:/DungLA/Python39/python.exe"
            cmd = f'"{remote_py}" -c "import psutil; print(any(p.info[\'name\'] and \'python\' in p.info[\'name\'].lower() and p.info[\'cmdline\'] and (\'v8_training_loop\' in \' \'.join(p.info[\'cmdline\']) or \'v8_train_full\' in \' \'.join(p.info[\'cmdline\'])) and \'-c\' not in p.info[\'cmdline\'] for p in psutil.process_iter([\'name\', \'cmdline\'])))"'
            stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
            out = stdout.read().decode('utf-8', errors='ignore').strip()
            err_out = stderr.read().decode('utf-8', errors='ignore').strip()
            if err_out:
                with open("logs/orchestrator_debug.log", "a", encoding="utf-8") as lf:
                    lf.write(f"{time.ctime()} - [{node}] Lỗi khi check psutil: {err_out}\n")
            client.close()
            if "ModuleNotFoundError" in err_out or "NameError" in err_out:
                return None
            return "True" in out
        except Exception as e:
            with open("logs/orchestrator_debug.log", "a", encoding="utf-8") as lf:
                lf.write(f"{time.ctime()} - [{node}] Lỗi kết nối SSH khi check: {e}\n")
            return None

def kill_node(node):
    """Kill process training trên node"""
    print(f"[{node}] Đang Kill tiến trình...")
    if node == "ARGO1":
        subprocess.run(['python', '-c', "import psutil; [p.terminate() for p in psutil.process_iter(['name', 'cmdline']) if p.info['name'] and 'python' in p.info['name'].lower() and p.info['cmdline'] and ('v8_training_loop' in ' '.join(p.info['cmdline']) or 'v8_train_full' in ' '.join(p.info['cmdline'])) and '-c' not in p.info['cmdline']]"])
    else:
        ip = NODES[node]["ip"]
        user = NODES[node]["user"]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=user, key_filename=os.path.expanduser("~/.ssh/id_rsa"), timeout=5)
            if node == "ARGO2":
                remote_py = "C:/argo/venv/Scripts/python.exe"
            else:
                remote_py = "D:/DungLA/Python39/python.exe"
            client.exec_command(f'"{remote_py}" -c "import psutil; [p.terminate() for p in psutil.process_iter([\'name\', \'cmdline\']) if p.info[\'name\'] and \'python\' in p.info[\'name\'].lower() and p.info[\'cmdline\'] and (\'v8_training_loop\' in \' \'.join(p.info[\'cmdline\']) or \'v8_train_full\' in \' \'.join(p.info[\'cmdline\'])) and \'-c\' not in p.info[\'cmdline\']]"', timeout=15)
            client.close()
        except Exception as e:
            with open("logs/orchestrator_debug.log", "a", encoding="utf-8") as lf:
                lf.write(f"{time.ctime()} - [{node}] Lỗi SSH khi kill: {e}\n")

def spawn_task(node, task):
    """Khởi động tiến trình training trên node với cấu hình của task"""
    layers = task['layers']
    lr = task['lr']
    opt_id = task['id']
    tf = task.get("base_timeframe", "M5")
    
    print(f"[{node}] Đang spawn task {opt_id} [TF={tf}]...")
    
    if node == "ARGO1":
        bat_path = os.path.abspath(f"temp/train_{node}_{opt_id}.bat")
        py_path = os.path.abspath("scripts/v8_train_full.py")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f'@echo off\nset PYTHONIOENCODING=utf-8\ncd /d "%~dp0\\.."\n"C:\\Users\\GiggaMan\\AppData\\Local\\Programs\\Python\\Python39\\python.exe" "{py_path}" --model brain_{opt_id}_{node}.pt --layers {layers} --lr 1e-5 --epochs 25 --scratch --batch_size 128 --node_id {node} --opt_id {opt_id}\n')
        
        user = NODES[node]["user"]
        cmd = f'schtasks /create /tn "V8_{node}_AutoML" /tr "{bat_path}" /sc once /st 00:00 /ru "{user}" /it /f ; schtasks /run /tn "V8_{node}_AutoML"'
        subprocess.run(["powershell", "-Command", cmd], shell=True)
    else:
        remote_base = NODES[node]["remote_base"]
        ip = NODES[node]["ip"]
        user = NODES[node]["user"]
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=user, key_filename=os.path.expanduser("~/.ssh/id_rsa"), timeout=10)
            
            # Create wrapper bat file on remote
            if node == "ARGO2":
                py_exe = "C:/argo/venv/Scripts/python.exe"
                bs = 32
            else:
                py_exe = "D:/DungLA/Python39/python.exe"
                bs = 64
                
            bat_content = f'@echo off\ncd /d "{remote_base}"\n"{py_exe}" scripts/v8_train_full.py --model brain_{opt_id}_{node}.pt --layers {layers} --lr 1e-5 --epochs 25 --scratch --batch_size {bs} --node_id {node} --opt_id {opt_id}\n'
            
            sftp = client.open_sftp()
            bat_file = f'{remote_base}/auto_{node.lower()}.bat'
            with sftp.file(bat_file, 'w') as f:
                f.write(bat_content)
            sftp.close()
            
            # Using Invoke-WmiMethod for remote spawn because schtasks fails sometimes and wmic is removed in Win11
            client.exec_command(f'powershell -Command "Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList \'cmd /c {bat_file}\'"', timeout=15)
            client.close()
        except Exception as e:
            with open("logs/orchestrator_debug.log", "a", encoding="utf-8") as lf:
                lf.write(f"{time.ctime()} - [{node}] Lỗi SSH khi spawn: {e}\n")

def parse_log(node, opt_id):
    """Đọc file log của v8_train_full.py. Trả về (is_done, epochs_done, total_epochs, last_loss)"""
    log_file = f"logs/v8_train_{node}_{opt_id}.log"
    raw = ""
    if node == "ARGO1":
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                raw = f.read()
    else:
        ip = NODES[node]["ip"]
        user = NODES[node]["user"]
        remote_base = NODES[node]["remote_base"]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=user, key_filename=os.path.expanduser("~/.ssh/id_rsa"), timeout=5)
            stdin, stdout, stderr = client.exec_command(f'powershell -Command "Get-Content {remote_base}/{log_file}"', timeout=15)
            raw = stdout.read().decode('utf-8', errors='ignore')
            client.close()
        except:
            pass
            
    if not raw:
        return False, 0, 25, 0.0
        
    is_done = "FULL_TRAIN_DONE" in raw
    
    # Parse total epochs from "Starting training for X epochs"
    total_epochs = 25
    m_total = re.search(r'Starting training for (\d+) epochs', raw)
    if m_total:
        total_epochs = int(m_total.group(1))
    
    # Parse completed epochs: "==> Epoch X/Y Completed | Average Loss: Z"
    epoch_losses = []
    for line in raw.split('\n'):
        m = re.search(r'Epoch (\d+)/(\d+) Completed \| Average Loss: ([\d.]+)', line)
        if m:
            epoch_losses.append(float(m.group(3)))
                
    epochs_done = len(epoch_losses)
    last_loss = epoch_losses[-1] if epoch_losses else 0.0
    return is_done, epochs_done, total_epochs, last_loss

def main():
    print("Khởi động AutoML Orchestrator...")
    send_tele("🚀 **AUTO-ML ORCHESTRATOR ĐÃ KHỞI ĐỘNG**\nHệ thống bắt đầu tự động điều phối hàng đợi các Option và đánh giá Early Stopping liên tục.")
    
    while True:
        try:
            q = load_queue()
            active_nodes = get_active_nodes()
            
            # Thống kê
            running_tasks = [t for t in q if t["status"] == "RUNNING"]
            pending_tasks = [t for t in q if t["status"] == "PENDING"]
            completed = [t for t in q if t["status"] in ["COMPLETED", "FAILED_EARLY"]]
            
            report = []
            
            report.append("🌟 **AUTO-ML STATUS REPORT**")
            report.append(f"📊 Tổng hàng đợi: {len(q)} (Đang chạy: {len(running_tasks)}, Chờ: {len(pending_tasks)}, Xong: {len(completed)})")
            report.append(f"🟢 Nodes kích hoạt: {', '.join(active_nodes)}")
            
            # --- KIỂM TRA TRẠNG THÁI CÁC MÁY ĐANG CHẠY ---
            assigned_nodes = [t["assigned_node"] for t in running_tasks if t.get("assigned_node")]
            for task in running_tasks:
                node = task["assigned_node"]
                if node not in active_nodes:
                    continue
                opt_id = task["id"]
                tf = task.get("base_timeframe", "M5")
                is_alive = check_node_running(node)
                
                if is_alive is None:
                    # SSH/Lỗi kết nối hoặc lỗi môi trường, không phán xét, skip qua
                    report.append(f"⚠️ {node} mất kết nối hoặc lỗi kiểm tra. Đang tạm bỏ qua.")
                    continue
                    
                is_done, epochs_done, total_epochs, last_loss = parse_log(node, opt_id)
                
                if not is_alive and not is_done:
                    # Chết bất đắc kỳ tử
                    task["status"] = "FAILED"
                    task["reason"] = "Crash/Killed unexpectedly"
                    report.append(f"💀 {opt_id} [{tf}] trên {node} bị CRASH. | Số lớp: {task['layers']} | LR: {task['lr']}")
                elif is_done:
                    task["status"] = "COMPLETED"
                    task["score"] = last_loss
                    report.append(f"✅ {opt_id} [{tf}] trên {node} XONG ({epochs_done}/{total_epochs} epochs). Loss: {last_loss:.4f} | Số lớp: {task['layers']}")
                else:
                    # Đang chạy
                    if epochs_done > 0:
                        report.append(f"⚡ {node} đang cày {opt_id} [{tf}] (Epoch {epochs_done}/{total_epochs}, Loss: {last_loss:.4f}) | Số lớp: {task['layers']}")
                    else:
                        report.append(f"⏳ {node} đang khởi tạo {opt_id} [{tf}] (Đang nạp dữ liệu...) | Số lớp: {task['layers']}")
                        
            # Thêm báo cáo cho các máy đang bận cày tay (không nằm trong queue)
            for node in active_nodes:
                if node in NODES and node not in assigned_nodes:
                    is_alive = check_node_running(node)
                    if is_alive:
                        report.append(f"🔥 {node} đang bận cày tay (Manual Training / Full Train) ngoài hệ thống AutoML.")
                        
            # --- TỰ ĐỘNG BƠM THÊM NHIỆM VỤ NẾU CẠN KIỆT ---
            if len(pending_tasks) == 0:
                report.append("⏳ Hàng đợi trống! Đang tự động sinh thêm 10 cấu hình mới...")
                last_id = 0
                if q:
                    last_task = q[-1]["id"]
                    if last_task.startswith("OPT-"):
                        try:
                            last_id = int(last_task.split("-")[1])
                        except:
                            pass
                
                for i in range(1, 11):
                    new_opt = {
                        "id": f"OPT-{last_id + i}",
                        "layers": random.randint(4, 7),
                        "lr": round(random.uniform(0.00005, 0.00030), 5),
                        "base_timeframe": random.choice(["M5", "M15"]),
                        "status": "PENDING",
                        "assigned_node": None,
                        "score": None,
                        "reason": None
                    }
                    q.append(new_opt)
                    pending_tasks.append(new_opt)
                save_queue(q)
                report.append(f"✅ Đã nạp thành công 10 cấu hình tiếp theo (OPT-{last_id+1} đến OPT-{last_id+10}).")

            # --- PHÂN BỔ VIỆC CHO MÁY RẢNH ---
            pending_tasks = [t for t in q if t["status"] == "PENDING"]
            for node in active_nodes:
                if node in NODES:
                    is_alive = check_node_running(node)
                    if is_alive == False:  # Chỉ phân công nếu node thực sự kết nối được và rảnh
                        if pending_tasks:
                            task = pending_tasks.pop(0)
                            task["status"] = "RUNNING"
                            task["assigned_node"] = node
                            spawn_task(node, task)
                            report.append(f"🎯 Đã nạp {task['id']} vào máy {node}.")
                        
            # Cập nhật lại Queue
            save_queue(q)
            
            # Gửi báo cáo
            send_tele('\n'.join(report))
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Lỗi Orchestrator: {e}\n{error_trace}")
            with open("logs/orchestrator_crash.log", "a", encoding="utf-8") as f:
                f.write(f"{time.ctime()} - Lỗi Orchestrator: {e}\n{error_trace}\n")
            
        time.sleep(180) # Lặp lại mỗi 3 phút thay vì 1 phút

if __name__ == "__main__":
    main()
