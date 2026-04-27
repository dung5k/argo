import json

with open('.agent/tasks.json', 'r') as f:
    data = json.load(f)

if isinstance(data, dict) and 'tasks' in data:
    tasks = data['tasks']
elif isinstance(data, list):
    tasks = data
else:
    tasks = []

for task in tasks:
    if task.get('id') == 'xag_asian_v4_tuning':
        task['enabled'] = False

with open('.agent/tasks.json', 'w') as f:
    json.dump(data if 'tasks' not in data else data, f, indent=2)

print("Disabled loop.")
