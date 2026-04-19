import sys
import json
import urllib.request
import urllib.error

def send_to_telegram(content, is_done=False):
    if not content:
        return
    url = 'http://127.0.0.1:38124/send-telegram'
    data = json.dumps({'text': content, 'done': is_done}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        print(f"Lỗi gửi HTTP request: {e}", file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(1)
    is_done = '--done' in sys.argv
    content = sys.argv[1]
    send_to_telegram(content, is_done)
