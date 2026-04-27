import os
import shutil

# Top 2 runs
keep_ldn = ['run_20260426_222918_v4_ldn_7', 'run_20260427_164304_v4_ldn_18', 'run_20260427_190222_v4_ldn_20']
keep_ny = ['run_20260427_060900_v4_ny_8', 'run_20260425_005343_v3_ny_18']

def cleanup_session(session_name, keep_list):
    runs_dir = os.path.join('workspaces', session_name, 'runs')
    if not os.path.exists(runs_dir):
        return
    for run_name in os.listdir(runs_dir):
        if run_name not in keep_list:
            run_path = os.path.join(runs_dir, run_name)
            try:
                shutil.rmtree(run_path)
                print(f"Deleted local: {run_path}")
            except Exception as e:
                print(f"Failed to delete {run_path}: {e}")

cleanup_session('CFG_XAG_LDN_V3_5', keep_ldn)
cleanup_session('CFG_XAG_NY_V3_5', keep_ny)
cleanup_session('CFG_XAG_ASIAN_V3_5', [])

print("Local cleanup finished.")
