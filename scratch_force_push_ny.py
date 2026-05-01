import os
import shutil
import json
import subprocess

config_id = 'CFG_XAG_NY_V3_5'
run_id = 'run_20260501_202219_v3_ny_baseline_fix'

run_dir = f'workspaces/{config_id}/runs/{run_id}'
root_dir = f'workspaces/{config_id}'
brains_dir = f'{root_dir}/brains'

os.makedirs(brains_dir, exist_ok=True)

print("Đang ép copy file lên root để đồng bộ...")
# Copy pth
shutil.copy(f'{run_dir}/brains/aamt_v3_{config_id}_final.pth', f'{brains_dir}/aamt_v3_{config_id}_final.pth')

# Copy scaler
shutil.copy(f'{run_dir}/data/tensors/scaler_{config_id}.pkl', f'{root_dir}/scaler_{config_id}.pkl')

# Copy config
shutil.copy(f'{run_dir}/config.json', f'{root_dir}/base_config.json')

# Cập nhật best_runs.json
best_runs_path = f'{root_dir}/best_runs.json'
with open(best_runs_path, 'w', encoding='utf-8') as f:
    json.dump({
        "13:00-22:00": {
            "score": 0.650, 
            "run_id": run_id
        }
    }, f, indent=4)

print("Đang Push lên HF...")
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
env['PYTHONUTF8'] = '1'
subprocess.run(['C:\\argo\\venv\\Scripts\\python.exe', 'scripts/sync_workspaces.py', 'push', config_id], check=True, env=env)
print("Hoàn tất Force Push!")
