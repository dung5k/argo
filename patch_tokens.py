import os
import re

files_to_fix = [
    "src/training_v6/train_v6.py",
    "src/training_v3/plotter_v3.py",
    "src/training_v3/train_v3.py",
    "scripts/get_chat_ids.py",
    "src/bot_master/bot_master.py",
    "src/bot_v3/bot_v3.py",
    "scripts/send_chart.py",
    "scripts/send_curl.py"
]

for filepath in files_to_fix:
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern 1: vsc_token = vsc.get("antigravityBridge.teleBotToken")
    content = content.replace(
        'vsc_token = vsc.get("antigravityBridge.teleBotToken")',
        'vsc_token = os.environ.get("TELEGRAM_BOT_TOKEN") or vsc.get("antigravityBridge.teleBotToken")'
    )
    
    # Pattern 2: vsc_chat = vsc.get("antigravityBridge.whitelistChatIds")
    content = content.replace(
        'vsc_chat = vsc.get("antigravityBridge.whitelistChatIds")',
        'vsc_chat = os.environ.get("TELEGRAM_CHAT_ID") or vsc.get("antigravityBridge.whitelistChatIds")'
    )

    # Pattern 3: tg_token = vsc_cfg.get("antigravityBridge.teleBotToken")
    content = content.replace(
        'tg_token = vsc_cfg.get("antigravityBridge.teleBotToken")',
        'tg_token = os.environ.get("TELEGRAM_BOT_TOKEN") or vsc_cfg.get("antigravityBridge.teleBotToken")'
    )

    # Pattern 4: tg_chat = vsc_cfg.get("antigravityBridge.whitelistChatIds")
    content = content.replace(
        'tg_chat = vsc_cfg.get("antigravityBridge.whitelistChatIds")',
        'tg_chat = os.environ.get("TELEGRAM_CHAT_ID") or vsc_cfg.get("antigravityBridge.whitelistChatIds")'
    )
    
    # Pattern 5 for scripts/send_chart.py etc using re.search
    content = re.sub(
        r'(m_token\s*=\s*re\.search\(.*?teleBotToken.*?content\)\n\s*if\s+m_token:\n\s*token\s*=\s*m_token\.group\(1\))',
        r'token = os.environ.get("TELEGRAM_BOT_TOKEN")\n    if not token:\n        \1',
        content
    )
    
    content = re.sub(
        r'(m_chat\s*=\s*re\.search\(.*?whitelistChatIds.*?content\)\n\s*if\s+m_chat:\n\s*chat_id\s*=\s*m_chat\.group\(1\))',
        r'chat_id = os.environ.get("TELEGRAM_CHAT_ID")\n    if not chat_id:\n        \1',
        content
    )

    # Pattern for plotter_v3.py / train_v3.py / train_v6.py fallback
    content = re.sub(
        r'(m\s*=\s*re\.search\(.*?teleBotToken.*?content\)\n\s*if\s+m:\n\s*)([a-zA-Z0-9_]+)\s*=\s*m\.group\(1\)',
        r'\g<2> = os.environ.get("TELEGRAM_BOT_TOKEN")\n                        if not \g<2>:\n                            \g<1>\g<2> = m.group(1)',
        content
    )
    
    content = re.sub(
        r'(m\s*=\s*re\.search\(.*?whitelistChatIds.*?content\)\n\s*if\s+m:\n\s*)([a-zA-Z0-9_]+)\s*=\s*m\.group\(1\)',
        r'\g<2> = os.environ.get("TELEGRAM_CHAT_ID")\n                        if not \g<2>:\n                            \g<1>\g<2> = m.group(1)',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filepath}")

