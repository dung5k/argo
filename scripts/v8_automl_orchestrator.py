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
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_queue(q):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2)

def check_node_running(node):
    """Trả về True nếu python đang chạy script training trên node này"""
    if node == "ARGO1":
        try:
            res = subprocess.run(
                ["powershell", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'v8_training_loop' } | Select-Object ProcessId"],
                capture_output=True, text=True, timeout=5
            )
            return "ProcessId" in res.stdout
        except:
            return False
    else:
        ip = NODES[node]["ip"]
        user = NODES[node]["user"]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=user, key_filename=os.path.expanduser("~/.ssh/id_rsa"), timeout=5)
            stdin, stdout, stderr = client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Where-Object { $_.CommandLine -match \'v8_training_loop\' } | Select-Object ProcessId"')
            out = stdout.read().decode('utf-8', errors='ignore').strip()
            client.close()
            return "ProcessId" in out
        except:
            return False

def kill_node(node):
    """Kill process training trên node"""
    print(f"[{node}] Đang Kill tiến trình...")
    if node == "ARGO1":
        subprocess.run('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Where-Object {$_.CommandLine -match \'v8_training_loop\'} | Invoke-CimMethod -MethodName Terminate"', shell=True)
    else:
        ip = NODES[node]["ip"]
        user = NODES[node]["user"]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=user, key_filename=os.path.expanduser("~/.ssh/id_rsa"), timeout=5)
            client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Where-Object {$_.CommandLine -match \'v8_training_loop\'} | Invoke-CimMethod -MethodName Terminate"')
            client.close()
        except:
            pass

def spawn_task(node, task):
    """Khởi động tiến trình training trên node với cấu hình của task"""
    print(f"[{node}] Đang spawn task {task['id']} (Layers: {task['layers']}, LR: {task['lr']})")
    opt_id = task['id']
    layers = task['layers']
    lr = task['lr']
    
    if node == "ARGO1":
        bat_path = os.path.abspath(f"temp/train_{node}_{opt_id}.bat")
        py_path = os.path.abspath("scripts/v8_training_loop.py")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f'@echo off\nset PYTHONIOENCODING=utf-8\ncd /d "%~dp0\\.."\n"C:\\Users\\GiggaMan\\AppData\\Local\\Programs\\Python\\Python39\\python.exe" "{py_path}" --node_id {node} --layers {layers} --lr {lr} --opt_id {opt_id}\n')
        
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
                py_exe = "D:\\argo\\venv\\Scripts\\python.exe"
            else:
                py_exe = "D:/DungLA/Python39/python.exe"
                
            bat_content = f'@echo off\ncd /d "{remote_base}"\n"{py_exe}" scripts/v8_training_loop.py --node_id {node} --layers {layers} --lr {lr} --opt_id {opt_id} > logs/argo_cmd_{opt_id}.log 2>&1\n'
            
            sftp = client.open_sftp()
            bat_file = f'{remote_base}/auto_{node.lower()}.bat'
            with sftp.file(bat_file, 'w') as f:
                f.write(bat_content)
            sftp.close()
            
            # Using Invoke-WmiMethod for remote spawn because schtasks fails sometimes and wmic is removed in Win11
            client.exec_command(f'powershell -Command "Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList \'cmd /c {bat_file}\'"')
            client.close()
        except Exception as e:
            print(f"[{node}] Lỗi SSH khi spawn: {e}")

