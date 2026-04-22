import sys
import datetime
from pathlib import Path

# Thêm src d? truy c?p các module h? tr?
base_dir = Path(r'c:/Users/Le Anh Dung/OneDrive/Apps/ck/forex_predictor')
sys.path.insert(0, str(base_dir / 'src' / 'orchestration'))
from hf_sync import _load_config
from huggingface_hub import HfApi, CommitOperationCopy, CommitOperationDelete

def move_old_runs():
    cfg = _load_config()
    api = HfApi(token=cfg['hf_token'])
    repo_id = cfg['hf_repo_id']
    
    print(f"B?t ??u qut th? m?c runs trn repo: {repo_id}...")
    
    # L?y danh sch file
    files_info = api.list_repo_tree(repo_id=repo_id, repo_type='dataset', path_in_repo='runs')
    
    # Gom File theo Run Folder
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=3)
    cutoff_str = cutoff_date.strftime("%Y%m%d")
    
    folders_to_move = set()
    all_files = []
    
    for f in files_info:
        # F.path typically "runs/run_YYYYMMDD_HHMMSS_xyz/..."
        # Chúng ta ch? quan tâm nh?ng th? m?c con c?a runs/, ho?c các file r?c
        parts = f.path.split('/')
        if len(parts) >= 2 and parts[0] == 'runs':
            if parts[1] == 'old' or parts[1] == 'V2_2026_DATA':
                continue # b? qua
                
            all_files.append(f.path)
            # N?u part l m?t run folder "run_YYYYMMDD_HHMM..."
            run_name = parts[1]
            if run_name.startswith("run_"):
                date_part = run_name.split('_')[1]
                if date_part.isdigit() and len(date_part) == 8:
                    if date_part <= cutoff_str:
                        folders_to_move.add(run_name)
    
    if not folders_to_move:
        print("Khng c folder run no qu 3 ngy c?n di chuy?n.")
        return
        
    print(f"Tm th?y {len(folders_to_move)} folders c? n?m: {folders_to_move}")
    
    # Chu?n b? cc Operation cho m?t Commit b? l?n
    operations = []
    for fpath in all_files:
        run_name = fpath.split('/')[1]
        if run_name in folders_to_move:
            dest_path = fpath.replace(f"runs/{run_name}", f"runs/old/{run_name}", 1)
            operations.append(CommitOperationCopy(src_path_in_repo=fpath, path_in_repo=dest_path))
            operations.append(CommitOperationDelete(path_in_repo=fpath))
            
    if operations:
        print(f"Dang th?c hi?n Commit v?i {len(operations)} operations...")
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=operations,
            commit_message=f"Move {len(folders_to_move)} old runs to runs/old/"
        )
        print("Di chuy?n thnh cng!")
    else:
        print("Khng c t?p no h?p l?.")

if __name__ == '__main__':
    move_old_runs()
