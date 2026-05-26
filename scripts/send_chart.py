import json
import os
import glob
import re
import urllib.request
import urllib.parse
import sys
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

try:
    import matplotlib.pyplot as plt
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'matplotlib'], check=True)
    import matplotlib.pyplot as plt

# 1. Find Run 38 metrics
files = glob.glob('workspaces/CFG_LTC_LONDON_V3_5/runs/run_*_38*/results/training_metrics_v3.json')
if not files:
    print('Run 38 metrics not found!')
    sys.exit(1)

with open(files[0], 'r') as f:
    data = json.load(f)

session_data = data.get('sessions', {}).get('london', {}).get('BEST_VLOSS', {})
thresholds = session_data.get('thresholds', [])
win_rates = session_data.get('win_rates', [])
totals = session_data.get('totals', [])

if not thresholds or not win_rates:
    print('Missing metric data')
    sys.exit(1)

# 2. Draw chart
plt.figure(figsize=(10, 6))
fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Prediction Confidence Threshold')
ax1.set_ylabel('Win Rate (%)', color=color)
ax1.plot(thresholds, [wr * 100 for wr in win_rates], marker='o', color=color, linewidth=2, markersize=8, label='Win Rate')
ax1.tick_params(axis='y', labelcolor=color)
ax1.grid(True, linestyle='--', alpha=0.7)

# Highlight max win rate
max_wr = max(win_rates)
max_idx = win_rates.index(max_wr)
ax1.annotate(f'{max_wr*100:.1f}% Win Rate\n({totals[max_idx]} trades)', 
             xy=(thresholds[max_idx], max_wr*100), xytext=(thresholds[max_idx]-0.02, max_wr*100+2),
             arrowprops=dict(facecolor='red', shrink=0.05), fontsize=12, fontweight='bold', color='red')

ax2 = ax1.twinx()
color = 'tab:orange'
ax2.set_ylabel('Total Trades', color=color)
ax2.bar(thresholds, totals, width=0.01, color=color, alpha=0.3, label='Total Trades')
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Run 38 (The Holy Grail) - LTC London Performance', fontsize=16, fontweight='bold')
fig.tight_layout()
chart_path = 'run_38_holy_grail.png'
plt.savefig(chart_path, dpi=300)

# 3. Get token
token = ''
chat_id = ''
settings_path = '.vscode/settings.json'
if os.path.exists(settings_path):
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    m_token = re.search(r'"antigravityBridge\.teleBotToken"\s*:\s*"([^"]+)"', content)
    m_chat = re.search(r'"antigravityBridge\.whitelistChatIds"\s*:\s*"([^"]+)"', content)
    if m_token: token = m_token.group(1)
    if m_chat: chat_id = m_chat.group(1)

if not token or not chat_id:
    print('Telegram config not found in settings.json')
    sys.exit(1)

chat_ids = [c.strip() for c in chat_id.split(',')]

# 4. Send photo via Telegram API
import uuid

for cid in chat_ids:
    if not cid: continue
    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    boundary = uuid.uuid4().hex
    
    with open(chart_path, 'rb') as f:
        photo_data = f.read()
    
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f'{cid}\r\n'
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="caption"\r\n\r\n'
        f'🏆 Biểu đồ thành tích Run 38 (The Holy Grail)\r\nĐường màu xanh là Win Rate (đạt đỉnh 90.9%).\r\nCột màu cam là số lượng tín hiệu giao dịch.\r\n'
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="photo"; filename="chart.png"\r\n'
        f'Content-Type: image/png\r\n\r\n'
    ).encode('utf-8') + photo_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
    
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(body))
    }
    
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        urllib.request.urlopen(req)
        print(f'Sent photo to {cid}')
    except Exception as e:
        print(f'Failed to send photo: {e}')
