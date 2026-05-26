import json
import os
import re
import subprocess
import sys

settings_path = '.vscode/settings.json'
token = ''
chat_id = ''
if os.path.exists(settings_path):
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    m_token = re.search(r'"antigravityBridge\.teleBotToken"\s*:\s*"([^"]+)"', content)
    m_chat = re.search(r'"antigravityBridge\.whitelistChatIds"\s*:\s*"([^"]+)"', content)
    if m_token: token = m_token.group(1)
    if m_chat: chat_id = m_chat.group(1)

chat_ids = [c.strip() for c in chat_id.split(',')]

for cid in chat_ids:
    if not cid: continue
    cmd = [
        'curl', '-s', '-X', 'POST',
        f'https://api.telegram.org/bot{token}/sendPhoto',
        '-F', f'chat_id={cid}',
        '-F', 'photo=@run_38_holy_grail.png',
        '-F', 'caption=🏆 Biểu đồ thành tích Run 38 (The Holy Grail)\nĐường màu xanh là Win Rate (đạt đỉnh 90.9%).\nCột màu cam là số lượng tín hiệu giao dịch.'
    ]
    subprocess.run(cmd)
    print(f'Sent via curl to {cid}')
