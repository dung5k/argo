import json, urllib.request, re

try:
    with open('.vscode/settings.json', encoding='utf-8') as f:
        settings = f.read()
    token = re.search(r'"antigravityBridge\.teleBotToken"\s*:\s*"([^"]+)"', settings).group(1)
    req = urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getUpdates')
    data = json.loads(req.read())
    
    chats = {}
    for m in data.get('result', []):
        if 'message' in m:
            chat = m['message']['chat']
            chat_id = chat['id']
            title = chat.get('title', chat.get('username', 'Private'))
            chats[chat_id] = title
            
    print('--- CÁC CHAT ID GẦN ĐÂY ---')
    for k, v in chats.items():
        print(f'ID: {k} | Tên/Loại: {v}')
    print('--- KẾT THÚC ---')
except Exception as e:
    print(f"Error: {e}")
