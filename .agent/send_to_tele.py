import sys
import json
import urllib.request
import urllib.error
import os

def get_bridge_port():
    port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bridge_port")
    try:
        if os.path.exists(port_file):
            with open(port_file, "r") as f:
                return int(f.read().strip())
    except:
        pass
    return None

def get_telegram_config(target_channels=None):
    token = ""
    default_chat_id = ""
    try:
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(agent_dir)
        settings_path = os.path.join(project_root, '.vscode', 'settings.json')
        if os.path.exists(settings_path):
            import re
            with open(settings_path, 'r', encoding='utf-8') as f:
                content = f.read()
            m = re.search(r'"antigravityBridge\.teleBotToken"\s*:\s*"([^"]+)"', content)
            if m: token = m.group(1)
            m = re.search(r'"antigravityBridge\.whitelistChatIds"\s*:\s*"([^"]+)"', content)
            if m: default_chat_id = m.group(1)
    except Exception:
        pass
        
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not default_chat_id:
        default_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        
    chat_ids = []
    try:
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        network_config_path = os.path.join(agent_dir, "network_config.json")
        network_data = {}
        if os.path.exists(network_config_path):
            with open(network_config_path, "r", encoding="utf-8") as f:
                network_data = json.load(f)
                
        agent_identity = network_data.get("agent_identity", "Antigravity")
        channels_dict = network_data.get("channels", {})
        
        if target_channels is None:
            target_channels = network_data.get("default_broadcast", [])
            if isinstance(target_channels, list):
                target_channels = ",".join(target_channels)
                
        if target_channels and target_channels.lower() == "all":
            for ch_key, ch_info in channels_dict.items():
                if "chat_id" in ch_info:
                    chat_ids.append(ch_info["chat_id"])
        elif target_channels:
            for ch in target_channels.split(","):
                ch = ch.strip()
                if not ch: continue
                if ch in channels_dict and "chat_id" in channels_dict[ch]:
                    chat_ids.append(channels_dict[ch]["chat_id"])
                else:
                    if ch.startswith("-") or ch.isdigit():
                        chat_ids.append(ch)
    except Exception as e:
        pass
        
    if not chat_ids and default_chat_id:
        chat_ids = [c.strip() for c in default_chat_id.split(",") if c.strip()]
        
    chat_ids = list(set(chat_ids))
        
    return token, ",".join(chat_ids), agent_identity

def send_via_bridge(content, is_done=False, token="", chat_id="", agent_identity="Antigravity"):
    port = get_bridge_port()
    if port is None: return False
    url = f'http://127.0.0.1:{port}/send-telegram'
    data = json.dumps({'text': content, 'done': is_done, 'token': token, 'chat_id': chat_id, 'agent_identity': agent_identity}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return True
    except:
        return False

def signal_done_to_extension():
    agent_dir = os.path.dirname(os.path.abspath(__file__))
    done_file = os.path.join(agent_dir, ".agent_done")
    try:
        with open(done_file, "w") as f:
            f.write(str(os.getpid()))
    except:
        pass

def send_via_telegram_api(content, is_done=False, target_channels=None, screenshot=False):
    token, chat_ids, agent_identity = get_telegram_config(target_channels)
    if not token or not chat_ids:
        print("Không tìm thấy TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID", file=sys.stderr)
        return False
    
    text = f"🤖 {agent_identity}:\n\n{content}"
    success = False
    
    screenshot_path = None
    if screenshot:
        try:
            from PIL import ImageGrab
            import tempfile
            fd, screenshot_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            img = ImageGrab.grab()
            img.save(screenshot_path)
        except Exception as e:
            print(f"Lỗi chụp màn hình: {e}", file=sys.stderr)
            screenshot_path = None

    import requests
    for chat_id in chat_ids.split(","):
        chat_id = chat_id.strip()
        if not chat_id: continue
        try:
            if screenshot_path and os.path.exists(screenshot_path):
                url = f'https://api.telegram.org/bot{token}/sendPhoto'
                with open(screenshot_path, 'rb') as photo:
                    response = requests.post(url, data={'chat_id': chat_id, 'caption': text}, files={'photo': photo}, timeout=20, verify=False)
                if response.status_code == 200:
                    success = True
                else:
                    print(f"Telegram API Error: {response.status_code} - {response.text}", file=sys.stderr)
            else:
                url = f'https://api.telegram.org/bot{token}/sendMessage'
                response = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10, verify=False)
                if response.status_code == 200:
                    success = True
                else:
                    print(f"Telegram API Error: {response.status_code} - {response.text}", file=sys.stderr)
        except Exception as e:
            print(f"Lỗi gửi Telegram API cho chat {chat_id}: {e}", file=sys.stderr)
            
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            os.remove(screenshot_path)
        except:
            pass
    
    if is_done:
        signal_done_to_extension()
    
    return success

def send_to_telegram(content, is_done=False, target_channels=None, screenshot=False):
    if not content and not screenshot: return
    token, chat_ids, agent_identity = get_telegram_config(target_channels)
    # Nếu có chụp ảnh, ép dùng API vì bridge chưa chắc xử lý được file binary
    if screenshot:
        send_via_telegram_api(content, is_done, target_channels, screenshot=True)
        return
        
    if send_via_bridge(content, is_done, token, chat_ids, agent_identity): return
    send_via_telegram_api(content, is_done, target_channels, screenshot=False)

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(1)
    
    is_done = '--done' in sys.argv
    if is_done:
        sys.argv.remove('--done')
        
    screenshot = '--screenshot' in sys.argv
    if screenshot:
        sys.argv.remove('--screenshot')
        
    target_channels = None
    if '--channel' in sys.argv:
        idx = sys.argv.index('--channel')
        if idx + 1 < len(sys.argv):
            target_channels = sys.argv[idx + 1]
            sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
        
    if '--target' in sys.argv:
        idx = sys.argv.index('--target')
        if idx + 1 < len(sys.argv):
            target_channels = sys.argv[idx + 1]
            sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
        
    content = sys.argv[1] if len(sys.argv) > 1 else ""
    content = content.replace('\\n', '\n').replace(r'\n', '\n')
    send_to_telegram(content, is_done, target_channels, screenshot)
