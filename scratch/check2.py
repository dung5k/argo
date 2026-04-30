import os, json

for loc, path in [("LDN", r"d:\DungLA\client1\workspaces\CFG_LTC_LONDON_V3_5\runs"), ("NY", r"d:\DungLA\client1\workspaces\CFG_LTC_NY_V3_5\runs")]:
    best_run = "None"
    best_score = 0.0
    if os.path.exists(path):
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if os.path.isdir(p):
                mf = os.path.join(p, "results", "training_metrics_v3.json")
                if os.path.exists(mf):
                    try:
                        d = json.load(open(mf))
                        score = d.get("composite_score", 0)
                        if score > best_score:
                            best_score = score
                            best_run = f
                    except: pass
    print(f"{loc} Best: {best_run} (Score: {best_score})")
