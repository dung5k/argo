# -*- coding: utf-8 -*-
import os, json, glob
from datetime import datetime

runs_dir = "workspaces/CFG_LTC_ASIAN_V6/runs"
results = []

for run_dir in sorted(glob.glob(os.path.join(runs_dir, "run_*"))):
    metrics_path = os.path.join(run_dir, "results", "training_metrics_v3.json")
    if not os.path.exists(metrics_path):
        continue
    run_name = os.path.basename(run_dir)
    if not (run_name.startswith("run_20260514") or run_name.startswith("run_20260515")):
        continue
    with open(metrics_path, 'r', encoding='utf-8') as f:
        m = json.load(f)
    asian = m["sessions"]["asian"]["BEST_VLOSS"]
    epoch = asian["epoch"]
    score = asian["composite_score"]
    wr_high = asian["win_rates"][-1] * 100
    thr_high = asian["thresholds"][-1]
    wr_mid = asian["win_rates"][-2] * 100 if len(asian["win_rates"]) >= 2 else 0
    total_signals_high = asian["totals"][-1]
    buy_high = asian["threshold_metrics"][-1]["total_buy"]
    sell_high = asian["threshold_metrics"][-1]["total_sell"]
    
    # Extract timestamp from run name: run_YYYYMMDD_HHMMSS_...
    parts = run_name.split("_")
    date_str = parts[1]  # YYYYMMDD
    time_str = parts[2]  # HHMMSS
    try:
        dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        time_display = dt.strftime("%d/%m %H:%M")
    except:
        time_display = "N/A"
    
    # Short name: remove run_YYYYMMDD_HHMMSS_v6_ASIAN_
    short = run_name.split("v6_ASIAN_")[-1] if "v6_ASIAN_" in run_name else run_name

    results.append({
        "short": short,
        "time": time_display,
        "epoch": epoch,
        "score": score,
        "wr_high": wr_high,
        "thr_high": thr_high,
        "wr_mid": wr_mid,
        "total_signals": total_signals_high,
        "buy": buy_high,
        "sell": sell_high,
    })

results.sort(key=lambda x: x["wr_high"], reverse=True)

lines = []
lines.append(f"TOP 15 BO NAO ASIAN V6 TOT NHAT (167 vong)")
lines.append(f"")
lines.append(f"{'#':>2} | {'Thoi gian':<12} | {'WR@High':>8} | {'Score':>7} | {'Sig':>4} | {'B/S':>7} | {'Ep':>3} | Ten cau hinh")
lines.append("-" * 90)
for i, r in enumerate(results[:15]):
    lines.append(f"{i+1:2d} | {r['time']:<12} | {r['wr_high']:>6.2f}% | {r['score']:>6.4f} | {r['total_signals']:>4} | {r['buy']:>3}/{r['sell']:<3} | E{r['epoch']:<2} | {r['short']}")

lines.append("")
lines.append("---")
lines.append("So sanh voi V159 (dang chay Live):")
for r in results:
    if "BigBrain_159" in r["short"]:
        lines.append(f"   | {r['time']:<12} | {r['wr_high']:>6.2f}% | {r['score']:>6.4f} | {r['total_signals']:>4} | {r['buy']:>3}/{r['sell']:<3} | E{r['epoch']:<2} | {r['short']}")
        break

report = "\n".join(lines)
print(report)

# Write to msg.txt
with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(report)
