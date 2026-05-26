import os
import sys
import json
import time
import urllib.request
import urllib.error
import re
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def get_telegram_config():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id_str = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    if not token or not chat_id_str:
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            settings_path = os.path.join(project_root, '.vscode', 'settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not token:
                    m = re.search(r'"antigravityBridge\.teleBotToken"\s*:\s*"([^"]+)"', content)
                    if m: token = m.group(1)
                if not chat_id_str:
                    m = re.search(r'"antigravityBridge\.whitelistChatIds"\s*:\s*"([^"]+)"', content)
                    if m: chat_id_str = m.group(1)
        except Exception as e:
            print(f"Error reading config: {e}", file=sys.stderr)
            
    return token, chat_id_str

def send_telegram_message(token, chat_id, text):
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        import ssl
        ssl_context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            return True
    except Exception as e:
        print(f"[CẢNH BÁO] Không thể gửi tin nhắn Telegram: {e}")
        return False

def main():
    token, chat_id_str = get_telegram_config()
    
    if not token:
        print("Lỗi: Không tìm thấy TELEGRAM_BOT_TOKEN trong cấu hình.", flush=True)
        return
        
    whitelist = [str(c).strip() for c in chat_id_str.split(',')] if chat_id_str else []
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    offset_file = os.path.join(current_dir, 'telegram_offset.txt')
    tasks_file = os.path.join(current_dir, 'tasks.json')
    
    offset = 0
    if os.path.exists(offset_file):
        try:
            with open(offset_file, 'r') as f:
                offset = int(f.read().strip())
        except:
            pass

    print(f"Đang lắng nghe tin nhắn Telegram và quản lý tasks.json... (Offset: {offset})", flush=True)
    
    while True:
        try:
            # 1. Quét tin nhắn mới từ Telegram
            url = f'https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=10'
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=15) as response:
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
                            
                            with open(offset_file, 'w') as f:
                                f.write(str(offset))
                                
                            if text.strip().lower() == '/restart':
                                print("[SYSTEM] Nhận lệnh /restart từ Telegram, đang thoát (code 99)...", flush=True)
                                send_telegram_message(token, chat_id, "🔄 Đang khởi động lại App Cầu Nối theo lệnh của sếp...")
                                sys.exit(99)
                                
                            # ĐỌC VÀ GHI VÀO TASKS.JSON
                            tasks = []
                            if os.path.exists(tasks_file):
                                try:
                                    with open(tasks_file, 'r', encoding='utf-8') as f:
                                        tasks = json.load(f)
                                except:
                                    pass
                                    
                            tasks.append({
                                'task_id': update_id,
                                'status': 'pending',
                                'prompt': text,
                                'chat_id': chat_id,
                                'reply_message': '',
                                'reply_status': 'pending',
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            with open(tasks_file, 'w', encoding='utf-8') as f:
                                json.dump(tasks, f, ensure_ascii=False, indent=2)
                                
                            print(f"[TELEGRAM_INBOX] Đã lưu yêu cầu của Sếp vào tasks.json! AI sẽ xử lý ngay lập tức.", flush=True)
                            
                            # Bắn tin nhắn phản hồi ngay lập tức cho Sếp biết
                            send_telegram_message(token, chat_id, "Đã nhận lệnh.")
                            
                        else:
                            with open(offset_file, 'w') as f:
                                f.write(str(offset))
                                
        except urllib.error.URLError as e:
            pass # Timeout or network error, ignore and continue checking tasks
        except Exception as e:
            with open(os.path.join(current_dir, 'listener_debug.log'), 'a', encoding='utf-8') as lf:
                lf.write(f"[ERROR] Exception in getUpdates: {e}\n")
            time.sleep(2)
            
        # 2. Kiểm tra tasks.json để trả lời tin nhắn từ AI
        try:
            if os.path.exists(tasks_file):
                tasks_modified = False
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                    
                for t in tasks:
                    if t.get('status') == 'completed' and t.get('reply_status') == 'pending':
                        reply = t.get('reply_message')
                        chat_id = t.get('chat_id') or whitelist[0] if whitelist else None
                        if reply and chat_id:
                            success = send_telegram_message(token, chat_id, f"🤖 Argo2:\n{reply}")
                            if success:
                                t['reply_status'] = 'sent'
                                tasks_modified = True
                                print(f"[TELEGRAM_OUTBOX] Đã trả lời Sếp thành công tác vụ {t.get('task_id')}", flush=True)
                        else:
                            t['reply_status'] = 'ignored'
                            tasks_modified = True
                            
                if tasks_modified:
                    with open(tasks_file, 'w', encoding='utf-8') as f:
                        json.dump(tasks, f, ensure_ascii=False, indent=2)
                        
        except Exception as e:
            with open(os.path.join(current_dir, 'listener_debug.log'), 'a', encoding='utf-8') as lf:
                lf.write(f"[ERROR] Exception checking tasks: {e}\n")
                
        time.sleep(1)

if __name__ == "__main__":
    main()
