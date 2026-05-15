import sys
import os
os.environ["TELEGRAM_BOT_TOKEN"] = "8057292338:AAF2EnD_V9dWVNiDPnEfPEyYMKHxJQnNzlg"
with open('error_summary.txt', 'r', encoding='utf-8') as f:
    content = f.read()
sys.path.insert(0, os.path.abspath('.agent'))
import send_to_tele
send_to_tele.send_to_telegram(content, is_done=True, target_channels='1816854047')
