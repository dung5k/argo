# -*- coding: utf-8 -*-
import os
import json
import glob
import shutil
import time
from huggingface_hub import HfApi

print("=============================================")
print("BẮT ĐẦU QUÁ TRÌNH SETUP LIVE & CLEANUP...")

# 1. TÌM SEED 108
run_id = "run_20260514_144526_v6_LONDON_15m_TP6_SL3_Drop30_W30_FarmSeed108"
seed_dir = os.path.join("workspaces", "CFG_LTC_LONDON_V6", "runs", run_id)
seed_cfg_path = os.path.join(seed_dir, "config.json")
seed_metrics_path = os.path.join(seed_dir, "results", "training_metrics_v3.json")

print(f"1. Cập nhật bot_schedule_v6_ltc.json theo Seed 108...")
with open(seed_cfg_path, 'r', encoding='utf-8') as f:
    seed_cfg = json.load(f)

with open(seed_metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)
max_threshold = metrics["sessions"]["london"]["BEST_VLOSS"]["max_threshold"]

with open("bot_schedule_v6_ltc.json", 'r', encoding='utf-8') as f:
    bot_schedule = json.load(f)

# Update london config
bot_schedule["schedule"]["london"]["run_id"] = run_id
bot_schedule["schedule"]["london"]["trading_config"]["min_prob_thresh"] = max_threshold
bot_schedule["schedule"]["london"]["feature_engineering"] = seed_cfg["FEATURE_ENGINEERING"]

with open("bot_schedule_v6_ltc.json", 'w', encoding='utf-8') as f:
    json.dump(bot_schedule, f, indent=4)

print("  -> Đã cập nhật file bot_schedule_v6_ltc.json!")

print("\n2. Đồng bộ trọng số (Weights) tốt nhất của Seed 108 ra ngoài Root...")
brain_src = glob.glob(os.path.join(seed_dir, "brains", "*_final.pth"))[0]
brain_dst_dir = os.path.join("workspaces", "CFG_LTC_LONDON_V6", "brains")
os.makedirs(brain_dst_dir, exist_ok=True)
brain_dst = os.path.join(brain_dst_dir, os.path.basename(brain_src))
shutil.copy(brain_src, brain_dst)
print(f"  -> Đã copy {brain_src} sang {brain_dst}")

print("\n3. Xóa các run khác trên Local...")
runs_dir = os.path.join("workspaces", "CFG_LTC_LONDON_V6", "runs")
for d in os.listdir(runs_dir):
    d_path = os.path.join(runs_dir, d)
    if os.path.isdir(d_path) and d != run_id and d != "legacy_run":
        try:
            shutil.rmtree(d_path)
            print(f"  -> Đã xóa local: {d}")
        except Exception as e:
            print(f"  -> Lỗi xóa {d}: {e}")

print("\n4. Xóa các run khác trên HuggingFace (dung5k/argo_workspaces)...")
hf_token = os.environ.get("HF_TOKEN", "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")
api = HfApi(token=hf_token)
repo_id = "dung5k/argo_workspaces"
target_prefix = "workspaces/CFG_LTC_LONDON_V6/runs/"
try:
    all_files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    files_to_delete = []
    for f in all_files:
        if f.startswith(target_prefix):
            # Lấy tên thư mục run
            parts = f.replace(target_prefix, "").split("/")
            if len(parts) > 0:
                run_folder = parts[0]
                if run_folder != run_id and run_folder != "legacy_run":
                    files_to_delete.append(f)
    
    if files_to_delete:
        # Get unique folders
        folders_to_delete = list(set([f.replace(target_prefix, "").split("/")[0] for f in files_to_delete]))
        print(f"  -> Đang thực hiện lệnh xóa {len(folders_to_delete)} thư mục thừa trên HuggingFace...")
        for folder in folders_to_delete:
            if folder and folder != run_id and folder != "legacy_run":
                try:
                    api.delete_folder(
                        path_in_repo=target_prefix + folder,
                        repo_id=repo_id,
                        repo_type="dataset",
                        commit_message=f"Cleanup old london runs, deleting {folder}"
                    )
                    time.sleep(1)
                    print(f"    + Đã xóa folder {folder}...")
                except Exception as ex:
                    print(f"    + Lỗi xóa {folder}: {ex}")
        print("  -> Đã dọn dẹp sạch sẽ HuggingFace!")
    else:
        print("  -> Không có file thừa nào trên HuggingFace!")
except Exception as e:
    print(f"  -> Lỗi khi thao tác với HuggingFace: {e}")

print("=============================================")
print("HOÀN TẤT SETUP & CLEANUP!")
