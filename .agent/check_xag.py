import os, json

def get_best_runs(workspace, session_name):
    runs_dir = os.path.join('workspaces', workspace, 'runs')
    if not os.path.exists(runs_dir): return []
    
    results = []
    for run in os.listdir(runs_dir):
        metrics_path = os.path.join(runs_dir, run, 'results', 'training_metrics_v3.json')
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, 'r', encoding='utf-8') as f:
                    metrics = json.load(f)
                
                # Check target structure
                if 'sessions' not in metrics: continue
                
                session_key = session_name
                # Some runs might have uppercase or different key for session
                if session_name not in metrics['sessions']:
                    for k in metrics['sessions'].keys():
                        if session_name in k.lower():
                            session_key = k
                            break
                            
                session_data = metrics.get('sessions', {}).get(session_key, {}).get('BEST_VLOSS', {})
                if not session_data: continue
                    
                score = session_data.get('composite_score', 0)
                
                threshold_metrics = session_data.get('threshold_metrics', [])
                best_wr = 0
                n_signals = 0
                for tm in threshold_metrics:
                    if abs(tm.get('threshold', 0) - 0.53) < 0.001:
                        best_wr = tm.get('win_rate', 0) * 100
                        n_signals = tm.get('total_signals', 0)
                        break
                
                if best_wr == 0 and threshold_metrics:
                    best_wr = max([tm.get('win_rate', 0) for tm in threshold_metrics]) * 100
                    n_signals = threshold_metrics[0].get('total_signals', 0)
                    
                results.append({
                    'run': run,
                    'score': score,
                    'wr': best_wr,
                    'n': n_signals
                })
            except Exception as e:
                pass
                
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:5]

ldn_runs = get_best_runs('CFG_XAG_LDN_V3_5', 'london')
if not ldn_runs: ldn_runs = get_best_runs('CFG_XAG_LDN_V3_5', 'ldn')
ny_runs = get_best_runs('CFG_XAG_NY_V3_5', 'ny')

print('--- TOP 5 XAG LONDON ---')
for r in ldn_runs: print(f"{r['run']} | Score: {r['score']:.3f} | WR: {r['wr']:.1f}% | N: {r['n']}")

print('\n--- TOP 5 XAG NY ---')
for r in ny_runs: print(f"{r['run']} | Score: {r['score']:.3f} | WR: {r['wr']:.1f}% | N: {r['n']}")
