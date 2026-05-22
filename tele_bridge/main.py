import json
import time
import os
import urllib.request
import urllib.parse
from datetime import datetime
from auto_clicker import AutoClicker

# Determine paths dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[-] Loi doc {CONFIG_PATH}: {e}")
        exit(1)

def send_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"[-] Loi gui tin nhan: {e}")

def get_absolute_tasks_path(tasks_path_str):
    if os.path.isabs(tasks_path_str):
        return tasks_path_str
    return os.path.normpath(os.path.join(BASE_DIR, tasks_path_str))

def main():
    print("[+] Telegram Bridge & Auto Clicker dang chay...")
    
    config = load_config()
    tg_config = config.get("telegram", {})
    BOT_TOKEN = tg_config.get("bot_token")
    ALLOWED_CHAT_IDS = tg_config.get("allowed_chat_ids", [])
    TASKS_PATH = get_absolute_tasks_path(tg_config.get("tasks_file", "../.agent/tasks.json"))

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("[-] Vui long cau hinh bot_token trong config.json")
        exit(1)
        
    print(f"[+] Theo doi file tasks tai: {TASKS_PATH}")
    
    # Khoi chay luong Auto-Clicker ngam
    try:
        tmpl_dir = os.path.join(BASE_DIR, "templates")
        clicker = AutoClicker(CONFIG_PATH, tmpl_dir)
        clicker.start()
    except Exception as e:
        print(f"[-] Khong the khoi dong Auto-Clicker: {e}")

    print("[+] Vui long nhan lenh qua Telegram cho Bot.")
    
    offset = 0
    while True:
        # Kiem tra phan hoi tu IDE trong tasks.json
        try:
            if os.path.exists(TASKS_PATH):
                with open(TASKS_PATH, "r", encoding="utf-8") as f:
                    task_data = json.load(f)
                
                tasks = task_data if isinstance(task_data, list) else [task_data]
                changed = False
                new_tasks = []
                now = datetime.now()

                for task in tasks:
                    if task.get("status") == "completed" and task.get("reply_status") == "pending":
                        reply_msg = task.get("reply_message", "")
                        chat_id = task.get("chat_id")
                        
                        if reply_msg and chat_id:
                            print(f"[+] Gui phan hoi tu IDE toi Tele...")
                            send_message(BOT_TOKEN, chat_id, reply_msg)
                        
                        task["reply_status"] = "sent"
                        changed = True

                    # Kiem tra xem co nen xoa task khong
                    keep = True
                    if task.get("status") == "completed" and task.get("reply_status") == "sent":
                        keep = False # xoa task da gui phan hoi
                    
                    if task.get("status") == "completed":
                        ts_str = task.get("timestamp", "")
                        if ts_str:
                            try:
                                ts = datetime.fromisoformat(ts_str)
                                if (now - ts).total_seconds() > 7200: # qua 2 tieng thi xoa
                                    keep = False
                            except:
                                pass
                                
                    if keep:
                        new_tasks.append(task)
                    else:
                        changed = True

                if changed:
                    with open(TASKS_PATH, "w", encoding="utf-8") as f:
                        json.dump(new_tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass # Bo qua loi doc/ghi file tam thoi

        # Lang nghe tin nhan moi
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    chat_id = chat.get("id")
                    
                    if chat_id in ALLOWED_CHAT_IDS:
                        text = message.get("text", "")
                        if text:
                            print(f"\n[+] Nhan lenh moi tu Tele: {text}")
                            
                            task_data = {
                                "task_id": update["update_id"],
                                "status": "pending",
                                "prompt": text,
                                "chat_id": chat_id,
                                "reply_message": "",
                                "reply_status": "sent",
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            current_tasks = []
                            if os.path.exists(TASKS_PATH):
                                try:
                                    with open(TASKS_PATH, "r", encoding="utf-8") as f:
                                        d = json.load(f)
                                        current_tasks = d if isinstance(d, list) else [d]
                                except:
                                    pass
                            
                            current_tasks.append(task_data)

                            with open(TASKS_PATH, "w", encoding="utf-8") as f:
                                json.dump(current_tasks, f, ensure_ascii=False, indent=2)
                                
                            print("[+] Da ghi vao tasks.json! Doi IDE thuc day de xu ly...")
                            send_message(BOT_TOKEN, chat_id, f"✅ Da tiep nhan lenh: '{text}'.\n\nHe thong se xu ly trong vai phut toi.")
                    else:
                        print(f"[-] Bo qua tin nhan tu Chat ID khong duoc phep: {chat_id}")
                        
        except urllib.error.URLError as e:
            time.sleep(2)
        except Exception as e:
            print(f"[-] Loi mang/he thong: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
