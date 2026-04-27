import os, json
def get_best(w):
    r_dir = os.path.join('workspaces', w, 'runs')
    if not os.path.exists(r_dir): return []
    runs = []
    session_key = w.split('_')[2].lower()
    for d in os.listdir(r_dir):
        path = os.path.join(r_dir, d, 'results', 'training_metrics_v3.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                score = data.get('sessions', {}).get(session_key, {}).get('BEST_VLOSS', {}).get('composite_score', 0)
                runs.append((d, score))
    runs.sort(key=lambda x: x[1], reverse=True)
    return runs

print('LDN Best:', get_best('CFG_XAG_LDN_V3_5')[:3])
print('NY Best:', get_best('CFG_XAG_NY_V3_5')[:3])
