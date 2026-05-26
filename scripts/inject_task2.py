import json
import time

task_file = r'd:\DungLA\aibot\.agent\tasks.json'
with open(task_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Thêm task mới
new_task = {
    "id": "check_tele_token",
    "enabled": True,
    "promptFile": ".agent/prompt_check_token.md",
    "nextRunTime": 0,
    "intervalMinutes": 0
}

# Remove if exists to avoid duplicate
data['tasks'] = [t for t in data['tasks'] if t['id'] != "check_tele_token"]
data['tasks'].append(new_task)

with open(task_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
