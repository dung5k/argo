import json
import glob
import os
runs = sorted(glob.glob('workspaces/CFG_LTC_NY_V6/runs/run_*'))
for r in runs:
    metrics_file = os.path.join(r, 'results', 'training_metrics_v3.json')
    try:
        with open(metrics_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            best_metrics = data['sessions']['ny']['BEST_VLOSS']['threshold_metrics']
            highest_thresh = best_metrics[-1]
            buy = highest_thresh['total_buy']
            sell = highest_thresh['total_sell']
            total = buy + sell
            tus = 1 - abs(buy - sell) / total if total > 0 else 0
            wr = highest_thresh['win_rate'] * 100
            print(f"Run: {os.path.basename(r)}")
            print(f"  - Threshold: {highest_thresh['threshold']}")
            print(f"  - WR: {wr:.2f}%")
            print(f"  - TUS: {tus:.2f} (Buy: {buy}, Sell: {sell})")
    except Exception as e:
        pass
