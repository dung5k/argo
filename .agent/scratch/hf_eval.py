import json, os, re
from huggingface_hub import HfApi

cfg = json.load(open('tg_config.json', 'r', encoding='utf-8'))
api = HfApi()
repo_id = cfg["hf_repo_id"]
token = cfg["hf_token"]

files = api.list_repo_files(repo_id=repo_id, repo_type="dataset", token=token)
runs_folders = set()
for f in files:
    if f.startswith('runs/'):
        d = f.split('/')[1]
        runs_folders.add(d)

latest_runs = {"asian": None, "london": None, "ny": None}
# We look for "asian_v2_1", "london_v2_1", "ny_v2_1" in the run folder names
for d in sorted(runs_folders, reverse=True): # Newest first
    if "asian_v2_1" in d.lower() and latest_runs["asian"] is None: latest_runs["asian"] = d
    if "london_v2_1" in d.lower() and latest_runs["london"] is None: latest_runs["london"] = d
    if "ny_v2_1" in d.lower() and latest_runs["ny"] is None: latest_runs["ny"] = d

print("Evaluating latest runs from Hugging Face...")
results_summary = {}

for k, v in latest_runs.items():
    if v:
        json_files = [f for f in files if f.startswith(f"runs/{v}/") and f.endswith('.json') and not "bot_config" in f]
        for jf in json_files:
            dl_path = api.hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=jf, token=token, local_dir=".agent/scratch")
            try:
                data = json.load(open(dl_path, 'r', encoding='utf-8'))
                
                top_metrics = []
                for cfg_name, cfg_data in data.items():
                    if "score" in cfg_name or "EV_" in cfg_name or "VLOSS" in cfg_name:
                        if isinstance(cfg_data, dict) and "threshold_metrics" in cfg_data:
                            best_wr = 0
                            best_ev = 0
                            signals = 0
                            for tm in cfg_data["threshold_metrics"]:
                                if tm["total_signals"] >= 30:
                                    if tm["win_rate"] > best_wr:
                                        best_wr = tm["win_rate"]
                                        best_ev = tm.get("ev_score", 0)
                                        signals = tm["total_signals"]
                            top_metrics.append({"wr": best_wr, "ev": best_ev, "n": signals, "type": cfg_name})
                                
                if top_metrics:
                    best = max(top_metrics, key=lambda x: x["wr"])
                    results_summary[k] = {"wr": best["wr"], "ev": best["ev"], "n": best["n"], "run": v}
            except Exception as e:
                pass

for k, v in results_summary.items():
    print(f"{k.upper()}: WR = {v['wr']:.2f}% | EV = {v['ev']:.6f} (N = {v['n']}) | Dir: {v['run']}")
    
if results_summary:
    worst_session = min(results_summary.items(), key=lambda x: x[1]['wr'])
    print(f"WORST_SESSION:{worst_session[0].upper()}")
