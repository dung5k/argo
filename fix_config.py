import glob
import json

for f in glob.glob('bot_config_v6_ltc_*.json'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace('"5min"', '"1m"').replace('"M15"', '"M1"')
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f"Updated {f}")
