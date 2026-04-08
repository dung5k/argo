import os
from huggingface_hub import HfApi

TOKEN = "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"
REPO_ID = "dung5k/argo_data"

api = HfApi(token=TOKEN)

print("Đang lấy danh sách các tệp trên HuggingFace...")
files = api.list_repo_files(repo_id=REPO_ID, repo_type="dataset")

# Tìm tất cả các thư mục run_... bên trong /runs/
runs_paths = set()
for f in files:
    if f.startswith("runs/run_"):
        parts = f.split('/')
        if len(parts) >= 2:
            runs_paths.add(parts[1])

print(f"Tổng số thư mục Run tìm thấy: {len(runs_paths)}")

complete_v2 = []
incomplete = []
old_runs = []

for run_folder in runs_paths:
    # Lấy danh sách file bên trong thư mục này
    run_files = [f for f in files if f.startswith(f"runs/{run_folder}/")]
    
    # Kiểm tra đặc điểm
    has_scaler_v1 = any("scaler.pkl" in f for f in run_files)
    has_scaler_v2 = any("scaler_v2.pkl" in f for f in run_files)
    has_metrix_v2 = any("training_metrix_v2.json" in f for f in run_files)
    
    # Ở V2 chuẩn, phải có scaler_v2.pkl và ít nhất 1 file weights (thường là 3 file weights của 3 phiên)
    # Đồng thời có JSON matrix.
    v2_weights = [f for f in run_files if "_weights_" in f and f.endswith(".pth")]
    
    if has_metrix_v2 and has_scaler_v2 and len(v2_weights) > 0:
        complete_v2.append((run_folder, run_files))
    elif has_scaler_v1 and not has_scaler_v2:
        old_runs.append((run_folder, run_files))
    else:
        incomplete.append((run_folder, run_files))

print(f"--- Hoàn thiện (V2 chuẩn): {len(complete_v2)}")
for r, _ in complete_v2:
    print(f"  + {r}")

print(f"--- Chưa hoàn thiện (Lỗi/Đang train): {len(incomplete)}")
for r, _ in incomplete:
    print(f"  + {r}")

print(f"--- Phiên bản CŨ (V1): {len(old_runs)}")
for r, _ in old_runs:
    print(f"  + {r}")

# Thực hiện MOVE (Cũ) và DELETE (Incomplete)
from huggingface_hub import CommitOperationCopy, CommitOperationDelete

print("\nĐang thiết lập lệnh di chuyển (Move)...")
for r, rfiles in old_runs:
    print(f"Lên lịch di chuyển thư mục cũ: {r} -> runs/old/{r}")
    ops = []
    for f in rfiles:
        new_path = f.replace(f"runs/{r}/", f"runs/old/{r}/")
        ops.append(CommitOperationCopy(src_path_in_repo=f, path_in_repo=new_path))
        ops.append(CommitOperationDelete(path_in_repo=f))
    
    if ops:
        try:
            api.create_commit(repo_id=REPO_ID, repo_type="dataset", token=TOKEN, operations=ops, commit_message=f"Archive old run {r}")
        except Exception as e:
            print(f"Lỗi move {r}: {e}")

print("\nĐang thiết lập lệnh xóa rác...")
for r, rfiles in incomplete:
    print(f"Lên lịch xóa thư mục chưa hoàn thiện: {r}")
    ops = []
    for f in rfiles:
        ops.append(CommitOperationDelete(path_in_repo=f))
        
    if ops:
        try:
            api.create_commit(repo_id=REPO_ID, repo_type="dataset", token=TOKEN, operations=ops, commit_message=f"Dọn dẹp rác {r}")
        except Exception as e:
            print(f"Lỗi delete {r}: {e}")

print("\nHoàn tất dọn dẹp!")
