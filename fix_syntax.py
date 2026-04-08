import os
for path in ['src/core/trade_mt5.py', 'src/bot_v2/bot_v2.py']:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        # Fix the syntax error causing the python crash
        text = text.replace('else \\"Local\\"}', 'else "Local"}')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
print("FIXED SYNTAX ERROR")
