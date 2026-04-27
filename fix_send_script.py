import os
import json

good_content = '''import sys
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

def get_telegram_config():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        try:
            agent_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(agent_dir)
            settings_path = os.path.join(project_root, '.vscode', 'settings.json')
            if os.path.exists(settings_path):
                import re
                with open(settings_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not token:
                    m = re.search(r'"antigravityBridge\.teleBotToken"\\s*:\\s*"([^"]+)"', content)
                    if m: token = m.group(1)
                if not chat_id:
                    m = re.search(r'"antigravityBridge\.whitelistChatIds"\\s*:\\s*"([^"]+)"', content)
                    if m: chat_id = m.group(1)
        except Exception:
            pass
    return token, chat_id

def send_via_bridge(content, is_done=False):
    port = get_bridge_port()
    if port is None: return False
    url = f'http://127.0.0.1:{port}/send-telegram'
    data = json.dumps({'text': content, 'done': is_done}).encode('utf-8')
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

def send_via_telegram_api(content, is_done=False):
    token, chat_ids = get_telegram_config()
    if not token or not chat_ids:
        print("Không tìm thấy TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID", file=sys.stderr)
        return False
    
    text = f"🤖 Antigravity:\\n\\n{content}"
    success = False
    for chat_id in chat_ids.split(","):
        chat_id = chat_id.strip()
        if not chat_id: continue
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                success = True
        except Exception as e:
            print(f"Lỗi gửi Telegram API cho chat {chat_id}: {e}", file=sys.stderr)
    
    if is_done:
        signal_done_to_extension()
    
    return success

def send_to_telegram(content, is_done=False):
    if not content: return
    if send_via_bridge(content, is_done): return
    send_via_telegram_api(content, is_done)

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(1)
    is_done = '--done' in sys.argv
    content = sys.argv[1]
    send_to_telegram(content, is_done)
'''

# 1. Update send_to_tele.py for client1
client1_path = r'd:\DungLA\client1\.agent\send_to_tele.py'
with open(client1_path, 'w', encoding='utf-8') as f:
    f.write(good_content)
print("Updated client1 send_to_tele.py")

# 2. Update send_to_tele.py for aibot
aibot_path = r'd:\DungLA\aibot\.agent\send_to_tele.py'
if os.path.exists(os.path.dirname(aibot_path)):
    with open(aibot_path, 'w', encoding='utf-8') as f:
        f.write(good_content)
    print("Updated aibot send_to_tele.py")

# 3. Update extension.js
ext_path = r'd:\DungLA\client1\tools\telegram_bridge_extension\extension.js'
with open(ext_path, 'r', encoding='utf-8') as f:
    ext_content = f.read()

import re

# Escape the good content for JS template literal
# Note: we need to escape backticks, \n inside regexes, etc.
# In our python string, we used double backslashes for regex so it's literal \s
# But in a JS template literal `...`, \s is just s, so we must double escape backslashes again
js_string_content = good_content.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

# Replace the block in ensureSendScript
pattern = re.compile(r'(const pyContent = `).*?(`;\s*fs\.writeFileSync)', re.DOTALL)
new_ext_content = pattern.sub(r'\1' + js_string_content + r'\2', ext_content)

with open(ext_path, 'w', encoding='utf-8') as f:
    f.write(new_ext_content)
print("Updated extension.js")

# 4. Bump version to 1.3.1 in package.json
pkg_path = r'd:\DungLA\client1\tools\telegram_bridge_extension\package.json'
with open(pkg_path, 'r', encoding='utf-8') as f:
    pkg = json.load(f)
pkg['version'] = '1.3.1'
with open(pkg_path, 'w', encoding='utf-8') as f:
    json.dump(pkg, f, indent=2)
print("Bumped package.json to 1.3.1")
