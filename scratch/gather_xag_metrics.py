import os
import json

sessions = ['CFG_XAG_LDN_V3_5', 'CFG_XAG_NY_V3_5', 'CFG_XAG_ASIAN_V3_5']
results = {}

for session in sessions:
    runs_dir = os.path.join('workspaces', session, 'runs')
    if not os.path.exists(runs_dir):
        continue
        
    session_runs = []
    for run_name in os.listdir(runs_dir):
        run_path = os.path.join(runs_dir, run_name)
        if not os.path.isdir(run_path):
            continue
            
        metrics_path = os.path.join(run_path, 'results', 'training_metrics_v3.json')
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, 'r', encoding='utf-8') as f:
                    metrics = json.load(f)
                    
                    score = 0
                    win_rate = 0
                    if 'sessions' in metrics:
                        for s_key, s_data in metrics['sessions'].items():
                            if 'BEST_VLOSS' in s_data:
                                score = s_data['BEST_VLOSS'].get('composite_score', 0)
                                if 'win_rates' in s_data['BEST_VLOSS'] and len(s_data['BEST_VLOSS']['win_rates']) > 0:
                                    win_rate = s_data['BEST_VLOSS']['win_rates'][-1]
                    session_runs.append({'run': run_name, 'score': score, 'win_rate': win_rate})
            except Exception as e:
                print(f"Error reading {metrics_path}: {e}")
        else:
            # Maybe it hasn't finished training
            print(f"No training_metrics_v3.json for {run_name} in {session}")
            
    # Sort by score descending
    session_runs.sort(key=lambda x: x['score'], reverse=True)
    results[session] = session_runs

print(json.dumps(results, indent=2))
