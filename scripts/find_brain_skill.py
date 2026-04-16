import json, os, traceback
import numpy as np
from huggingface_hub import HfApi

VERSION_SUFFIX = "V2_2"

def find_and_apply_best_brains(target_signals=100, apply_to_config=True):
    print("🚀 Bắt đầu quá trình nội suy lấy Brain tốt nhất từ HuggingFace...")
    
    try:
        cfg = json.load(open("tg_config.json", "r", encoding="utf-8"))
        HF_TOKEN = cfg["hf_token"]
        REPO_ID = cfg["hf_repo_id"]
    except Exception as e:
        print(f"❌ Lỗi load cấu hình tg_config: {e}")
        return

    api = HfApi(token=HF_TOKEN)
    files = list(api.list_repo_files(repo_id=REPO_ID, repo_type="dataset"))

    v2_runs = set()
    for f in files:
        if f.startswith("runs/") and f"_{VERSION_SUFFIX}".upper() in f.upper():
            v2_runs.add(f.split('/')[1])

    print(f"✅ Tìm thấy {len(v2_runs)} bản run phiên bản {VERSION_SUFFIX} trên Cloud.")

    sessions_map = {
        "asian": "CFG_XAU_ASIAN_V2_1",
        "european": "CFG_XAU_LONDON_V2_1",
        "ny": "CFG_XAU_NY_V2_1"
    }

    best_selections = {}

    for sess_key, cfg_id in sessions_map.items():
        print(f"\n================== 📊 Phiên {sess_key.upper()} ==================")
        sess_runs = [r for r in v2_runs if cfg_id.upper() in r.upper()]
        
        best_wr_target = -1
        best_run = None
        best_thresh_target = None
        best_weight = None

        for r in sess_runs:
            metrix_file = f"runs/{r}/training_metrix_v2.json"
            
            # Quét file weights (.pth) trong run của HF
            w_file = None
            for fi in files:
                if fi.startswith(f"runs/{r}/") and fi.endswith(".pth") and "weights_EV" in fi:
                    w_file = fi.split('/')[-1]
                    break
            if not w_file:
                for fi in files:
                    if fi.startswith(f"runs/{r}/") and fi.endswith(".pth"):
                        w_file = fi.split('/')[-1]
                        break

            if metrix_file in files:
                try:
                    db_path = api.hf_hub_download(repo_id=REPO_ID, filename=metrix_file, repo_type="dataset")
                    with open(db_path, "r") as f:
                        data = json.load(f)

                    # Extract the lists recursively
                    arr = []
                    def extract_lists(d):
                        if isinstance(d, dict):
                            for k, v in d.items():
                                if k == "threshold_metrics" and isinstance(v, list):
                                    arr.extend(v)
                                else:
                                    extract_lists(v)
                        elif isinstance(d, list):
                            for i in d: extract_lists(i)
                    
                    extract_lists(data)
                    
                    thresholds, wrs, sigs = [], [], []
                    for item in arr:
                        if item.get("total_signals", 0) > 0:
                            thresholds.append(item.get("threshold", 0))
                            wrs.append(item.get("win_rate", 0))
                            sigs.append(item.get("total_signals", 0))
                            
                    if len(sigs) < 2:
                        continue
                        
                    idx = np.argsort(sigs)
                    s_arr = np.array(sigs)[idx]
                    t_arr = np.array(thresholds)[idx]
                    w_arr = np.array(wrs)[idx]
                    
                    if target_signals < np.min(s_arr) or target_signals > np.max(s_arr):
                        closest_idx = np.argmin(np.abs(s_arr - target_signals))
                        interp_t = t_arr[closest_idx]
                        interp_w = w_arr[closest_idx]
                    else:
                        interp_t = float(np.interp(target_signals, s_arr, t_arr))
                        interp_w = float(np.interp(target_signals, s_arr, w_arr))
                        
                    print(f"[*] {r}: Thresh@{target_signals} = {interp_t:.4f} | WinRate@{target_signals} = {interp_w:.2f}%")
                    
                    if interp_w > best_wr_target:
                        best_wr_target = interp_w
                        best_run = r
                        best_thresh_target = interp_t
                        best_weight = w_file
                except Exception as e:
                    print(f"[!] Lỗi đọc run {r}: {e}")

        if best_run:
            print(f">>> 🏆 Lựa chọn Vô Địch Phiên {sess_key.upper()}:")
            print(f"    Run ID   : {best_run}")
            print(f"    Weight   : {best_weight}")
            print(f"    Thresh   : {best_thresh_target:.4f}")
            print(f"    WinRate  : {best_wr_target:.2f}%")
            
            best_selections[sess_key] = {
                "run_id": best_run,
                "weight": best_weight,
                "thresh": round(best_thresh_target, 4),
                "winrate": round(best_wr_target, 2)
            }

    if not apply_to_config:
        return best_selections

    # ========================================================
    # ÉP CẤU HÌNH VÀO TRADING BOT
    # ========================================================
    sched_path = "data/bot_v2_brain_schedule.json"
    if not os.path.exists(sched_path):
        print("\n❌ Không tìm thấy file", sched_path)
        return best_selections
        
    with open(sched_path, "r", encoding="utf-8") as f:
        sched_data = json.load(f)

    updated_sessions = 0
    for sess_key, b in best_selections.items():
        if sess_key in sched_data.get("schedule", {}):
            cfg_node = sched_data["schedule"][sess_key]
            
            cfg_node["run_id"] = b["run_id"]
            if b["weight"]:
                cfg_node["weight_file"] = b["weight"]
            
            cfg_node["_metrix"] = f"Auto-selected (Target: {target_signals} signals) -> WR={b['winrate']}% | thresh={b['thresh']:.4f}"
            
            if "trading_config" not in cfg_node:
                cfg_node["trading_config"] = {}
                
            # Cập nhật CHỈ thông số threshold, giữ nguyên sl_pips, tp_pips
            cfg_node["trading_config"]["entry_thresh"] = b["thresh"]
            updated_sessions += 1

    with open(sched_path, "w", encoding="utf-8") as f:
        json.dump(sched_data, f, indent=4)
        
    print(f"\n🎉 Đã tự động chèn cấu hình cho {updated_sessions} phiên vào file '{sched_path}' thành công!")
    return best_selections

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--signals", type=int, default=100, help="Mốc nội suy tương đối (Mặc định 100)")
    parser.add_argument("--no-apply", action="store_true", help="Chỉ tìm, không độ vào cấu hình file json")
    args = parser.parse_args()
    
    find_and_apply_best_brains(target_signals=args.signals, apply_to_config=not args.no_apply)
