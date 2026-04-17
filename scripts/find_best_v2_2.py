import json
import os
from huggingface_hub import HfFileSystem, hf_hub_download

with open("tg_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
token = cfg.get("hf_token")

fs = HfFileSystem(token=token)
runs = fs.ls('datasets/dung5k/argo_data/runs')

v2_2_runs = [r['name'].split('/')[-1] for r in runs if "V2_2" in r['name']]
print(f"Tổng cộng {len(v2_2_runs)} runs V2.2 \n")

best_runs = []

for run_id in v2_2_runs:
    try:
        local_path = hf_hub_download(repo_id="dung5k/argo_data", repo_type="dataset", filename=f"runs/{run_id}/training_metrix_v2.json", token=token)
        with open(local_path, 'r', encoding='utf-8') as f:
            metrix = json.load(f)
            
        sessions = metrix.get("sessions", {})
        
        for sess_name, sess_data in sessions.items():
            for cfg_name, cfg_data in sess_data.items():
                epoch = cfg_data.get("epoch")
                comp_score = cfg_data.get("composite_score", 0)
                best_ev = cfg_data.get("best_ev", 0)
                
                # Tìm threshold có Win Rate cao nhất trong số các metrics >= 100 signals
                thr_metrics = cfg_data.get("threshold_metrics", [])
                
                best_wr = 0
                best_thr = 0
                best_n_sig = 0
                
                for t_m in thr_metrics:
                    sig = t_m.get("total_signals", 0)
                    wr = t_m.get("win_rate", 0)
                    if sig >= 100 and wr > best_wr:
                        best_wr = wr
                        best_thr = t_m.get("threshold", 0)
                        best_n_sig = sig
                        
                best_runs.append({
                    "run_id": run_id,
                    "session": sess_name,
                    "cfg_name": cfg_name,
                    "epoch": epoch,
                    "composite_score": comp_score,
                    "best_ev": best_ev,
                    "wr": best_wr,
                    "thr": best_thr,
                    "sig": best_n_sig
                })
    except Exception as e:
        pass

best_runs.sort(key=lambda x: x["wr"], reverse=True)

print("========== HÀNG TOP V2.2 (SẮP XẾP THEO WIN RATE TRÊN 100 SIGNALS) ==========")
for i, r in enumerate(best_runs[:10]):
    print(f"#{i+1}: [{r['session'].upper()}] {r['run_id']} | CFG: {r['cfg_name']} | WR: {r['wr']:.2f}% | Lệnh: {r['sig']} | EV: {r['best_ev']:.6f} | Epoch {r['epoch']} (Thr {r['thr']})")
