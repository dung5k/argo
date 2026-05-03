import urllib.request
import json
import sys

token = "8778828373:AAE6gYFhRUxyKHc5UfEavqMPBzeathAOPxQ"
chat_id = "1816854047"
text = "🤖 Kiểm tra trực tiếp API Telegram - Bỏ qua Bridge"

url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
req = urllib.request.Request(url, data=data, headers=headers)

try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Thành công! Phản hồi: {response.read().decode()}")
except Exception as e:
    print(f"Lỗi: {e}")
