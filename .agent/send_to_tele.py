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
    # 1. Cố gắng lấy Telegram credentials từ Environment Variables trước (Ưu tiên số 1)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    default_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    # 2. Đọc từ cấu hình của Extension VSCode (.vscode/settings.json) nếu env vars bị thiếu
    if not token or not default_chat_id:
        try:
            agent_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(agent_dir)
            settings_path = os.path.join(project_root, '.vscode', 'settings.json')
            if os.path.exists(settings_path):
                import re
                with open(settings_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not token:
                    m = re.search(r'"antigravityBridge\.teleBotToken"\s*:\s*"([^"]+)"', content)
                    if m: token = m.group(1)
                if not default_chat_id:
                    m = re.search(r'"antigravityBridge\.whitelistChatIds"\s*:\s*"([^"]+)"', content)
                    if m: default_chat_id = m.group(1)
        except Exception:
            pass

    # 3. Đọc từ các file cấu hình cục bộ của hệ thống (tg_config.json hoặc telegram_bot_info.json) nếu vẫn thiếu
    if not token or not default_chat_id:
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(agent_dir)
        tg_config_candidates = [
            os.path.join(agent_dir, "telegram_bot_info.json"),
            os.path.join(project_root, "tg_config.json"),
        ]
        for tg_config_path in tg_config_candidates:
            if os.path.exists(tg_config_path):
                try:
                    with open(tg_config_path, "r", encoding="utf-8") as f:
                        tcfg = json.load(f)
                    if not token:
                        token = tcfg.get("bot_token", "")
                    if not default_chat_id:
                        tg_chat_id = tcfg.get("allowed_chat_ids", [None])[0]
                        if tg_chat_id: default_chat_id = str(tg_chat_id)
                    break
                except Exception:
                    pass

    chat_ids = []
    try:
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        network_config_path = os.path.join(agent_dir, "network_config.json")
        network_data = {}
        if os.path.exists(network_config_path):
            with open(network_config_path, "r", encoding="utf-8") as f:
                network_data = json.load(f)
                
        # Phân giải agent_identity động theo hostname/env để tránh bị overwrite bởi git pull của máy khác
        agent_identity = os.environ.get("ARGO_CLIENT_ID", "")
        if not agent_identity or agent_identity == "UnknownClient":
            import socket
            hostname = socket.gethostname().upper()
            if "N67BHMU" in hostname:
                agent_identity = "Argo1"
            elif "4C05378" in hostname:
                agent_identity = "Argo2"
            else:
                agent_identity = network_data.get("agent_identity", "Antigravity")
        else:
            if agent_identity.upper() == "ARGO1":
                agent_identity = "Argo1"
            elif agent_identity.upper() == "ARGO2":
                agent_identity = "Argo2"

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

def take_screenshot(save_path):
    import subprocess
    # Script powershell chụp toàn bộ màn hình của Primary Screen
    ps_cmd = (
        "[Reflection.Assembly]::LoadWithPartialName('System.Drawing') | Out-Null; "
        "[Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
        "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height); "
        "$graphics = [System.Drawing.Graphics]::FromImage($bmp); "
        "$graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size); "
        f"$bmp.Save('{save_path}', [System.Drawing.Imaging.ImageFormat]::Png); "
        "$graphics.Dispose(); $bmp.Dispose();"
    )
    try:
        subprocess.run(["powershell", "-Command", ps_cmd], shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return os.path.exists(save_path)
    except Exception as e:
        print(f"Lỗi chụp màn hình qua PowerShell: {e}", file=sys.stderr)
        return False

def send_via_telegram_api(content, is_done=False, target_channels=None, screenshot=False):
    token, chat_ids, agent_identity = get_telegram_config(target_channels)
    if not token or not chat_ids:
        print("Không tìm thấy TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID", file=sys.stderr)
        return False
    
    text = f"🤖 {agent_identity}:\n\n{content}"
    success = False
    
    screenshot_path = None
    if screenshot:
        import tempfile
        fd, screenshot_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        if not take_screenshot(screenshot_path):
            screenshot_path = None

    import ssl
    ssl_context = ssl._create_unverified_context()

    for chat_id in chat_ids.split(","):
        chat_id = chat_id.strip()
        if not chat_id: continue
        
        try:
            if screenshot_path and os.path.exists(screenshot_path):
                url = f'https://api.telegram.org/bot{token}/sendPhoto'
                boundary = '----WebKitFormBoundaryAntigravityScreenshot'
                
                parts = []
                parts.append(f'--{boundary}')
                parts.append('Content-Disposition: form-data; name="chat_id"')
                parts.append('')
                parts.append(str(chat_id))
                
                parts.append(f'--{boundary}')
                parts.append('Content-Disposition: form-data; name="caption"')
                parts.append('')
                parts.append(text)
                
                parts.append(f'--{boundary}')
                parts.append('Content-Disposition: form-data; name="photo"; filename="screenshot.png"')
                parts.append('Content-Type: image/png')
                parts.append('')
                
                with open(screenshot_path, 'rb') as f:
                    file_content = f.read()
                    
                body_parts = []
                for p in parts:
                    body_parts.append(p.encode('utf-8'))
                body_parts.append(file_content)
                body_parts.append(f'--{boundary}--'.encode('utf-8'))
                
                body = b'\r\n'.join(body_parts[0:-2]) + b'\r\n' + body_parts[-2] + b'\r\n' + body_parts[-1] + b'\r\n'
                
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        'Content-Type': f'multipart/form-data; boundary={boundary}',
                        'Content-Length': str(len(body))
                    }
                )
            else:
                url = f'https://api.telegram.org/bot{token}/sendMessage'
                data = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                
            with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
                success = True
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
    if content.startswith('@file:'):
        file_path = content[6:].strip()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                os.remove(file_path) # Clean up temporary file
            except Exception as e:
                print(f"Error reading message file: {e}", file=sys.stderr)
    else:
        # Sửa lỗi ký tự xuống dòng bị cắt/báo lỗi trên terminal
        content = content.replace('\\n', '\n').replace('\\t', '\t')
        
    send_to_telegram(content, is_done, target_channels, screenshot)
