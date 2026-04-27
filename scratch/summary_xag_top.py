import os, json, glob

def list_top_runs(workspace):
    runs_dir = os.path.join("workspaces", workspace, "runs")
    if not os.path.exists(runs_dir):
        return []
        
    runs = []
    for run_dir in glob.glob(os.path.join(runs_dir, "run_*")):
        metrics_file = os.path.join(run_dir, "results", "training_metrics_v3.json")
        if not os.path.exists(metrics_file):
            continue
            
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sessions = data.get("sessions", {})
            for session_name, session_data in sessions.items():
                if "BEST_VLOSS" in session_data:
                    score = session_data["BEST_VLOSS"].get("composite_score", 0.0)
                    runs.append({
                        "run": os.path.basename(run_dir),
                        "score": score,
                        "metrics": session_data["BEST_VLOSS"]
                    })
        except Exception as e:
            pass
            
    runs.sort(key=lambda x: x["score"], reverse=True)
    return runs[:3]

print("🔴 ASIAN:")
for r in list_top_runs("CFG_XAG_ASIAN_V3_5"): print(f"  {r['run']}: {r['score']:.3f}")
print("🟢 LONDON:")
for r in list_top_runs("CFG_XAG_LDN_V3_5"): print(f"  {r['run']}: {r['score']:.3f}")
print("🔵 NEW YORK:")
for r in list_top_runs("CFG_XAG_NY_V3_5"): print(f"  {r['run']}: {r['score']:.3f}")
