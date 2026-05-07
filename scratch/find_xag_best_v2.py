import os, glob, json

best_runs = {}
for path in glob.glob("workspaces/CFG_XAG_*/runs/*/results/training_metrics_v3.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            path = path.replace("\\", "/")
            session_ws = path.split("/")[1]
            score = 0
            wr = 0
            if "sessions" in data:
                sess_key = list(data["sessions"].keys())[0]
                best_vloss = data["sessions"][sess_key].get("BEST_VLOSS", {})
                score = best_vloss.get("composite_score", 0)
                if "threshold_metrics" in best_vloss and len(best_vloss["threshold_metrics"]) > 0:
                    wr = best_vloss["threshold_metrics"][-1].get("win_rate", 0)
            else:
                score = data.get("test_metrics", {}).get("composite_score", 0)
                if "test_metrics" in data and "win_rate_stats" in data["test_metrics"]:
                    wr = data["test_metrics"]["win_rate_stats"].get("overall_win_rate", 0)
            
            if session_ws not in best_runs or score > best_runs[session_ws]["score"]:
                best_runs[session_ws] = {"run_id": path.split("/")[3], "score": score, "wr": wr}
    except Exception as e: 
        pass
        
for s, b in best_runs.items(): 
    print(f"{s}: Best Run: {b['run_id']} - Score: {b['score']:.4f} - WR: {b['wr']*100:.2f}%")
