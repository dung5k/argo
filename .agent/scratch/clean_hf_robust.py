import sys, re, time
from huggingface_hub import HfApi, CommitOperationCopy, CommitOperationDelete

api = HfApi(token='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')
repo = 'dung5k/argo_data'
print("Fetching files...")
files = api.list_repo_files(repo, repo_type='dataset')
to_move = []
for f in files:
    if f.startswith('runs/run_'):
        m = re.match(r'runs/(run_(\d{8})_.*)', f)
        if m:
            date_str = m.group(2)
            if date_str < '20260412':
                to_move.append((f, f'runs/old/{m.group(1)}'))

print(f'Total {len(to_move)} files to move.')
batch_size = 20
for i in range(0, len(to_move), batch_size):
    batch = to_move[i:i+batch_size]
    ops = []
    for src, dst in batch:
        ops.append(CommitOperationCopy(src_path_in_repo=src, path_in_repo=dst))
        ops.append(CommitOperationDelete(path_in_repo=src))
    print(f'Batch {i//batch_size+1} ({i}/{len(to_move)})...')
    
    retries = 3
    for r in range(retries):
        try:
            api.create_commit(repo_id=repo, repo_type='dataset', operations=ops, commit_message=f'Move runs_old {i}')
            break
        except Exception as e:
            print(f'Error on retry {r}:', e)
            if r == retries - 1:
                print('Failed completely')
                sys.exit(1)
            time.sleep(5)
print('Done!')
