from huggingface_hub import HfApi, CommitOperationCopy, CommitOperationDelete
import re

api = HfApi(token='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')
repo = 'dung5k/argo_data'
files = api.list_repo_files(repo, repo_type='dataset')

to_move = []
for f in files:
    if f.startswith('runs/run_'):
        m = re.match(r'runs/(run_(\d{8})_.*)', f)
        if m:
            date_str = m.group(2)
            if date_str < '20260412':
                to_move.append((f, f"runs/old/{m.group(1)}"))

print(f"Total files to move: {len(to_move)}")

batch_size = 400
for i in range(0, len(to_move), batch_size):
    batch = to_move[i:i+batch_size]
    ops = []
    for src, dst in batch:
        ops.append(CommitOperationCopy(src_path_in_repo=src, path_in_repo=dst))
        ops.append(CommitOperationDelete(path_in_repo=src))
    print(f"Committing batch {i//batch_size + 1}...")
    api.create_commit(
        repo_id=repo,
        repo_type="dataset",
        operations=ops,
        commit_message=f"Move old runs {i//batch_size + 1}"
    )
print("Done moving huggingface runs!")
