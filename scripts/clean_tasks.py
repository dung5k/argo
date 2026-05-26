import json

task_file = r'd:\DungLA\aibot\.agent\tasks.json'
with open(task_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Remove the incorrectly added tasks
data['tasks'] = [t for t in data['tasks'] if t['id'] not in ["fix_tele_connection_urgent", "check_tele_token"]]

with open(task_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
