import os, glob, json
best_runs = {}
for path in glob.glob("workspaces/CFG_XAG_*/runs/*/results/training_metrics_v3.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            score = data.get("test_metrics", {}).get("composite_score", 0)
            wr = 0
            if "test_metrics" in data and "win_rate_stats" in data["test_metrics"]:
                wr = data["test_metrics"]["win_rate_stats"].get("overall_win_rate", 0)
            
            # replace backslashes
            path = path.replace("\\", "/")
            session = path.split("/")[1]
            if session not in best_runs or score > best_runs[session]["score"]:
                best_runs[session] = {"run_id": path.split("/")[3], "score": score, "wr": wr}
    except Exception as e: 
        print("error", path, e)
        pass
for s, b in best_runs.items(): 
    print(f"{s}: Best Run: {b['run_id']} - Score: {b['score']:.4f} - WR: {b['wr']*100:.2f}%")
