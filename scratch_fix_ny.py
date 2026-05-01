import json
import os
import shutil
import subprocess
from datetime import datetime

# 1. Tạo Run ID mới
run_id = f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}_v3_ny_baseline_fix'
run_dir = f'workspaces/CFG_XAG_NY_V3_5/runs/{run_id}'
os.makedirs(run_dir, exist_ok=True)

# 2. Copy config của run 8 (vì đây là run tốt nhất) sang run mới
src_config = 'workspaces/CFG_XAG_NY_V3_5/runs/run_20260427_060900_v4_ny_8/config.json'
dst_config = f'{run_dir}/config.json'

with open(src_config, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

# Đảm bảo SYNC_CHUNKS = True để đẩy lên HF
cfg['HF_CLOUD']['SYNC_CHUNKS'] = True
with open(dst_config, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=4)

print(f'Tạo thành công: {run_id}')

# 3. Chạy upload_v3_dataset.py (sẽ tính toán lại features = 54)
print('Đang chuẩn bị Tensor Data (input_dim=54)...')
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
env['PYTHONUTF8'] = '1'
subprocess.run(['C:\\argo\\venv\\Scripts\\python.exe', 'scripts/upload_v3_dataset.py', '--config', dst_config], check=True, env=env)

# 4. Chạy train_v3.py
print('Đang Train mô hình mới...')
subprocess.run(['C:\\argo\\venv\\Scripts\\python.exe', 'src/training_v3/train_v3.py', dst_config, '--session', 'ny', '--scratch', '--run-id', run_id], check=True, env=env)

# 5. Push lên HuggingFace qua Smart Sync
print('Đang Push lên HF...')
subprocess.run(['C:\\argo\\venv\\Scripts\\python.exe', 'scripts/sync_workspaces.py', 'push', 'CFG_XAG_NY_V3_5'], check=True, env=env)

print('HOÀN TẤT VÁ LỖI CHO LIVE BOT!')
