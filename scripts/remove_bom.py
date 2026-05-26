import os
import json

f = 'bot_schedule_v6_ltc.json'
with open(f, 'r', encoding='utf-8-sig') as file:
    data = json.load(file)
with open(f, 'w', encoding='utf-8') as file:
    json.dump(data, file, indent=4)
