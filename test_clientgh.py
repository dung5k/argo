import os
from pathlib import Path
log_dir = Path(os.environ.get('ARGO_LOGS_DIR', 'C:/argo/logs')) / 'clientGH'
if log_dir.exists():
    log_files = sorted(log_dir.glob('*_train.log'))
    if log_files:
        lines = log_files[-1].read_text(encoding='utf-8').splitlines()
        for i, l in enumerate(lines[:10]):
            print(f"LINE {i}: {l}")
