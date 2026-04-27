import sys
sys.path.append('.')
from scripts.sync_workspaces import push_run

print("Đẩy Best Run phiên London...")
push_run('CFG_XAG_LDN_V3_5', 'run_20260426_204917_v4_ldn_2')

print("\nĐẩy Best Run phiên NY...")
push_run('CFG_XAG_NY_V3_5', 'run_20260427_060900_v4_ny_8')

print("\nĐã đẩy thành công lên Hugging Face!")
