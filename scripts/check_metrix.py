import json, glob, os

runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
metrix_files = sorted(glob.glob(os.path.join(runs_dir, '**', 'training_metrix.json'), recursive=True))

results = []
for mf in metrix_files:
    with open(mf, 'r', encoding='utf-8') as f:
        try: m = json.load(f)
        except: continue
    feats = m.get('training_metadata', {}).get('data_features', [])
    run = os.path.basename(os.path.dirname(mf))
    cfg = m.get('config', {})
    results.append((run, len(feats), cfg.get('num_xau_features', '?')))

with open('logs/all_runs.txt', 'w', encoding='utf-8') as f:
    for r, n, nx in results:
        f.write(f"{r}: {n} features, num_xau={nx}\n")

print('Written to logs/all_runs.txt')
print(f"Total runs: {len(results)}")
