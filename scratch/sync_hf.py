import os
from huggingface_hub import HfApi

repo_id = "dung5k/argo_workspaces"
hf_token = "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"
api = HfApi(token=hf_token)

top_runs = {
    'CFG_XAG_LDN_V3_5': ['run_20260426_222918_v4_ldn_7', 'run_20260427_164304_v4_ldn_18'],
    'CFG_XAG_NY_V3_5': ['run_20260427_060900_v4_ny_8', 'run_20260425_005343_v3_ny_18']
}

print("Cleaning up remote datasets on HF...")
for session in ['CFG_XAG_LDN_V3_5', 'CFG_XAG_NY_V3_5', 'CFG_XAG_ASIAN_V3_5']:
    remote_path = f"workspaces/{session}"
    try:
        api.delete_folder(repo_id=repo_id, repo_type="dataset", path_in_repo=remote_path)
        print(f"Deleted remote {remote_path}")
    except Exception as e:
        print(f"Failed to delete remote {remote_path}: {e}")

print("Pushing best configs to HF...")
for session, runs in top_runs.items():
    base_cfg = os.path.join("workspaces", session, "base_config.json")
    if os.path.exists(base_cfg):
        try:
            api.upload_file(
                path_or_fileobj=base_cfg,
                path_in_repo=f"workspaces/{session}/base_config.json",
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"Restore base config for {session}"
            )
            print(f"Uploaded {base_cfg}")
        except Exception as e:
            print(f"Error uploading {base_cfg}: {e}")
            
    for run in runs:
        local_run_dir = os.path.join("workspaces", session, "runs", run)
        remote_run_dir = f"workspaces/{session}/runs/{run}"
        if os.path.exists(local_run_dir):
            print(f"Uploading {local_run_dir} -> {remote_run_dir}")
            try:
                api.upload_folder(
                    folder_path=local_run_dir,
                    path_in_repo=remote_run_dir,
                    repo_id=repo_id,
                    repo_type="dataset",
                    commit_message=f"Sync best run {run} for {session}"
                )
                print(f"Successfully uploaded {run}")
            except Exception as e:
                print(f"Error uploading {run}: {e}")
        else:
            print(f"Local dir not found: {local_run_dir}")

print("HF Sync completed.")