def parse_log(node, opt_id):
    """Đọc file log và tính Edge trung bình. Trả về (is_done, splits_done, avg_edge)"""
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
            stdin, stdout, stderr = client.exec_command(f'powershell -Command "Get-Content {remote_base}/{log_file}"')
            raw = stdout.read().decode('utf-8', errors='ignore')
            client.close()
        except:
            pass
            
    if not raw:
        return False, 0, 0.0
        
    is_done = "DA HOAN THANH" in raw
    
    # Tìm tất cả Edge của các split
    edges = []
    is_ep10 = False
    for line in raw.split('\n'):
        if "Ep 10" in line:
            is_ep10 = True
        
        # Chỉ lấy Edge của Threshold 0.22 ở Epoch 10
        if is_ep10 and "Threshold 0.22" in line:
            m = re.search(r'Edge:\s*([+\-]?[\d.]+)%', line)
            if m:
                edges.append(float(m.group(1)))
                is_ep10 = False # reset cho split tiếp theo
                
    if not edges:
        return is_done, 0, 0.0
        
    splits_done = len(edges)
    avg_edge = sum(edges) / len(edges)
    return is_done, splits_done, avg_edge

def main():
    print("Khởi động AutoML Orchestrator...")
    send_tele("🚀 **AUTO-ML ORCHESTRATOR ĐÃ KHỞI ĐỘNG**\nHệ thống bắt đầu tự động điều phối hàng đợi các Option và đánh giá Early Stopping liên tục.")
    
    while True:
        try:
            q = load_queue()
            
            # Thống kê
            running_tasks = [t for t in q if t["status"] == "RUNNING"]
            pending_tasks = [t for t in q if t["status"] == "PENDING"]
            completed = [t for t in q if t["status"] in ["COMPLETED", "FAILED_EARLY"]]
            
            report = []
            report.append("🔄 **AUTO-ML STATUS REPORT**")
            report.append(f"📦 Tổng hàng đợi: {len(q)} (Đang chạy: {len(running_tasks)}, Chờ: {len(pending_tasks)}, Xong: {len(completed)})")
            
            # --- KIỂM TRA TRẠNG THÁI CÁC MÁY ĐANG CHẠY ---
            for task in running_tasks:
                node = task["assigned_node"]
                opt_id = task["id"]
                is_alive = check_node_running(node)
                is_done, splits, avg_edge = parse_log(node, opt_id)
                
                if not is_alive and not is_done:
                    # Chết bất đắc kỳ tử
                    task["status"] = "FAILED"
                    task["reason"] = "Crash/Killed unexpectedly"
                    report.append(f"❌ {opt_id} trên {node} bị CRASH.")
                elif is_done:
                    task["status"] = "COMPLETED"
                    task["score"] = avg_edge
                    report.append(f"✅ {opt_id} trên {node} ĐÃ HOÀN THÀNH. Edge tổng: {avg_edge:+.2f}%")
                else:
                    # Đang chạy, check early stopping
                    report.append(f"▶️ {node} đang cày {opt_id} (Đã xong {splits} splits, Edge TB: {avg_edge:+.2f}%)")
                    if splits >= 5 and avg_edge < -2.0:
                        report.append(f"  👉 CẢNH BÁO: Option này rác! Kích hoạt EARLY STOPPING.")
                        kill_node(node)
                        task["status"] = "FAILED_EARLY"
                        task["reason"] = f"Early stop: Edge {avg_edge:+.2f}% after {splits} splits"
                        
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
                        "layers": random.randint(2, 6),
                        "lr": round(random.uniform(0.0001, 0.001), 5),
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
            active_nodes = [t["assigned_node"] for t in q if t["status"] == "RUNNING"]
            for node in NODES.keys():
                if node not in active_nodes:
                    # Nếu node không được đánh dấu là running, kiểm tra xem nó có thực sự rảnh ko
                    if check_node_running(node):
                        # Node đang chạy một tiến trình (có thể do user manual bật), bỏ qua
                        continue
                        
                    # Tìm task PENDING
                    pending = [t for t in q if t["status"] == "PENDING"]
                    if pending:
                        next_task = pending[0]
                        spawn_task(node, next_task)
                        next_task["status"] = "RUNNING"
                        next_task["assigned_node"] = node
                        report.append(f"🎯 Đã nạp {next_task['id']} vào máy {node}.")
                        active_nodes.append(node)
                        
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
            
        time.sleep(60) # Lặp lại mỗi 1 phút thay vì 5 phút

if __name__ == "__main__":
    main()
