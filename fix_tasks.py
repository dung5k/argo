import json
with open(".agent/tasks.json", "r", encoding="utf-8") as f:
    data = json.load(f)
for task in data.get("tasks", []):
    if task.get("id") == "xag_all_sessions_v5_auto_tuning":
        task["enabled"] = False
with open(".agent/tasks.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
