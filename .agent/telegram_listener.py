import os
import sys
import json
import time
import urllib.request
import urllib.error
import re

import ssl

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Bỏ qua xác thực SSL (Fix lỗi tự ký SSL certificate của Windows/Antivirus)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

def get_telegram_config():
    token = ""
    chat_id_str = ""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        settings_path = os.path.join(project_root, '.vscode', 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                content = f.read()
            m = re.search(r'"antigravityBridge\.teleBotToken"\s*:\s*"([^"]+)"', content)
            if m: token = m.group(1)
            m = re.search(r'"antigravityBridge\.whitelistChatIds"\s*:\s*"([^"]+)"', content)
            if m: chat_id_str = m.group(1)
    except Exception as e:
        print(f"Error reading config: {e}", file=sys.stderr)
        
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not chat_id_str:
        chat_id_str = os.environ.get("TELEGRAM_CHAT_ID", "")
        
    return token, chat_id_str

def main():
    token, chat_id_str = get_telegram_config()
    
    if not token:
        print("Lỗi: Không tìm thấy TELEGRAM_BOT_TOKEN trong cấu hình.", flush=True)
        return
        
    whitelist = [c.strip() for c in chat_id_str.split(',')] if chat_id_str else []
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    offset_file = os.path.join(current_dir, 'telegram_offset.txt')
    offset = 0
    if os.path.exists(offset_file):
        try:
            with open(offset_file, 'r') as f:
                offset = int(f.read().strip())
        except:
            pass

    print(f"Đang lắng nghe tin nhắn... (Offset: {offset})", flush=True)
    
    while True:
        try:
            url = f'https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30'
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=35) as response:
                body = response.read().decode('utf-8')
                data = json.loads(body)
                
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        update_id = update['update_id']
                        offset = max(offset, update_id + 1)
                        
                        message = update.get('message')
                        if message and 'text' in message:
                            chat_id = str(message['chat']['id'])
                            text = message['text']
                            name = message['chat'].get('first_name', 'User')
                            
                            if chat_id not in whitelist:
                                print(f"[CẢNH BÁO] Nhận tin nhắn từ Chat ID chưa Whitelist: {chat_id} (Tên: {name}) | Nội dung: {text}", flush=True)
                                with open(offset_file, 'w') as f:
                                    f.write(str(offset))
                                continue
                            
                            # Cập nhật offset để lần sau không đọc lại tin nhắn này
                            with open(offset_file, 'w') as f:
                                f.write(str(offset))
                                
                            # Nếu là lệnh /sn, chạy trực tiếp không cần đánh thức agent
                            if text.strip().lower() in ['/sn', '/screenshot']:
                                print(f"Đã nhận lệnh {text.strip()} từ {name}. Đang chụp màn hình và gửi lại...", flush=True)
                                import subprocess
                                send_tele_path = os.path.join(current_dir, "send_to_tele.py")
                                subprocess.run([sys.executable, send_tele_path, f"📷 Ảnh màn hình được yêu cầu bởi {name}", "--target", chat_id, "--screenshot"])
                                continue
                            
                            # IN RA VÀ LẬP TỨC THOÁT (EXIT) ĐỂ ĐÁNH THỨC ANTIGRAVITY
                            print(f"\n[TELEGRAM_MESSAGE_RECEIVED]", flush=True)
                            print(f"User: {name}", flush=True)
                            print(f"ID: {chat_id}", flush=True)
                            print(f"Message: {text}", flush=True)
                            print(f"\n[AI_MANDATORY_ACTIONS]", flush=True)
                            print(f"1. Gửi ack ngay: python .agent/send_to_tele.py \"⚡ Đang xử lý...\"", flush=True)
                            print(f"2. Xử lý yêu cầu.", flush=True)
                            print(f"3. Gửi kết quả: python .agent/send_to_tele.py \"[kết quả]\" --done", flush=True)
                            print(f"4. Restart: python -u .agent/telegram_listener.py", flush=True)
                            sys.exit(0)
                        else:
                            # Không phải tin nhắn text, vẫn update offset
                            with open(offset_file, 'w') as f:
                                f.write(str(offset))
                            
        except urllib.error.URLError:
            time.sleep(3)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
