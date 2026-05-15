import os
import json
import shutil

runs_dir = r'd:\DungLA\client1\workspaces\CFG_LTC_WEEKEND_V6\runs'
best_run = None
best_score = -1
best_run_path = ''

for run_name in os.listdir(runs_dir):
    run_path = os.path.join(runs_dir, run_name)
    metrics_path = os.path.join(run_path, 'results', 'training_metrics_v3.json')
    
    if not os.path.exists(metrics_path):
        continue
        
    with open(metrics_path, 'r', encoding='utf-8') as f:
        try:
            metrics = json.load(f)
        except:
            continue
            
    best_vloss = metrics.get('sessions', {}).get('weekend', {}).get('BEST_VLOSS', {})
    if not best_vloss:
        continue
        
    t_metrics = best_vloss.get('threshold_metrics', [])
    if not t_metrics:
        continue
        
    # Find the metric with max WR? Or max score? 
    # Let's find the max signals
    max_signals = max([m.get('total_signals', 0) for m in t_metrics])
    
    # Check what was the highest win_rate among those with at least 10 signals
    valid_metrics = [m for m in t_metrics if m.get('total_signals', 0) >= 10]
    
    if not valid_metrics:
        print(f"Xóa Run: {run_name} (Max Signals: {max_signals})")
        # try to delete
        try:
            shutil.rmtree(run_path)
        except Exception as e:
            print(f" Lỗi xóa {run_name}: {e}")
        continue
        
    # The score could be the max balanced_score
    max_score = max([m.get('ev_score', 0) for m in valid_metrics])
    
    if max_score > best_score:
        best_score = max_score
        best_run = run_name
        best_run_path = run_path

print(f"BEST RUN FOUND: {best_run} with score {best_score}")

if best_run:
    config_path = r'd:\DungLA\client1\bot_config_v6_ltc_weekend.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    config['INFERENCE']['MODEL_PATH'] = os.path.join(best_run_path, 'brains', 'aamt_v3_CFG_LTC_WEEKEND_V6_final.pth')
    config['INFERENCE']['SCALER_PATH'] = os.path.join(best_run_path, 'brains', 'scaler_CFG_LTC_WEEKEND_V6.pkl')
    
    # We should set PROB_THRESHOLD to the threshold of the best valid metric
    with open(os.path.join(best_run_path, 'results', 'training_metrics_v3.json'), 'r') as f:
        best_metrics = json.load(f)['sessions']['weekend']['BEST_VLOSS']['threshold_metrics']
        valid = [m for m in best_metrics if m.get('total_signals', 0) >= 10]
        best_metric = max(valid, key=lambda x: x.get('ev_score', 0))
        config['INFERENCE']['PROB_THRESHOLD'] = best_metric['threshold']
        print(f"Set threshold to {best_metric['threshold']} with WR {best_metric['win_rate']}")
        
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
