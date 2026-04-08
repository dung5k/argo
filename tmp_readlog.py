import os, glob

log_dir = r"clientEW/logs"
try:
    if not os.path.exists(log_dir):
        print(f"Khong co thu muc log {log_dir}")
    else:
        logs = glob.glob(os.path.join(log_dir, "*train.log"))
        if not logs:
            print("Khong co file log train nao!")
        else:
            latest = max(logs, key=os.path.getctime)
            print(f"=== LOG: {latest} ===")
            with open(latest, "r", encoding="utf-8") as f:
                lines = f.readlines()
                print("".join(lines[-30:]))
                
            print("\n=== SYSTEM LOG ===")
            sys_logs = glob.glob(os.path.join(log_dir, "tg_agent*.log"))
            if sys_logs:
                latest_sys = max(sys_logs, key=os.path.getctime)
                with open(latest_sys, "r", encoding="utf-8") as f:
                    print("".join(f.readlines()[-30:]))
                    
except Exception as e:
    print(f"Loi: {e}")
