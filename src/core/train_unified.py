"""
train_unified.py - Unified Model v4.0: Transformer + Phoenix Restart
=====================================================================
- #1 TRANSFORMER: TransformerModel (Multi-Head Attention)
- #2 SIDEWAYS FILTER: Target chỉ học nến có biến động > 0.02%
- #3 LABEL SMOOTHING + AdamW: Chống hallucination
- #4 PHOENIX RESTART: Tái nạp bản best + pertubation chiến lược
"""
import sys
# Bắt buộc UTF-8 stdout để chạy được trên mọi máy Windows (kể cả locale cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import copy
import json
import random
import datetime
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legacy.train_ga import TransformerModel, TimeSeriesDataset, device


def train_unified_model(features, targets, num_features, run_dir, target_prefix="XAU_USD"):
    # ── Chế độ Hiệu suất (Performance Mode) ────────────────────
    perf_mode = os.environ.get("PERFORMANCE_MODE", "MAX").upper()
    if perf_mode == "LIGHT":
        import multiprocessing
        cores = multiprocessing.cpu_count()
        threads = max(1, cores // 2)
        torch.set_num_threads(threads)
        print(f"[{perf_mode} MODE] 🌿 Chế độ nhẹ nhàng: Giới hạn PyTorch dùng {threads}/{cores} CPU luồng để chạy ẩn.")
    else:
        print(f"[{perf_mode} MODE] 🚀 Chế độ Tối đa: Mở khóa hiệu suất chiếm dụng toàn bộ thiết bị.")

    """
    Train 1 model Transformer duy nhất trên toàn bộ data.
    """
    print("=======================================================")
    print("🧠 TRANSFORMER UNIFIED MODEL v5.1 (Deep Phoenix)     ")
    print("=======================================================")

    try:
        if torch.cuda.is_available():
            print(f"🖥️ [HARDWARE] Phát hiện sư tử đá GPU: {torch.cuda.get_device_name(0)}")
        else:
            print(f"🖥️ [HARDWARE] Máy này KHÔNG CÓ GPU (đang chạy bằng sức trâu CPU).")
    except: pass

    # CỐ ĐỊNH HYPERPARAMS V5
    window_size = 60
    d_model = 256
    nhead = 8
    num_attn_layers = 3
    dropout_rate = 0.2
    lr_base = 0.0003
    print(f"🤖 [V5 ARCHITECTURE] d_model={d_model}, nhead={nhead}, layers={num_attn_layers}, window={window_size}")

    # PHOENIX HYPERPARAMS
    epochs         = 10000
    batch_size     = 512
    BASE_LR        = 1e-4
    MAX_STAGNATE   = 10
    MAX_PHOENIX    = 40
    MIN_SIGNALS    = 30

    import subprocess
    try:
        import pytz
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
        import pytz

    _cfg_path = None
    import json as _json
    _base_proj = str(Path(__file__).resolve().parent.parent.parent)
    for _candidate in [os.path.join(_base_proj, "data", "bot_config_xau.json"),
                       os.path.join(_base_proj, "data", "bot_config.json")]:
        if os.path.exists(_candidate):
            _cfg_path = _candidate
            break

    _date_override = {}
    if _cfg_path:
        try:
            with open(_cfg_path, "r", encoding="utf-8") as _f:
                _c = _json.load(_f)
                
                # Cố gắng lấy từ thư mục gốc
                for _k in ["TRAIN_FROM", "TRAIN_TO", "VAL_TO", "TRAIN_START", "TRAIN_END", "VAL_END", "CONFIG_ID"]:
                    if _k in _c:
                        _date_override[_k] = _c[_k]
                        
                # Lấy từ "TRAINING" block nếu có
                if "TRAINING" in _c:
                    for _k in ["TRAIN_FROM", "TRAIN_TO", "VAL_TO", "TRAIN_START", "TRAIN_END", "VAL_END"]:
                        if _k in _c["TRAINING"]:
                            _date_override[_k] = _c["TRAINING"][_k]
        except: pass

    # Hỗ trợ cả TRAIN_FROM và TRAIN_START cho tương thích với bộ config mới
    t_start = _date_override.get("TRAIN_START") or _date_override.get("TRAIN_FROM")
    t_end   = _date_override.get("TRAIN_END") or _date_override.get("TRAIN_TO")
    v_end   = _date_override.get("VAL_END") or _date_override.get("VAL_TO")

    if t_start and t_end and v_end:
        train_start = pd.Timestamp(t_start, tz='UTC')
        train_end   = pd.Timestamp(t_end,   tz='UTC')
        val_start   = train_end
        val_end     = pd.Timestamp(v_end,     tz='UTC') + pd.Timedelta(days=1)
        print(f"\n📅 [DATE RANGE FROM CONFIG]")
    else:
        now_utc     = pd.Timestamp.now(tz='UTC')
        val_end     = now_utc
        val_start   = val_end   - pd.Timedelta(days=4)
        train_end   = val_start
        train_start = train_end - pd.Timedelta(days=90)
        print(f"\n📅 [ROLLING WINDOW SPLIT]")

    print(f"   Train : {train_start.strftime('%Y-%m-%d')} → {train_end.strftime('%Y-%m-%d')}")
    print(f"   Test  : {val_start.strftime('%Y-%m-%d')} → {val_end.strftime('%Y-%m-%d')}")

    features_utc = features.tz_convert('UTC')
    targets_utc = targets.tz_convert('UTC')

    train_mask = (features_utc.index >= train_start) & (features_utc.index < train_end)
    val_mask   = (features_utc.index >= val_start)   & (features_utc.index < val_end)

    train_features = features_utc[train_mask]
    train_targets  = targets_utc[train_mask]
    val_features   = features_utc[val_mask]
    val_targets    = targets_utc[val_mask]

    print(f"   -> Train: {len(train_features):,} nến | Test thực chiến: {len(val_features):,} nến")

    if len(train_features) <= window_size or len(val_features) <= window_size:
        print("⚠️ Dữ liệu quá cạn! Kiểm tra lại thời gian cào data.")
        return


    train_labels = train_targets['target'].values
    n_total = len(train_labels)
    n_buy  = (train_labels == 1).sum()
    n_sell = (train_labels == 0).sum()
    weight_sell = n_total / (2.0 * n_sell) if n_sell > 0 else 1.0
    weight_buy  = n_total / (2.0 * n_buy)  if n_buy  > 0 else 1.0
    class_weights = torch.tensor([weight_sell, weight_buy], dtype=torch.float32).to(device)
    print(f"⚖️ [Class Weight] SELL={weight_sell:.3f}, BUY={weight_buy:.3f}")
    print(f"   ({n_sell:,} Sell | {n_buy:,} Buy trong {n_total:,} mẫu Train)")

    train_dataset = TimeSeriesDataset(train_features, train_targets, window_size)
    val_dataset   = TimeSeriesDataset(val_features,   val_targets,   window_size)
    train_loader  = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader    = DataLoader(val_dataset,   batch_size=batch_size, shuffle=False)

    meta_path = rf"C:\argo\data\feature_meta_{target_prefix}.json"
    num_xau_features = None
    target_name = target_prefix.lower().replace("_", "")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
            num_xau_features = meta.get("num_xau_features", None)
            target_name = meta.get("target_prefix", target_prefix).lower().replace("_", "")
        print(f"🧬 [DUAL-STREAM] TARGET ({target_name}): {num_xau_features} | Macro: {num_features - (num_xau_features or 0)}")

    model = TransformerModel(
        num_features, d_model=d_model, nhead=nhead,
        num_layers=num_attn_layers, dropout_rate=dropout_rate,
        num_xau_features=num_xau_features
    ).to(device)

    # === [RESUME] LOAD CHECKPOINT ===
    runs_base = "C:/argo/logs/runs"
    
    # Chỉ kế thừa checkpoint TỪ CÙNG MỘT CONFIG_ID
    cfg_id = _date_override.get("CONFIG_ID", "DEFAULT")
    checkpoint_candidates = sorted(
        [p for p in Path(runs_base).glob(f"**/{target_name}_unified_weights*.pth") if "old" not in p.parts and cfg_id in str(p)],
        key=lambda p: p.parent.name,
        reverse=True
    ) if Path(runs_base).exists() else []

    global_best_score  = 0.0
    global_best_val_loss = float('inf')
    best_thresholds  = [0.50, 0.50, 0.50, 0.50]
    best_wrs         = [0.0, 0.0, 0.0, 0.0]
    best_totals      = [0, 0, 0, 0]
    best_max_thresh  = 0.50

    def calc_strats(wrs_arr, avg_v_loss):
        return {
            "L3_1.4_L4_1.0": (1.4 * wrs_arr[2] + 1.0 * wrs_arr[3]) / 2.4,
            "L3_1.1_L4_1.0": (1.1 * wrs_arr[2] + 1.0 * wrs_arr[3]) / 2.1,
            "BEST_VLOSS": -avg_v_loss
        }

    resumed = False
    if checkpoint_candidates:
        latest_ckpt = checkpoint_candidates[int(len(checkpoint_candidates)>1)] # Dùng ckpt tốt nhất hoặc bản baseline
        print(f"\n♻️  Tìm thấy checkpoint: {latest_ckpt}")
        try:
            state = torch.load(str(latest_ckpt), map_location=device, weights_only=True)
            
            current_state = model.state_dict()
            matched_state = {}
            for k, v in state.items():
                if k in current_state and current_state[k].shape == v.shape:
                    matched_state[k] = v
                else:
                    print(f"    ⚠️ Cắt bỏ trọng số layer: {k} (Kích thước đổi do Data mới)")
            
            current_state.update(matched_state)
            model.load_state_dict(current_state)
            
            resumed = True
            print(f"    ✅ TRANSFER LEARNING: Kế thừa Core Memory từ {latest_ckpt.parent.name}")

            print(f"    🔄 Đang tính toán Baseline trên dữ liệu Validate HIỆN TẠI...")
            model.eval()
            all_probs_up = []
            all_labels   = []
            temp_val_loss = 0.0
            temp_criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.15).to(device)
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_y = batch_y.view(-1)
                    outputs = model(batch_x)
                    loss = temp_criterion(outputs, batch_y)
                    temp_val_loss += loss.item()
                    probs = F.softmax(outputs.data, dim=1)
                    all_probs_up.append(probs[:, 1].cpu())
                    all_labels.append(batch_y.cpu())
            
            avg_base_val_loss = temp_val_loss / len(val_loader) if len(val_loader) > 0 else 0
            all_probs_up = torch.cat(all_probs_up)
            all_labels   = torch.cat(all_labels)
            
            max_thresh = 0.50
            for t_int in range(99, 51, -1):
                t = t_int / 100.0
                n_buy_sig  = (all_probs_up > t).sum().item()
                n_sell_sig = (all_probs_up < (1.0 - t)).sum().item()
                if (n_buy_sig + n_sell_sig) >= MIN_SIGNALS:
                    max_thresh = t
                    break

            step = (max_thresh - 0.50) / 3 if max_thresh > 0.50 else 0
            thresholds = [round(0.50 + step * i, 4) for i in range(4)]

            wrs, totals_t = [], []
            for t in thresholds:
                lo = 1.0 - t
                b = all_probs_up > t
                s = all_probs_up < lo
                n = b.sum().item() + s.sum().item()
                c = (all_labels[b] == 1).sum().item() + (all_labels[s] == 0).sum().item()
                wrs.append(c / n if n > 0 else 0.0)
                totals_t.append(n)

            if totals_t[3] >= MIN_SIGNALS:
                baseline_scores = calc_strats(wrs, avg_base_val_loss)
                top_configs = {}
                for s_name, s_val in baseline_scores.items():
                    top_configs[s_name] = {
                        "score": s_val,
                        "state_dict": copy.deepcopy(model.state_dict()),
                        "thresholds": thresholds[:],
                        "wrs": wrs[:],
                        "totals": totals_t[:],
                        "max_thresh": max_thresh
                    }
                global_best_score = baseline_scores["L3_1.4_L4_1.0"]
                global_best_val_loss = avg_base_val_loss
                best_wrs = wrs
                best_totals = totals_t
                best_thresholds = thresholds
                best_max_thresh = max_thresh
                thr_str = " | ".join(f">{t*100:.0f}%: {wrs[i]*100:.1f}%({totals_t[i]}L)" for i, t in enumerate(thresholds))
                print(f"    📊 Baseline WR: {global_best_score*100:.1f}% | VLoss: {avg_base_val_loss:.4f} | MaxTh: {max_thresh:.2f}")
                print(f"    {thr_str}")
            else:
                print("    ⚠️ Baseline không đủ tập mẫu, xếp hạng từ 0")
        except Exception as e:
            print(f"    ⚠️  Không thể load ({e}) → Khởi tạo model mới.")
    else:
        print("\n📌 Không có checkpoint trước. Khởi tạo model mới.")

    model_file = os.path.join(run_dir, f"{target_name}_unified_weights.pth")

    best_state_dict = copy.deepcopy(model.state_dict())

    if 'top_configs' not in locals():
        top_configs = {
            "L3_1.4_L4_1.0": None,
            "L3_1.1_L4_1.0": None,
            "BEST_VLOSS": None
        }

    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.15)

    def make_optimizer(lr=BASE_LR):
        return optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)

    def make_scheduler(opt):
        return optim.lr_scheduler.ReduceLROnPlateau(opt, mode='max', patience=10, factor=0.5, min_lr=1e-6)

    optimizer = make_optimizer()
    scheduler = make_scheduler(optimizer)

    def save_blackbox(epoch_num, is_interrupted=False):
        top_configs_meta = []
        for s_name, cfg in top_configs.items():
            if cfg is not None:
                top_configs_meta.append({
                    "strategy": s_name,
                    "score": cfg["score"] * 100,
                    "max_thresh": cfg["max_thresh"],
                    "thresholds": cfg["thresholds"],
                    "win_rates": [wr * 100 for wr in cfg["wrs"]],
                    "totals": cfg["totals"]
                })

        blackbox_file = os.path.join(run_dir, "training_metrix.json")
        data = {
            "target": target_name,
            "status": "STOPPED" if is_interrupted else "RUNNING_OR_DONE",
            "epochs_trained": epoch_num,
            "best_winrate": global_best_score * 100,
            "best_val_loss": global_best_val_loss,
            "best_max_thresh": best_max_thresh,
            "thresholds": best_thresholds,
            "win_rates": [wr * 100 for wr in best_wrs],
            "totals": best_totals,
            "top_configs_saved": top_configs_meta
        }
        try:
            with open(blackbox_file, "w", encoding="utf-8") as bf:
                json.dump(data, bf, indent=4, ensure_ascii=False)
        except: pass

        def hf_sync_best_weights():
            try:
                import sys, os
                base_dir = os.path.dirname(os.path.dirname(run_dir))
                orchestration_dir = os.path.join(base_dir, "src", "orchestration")
                if orchestration_dir not in sys.path:
                    sys.path.insert(0, orchestration_dir)
                from hf_sync import push_runs
                ok = push_runs()
                if ok:
                    print("    [HF] Đã đồng bộ trọng số mới lên kho dữ liệu HuggingFace.")
            except Exception as e:
                pass
        
        import threading
        threading.Thread(target=hf_sync_best_weights, daemon=True).start()

    if resumed and global_best_score > 0:
        torch.save(model.state_dict(), model_file)
        for s_name in top_configs.keys():
            torch.save(model.state_dict(), os.path.join(run_dir, f"{target_name}_unified_weights_{s_name}.pth"))
        save_blackbox(0)
        print(f"    💾 Đã lưu các bản đầu tiên (baseline) vào run hiện tại.")

    def apply_perturbation(phoenix_num):
        nonlocal optimizer, scheduler, batch_size
        strat = random.choice(['A', 'B', 'C', 'D'])
        if strat == 'A':
            spike_lr = random.uniform(2e-4, 8e-4)
            optimizer = make_optimizer(lr=spike_lr)
            scheduler = make_scheduler(optimizer)
            print(f"  🔥 Chiến lược A: LR Spike → LR={spike_lr:.1e} (thoát local minima)")
        elif strat == 'B':
            noise_sigma = random.uniform(0.001, 0.005)
            with torch.no_grad():
                for param in model.parameters():
                    param.add_(torch.randn_like(param) * noise_sigma)
            optimizer = make_optimizer(lr=BASE_LR)
            scheduler = make_scheduler(optimizer)
            print(f"  🌊 Chiến lược B: Noise Injection σ={noise_sigma:.4f} (khám phá vùng lân cận)")
        elif strat == 'C':
            fine_lr = random.uniform(5e-5, 2e-4)
            optimizer = optim.AdamW(model.parameters(), lr=fine_lr, weight_decay=random.uniform(1e-3, 5e-3))
            scheduler = make_scheduler(optimizer)
            print(f"  🎯 Chiến lược C: Fine-tune Sâu → LR={fine_lr:.1e}, WD tăng (tinh chỉnh precision)")
        elif strat == 'D':
            new_batch = random.choice([128, 256, 384])
            batch_size = new_batch
            print(f"  🎲 Chiến lược D: Batch Shuffle → batch_size={new_batch} (gradient đa dạng hơn)")
            return True
        return False

    epochs_no_improve = 0
    phoenix_count     = 0
    total_epoch       = 0
    need_reload_loader = False

    import time
    try:
        while phoenix_count <= MAX_PHOENIX:
            epoch_start_time = time.time()

            if need_reload_loader:
                train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
                need_reload_loader = False

            model.train()
            train_loss = 0.0
            for batch_x, batch_y in train_loader:
                batch_y = batch_y.view(-1)
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                train_loss += loss.item()

            model.eval()
            correct, total = 0, 0
            val_loss = 0.0
            all_probs_up = []
            all_labels   = []

            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_y = batch_y.view(-1)
                    outputs = model(batch_x)
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    total += batch_y.size(0)
                    correct += (predicted == batch_y).sum().item()
                    probs = F.softmax(outputs.data, dim=1)
                    all_probs_up.append(probs[:, 1].cpu())
                    all_labels.append(batch_y.cpu())

            all_probs_up = torch.cat(all_probs_up)
            all_labels   = torch.cat(all_labels)

            max_thresh = 0.50
            for t_int in range(99, 51, -1):
                t = t_int / 100.0
                n_buy_sig  = (all_probs_up > t).sum().item()
                n_sell_sig = (all_probs_up < (1.0 - t)).sum().item()
                if (n_buy_sig + n_sell_sig) >= MIN_SIGNALS:
                    max_thresh = t
                    break

            step = (max_thresh - 0.50) / 3 if max_thresh > 0.50 else 0
            thresholds = [round(0.50 + step * i, 4) for i in range(4)]

            wrs, totals_t = [], []
            for t in thresholds:
                lo = 1.0 - t
                b = all_probs_up > t
                s = all_probs_up < lo
                n = b.sum().item() + s.sum().item()
                c = (all_labels[b] == 1).sum().item() + (all_labels[s] == 0).sum().item()
                wrs.append(c / n if n > 0 else 0.0)
                totals_t.append(n)

            val_acc      = correct / total if total > 0 else 0.0
            avg_val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0
            cur_lr       = optimizer.param_groups[0]['lr']
            total_epoch += 1

            phoenix_tag = f"[P{phoenix_count}]" if phoenix_count > 0 else ""
            epoch_time = time.time() - epoch_start_time
            print(f"Epoch {total_epoch:04d} {phoenix_tag}| VLoss: {avg_val_loss:.4f} | LR: {cur_lr:.2e} | WR: {val_acc*100:.1f}% | MaxTh: {max_thresh:.2f} | Time: {epoch_time:.1f}s")
            thr_str = " | ".join(f">{t*100:.0f}%: {wrs[i]*100:.1f}%({totals_t[i]}L)" for i, t in enumerate(thresholds))
            print(f"  {thr_str}")

            scheduler.step(wrs[3] if totals_t[3] > 0 else avg_val_loss)

            if avg_val_loss < global_best_val_loss:
                global_best_val_loss = avg_val_loss

            is_statistically_valid = totals_t[3] >= MIN_SIGNALS
            current_scores = calc_strats(wrs, avg_val_loss)
            improved_strategies = []

            if is_statistically_valid:
                for s_name, s_val in current_scores.items():
                    if top_configs[s_name] is None or s_val > top_configs[s_name]["score"]:
                        top_configs[s_name] = {
                            "score": s_val,
                            "state_dict": copy.deepcopy(model.state_dict()),
                            "thresholds": thresholds[:],
                            "wrs": wrs[:],
                            "totals": totals_t[:],
                            "max_thresh": max_thresh
                        }
                        
                        rank_file = os.path.join(run_dir, f"{target_name}_unified_weights_{s_name}.pth")
                        torch.save(top_configs[s_name]["state_dict"], rank_file)
                        improved_strategies.append(s_name)

                if improved_strategies:
                    epochs_no_improve = 0
                    valid_cfgs = [c for c in top_configs.values() if c is not None]
                    best_cfg = max(valid_cfgs, key=lambda x: x["score"])
                    global_best_score = best_cfg["score"]
                    best_thresholds  = best_cfg["thresholds"]
                    best_wrs         = best_cfg["wrs"]
                    best_totals      = best_cfg["totals"]
                    best_max_thresh  = best_cfg["max_thresh"]
                    best_state_dict  = copy.deepcopy(best_cfg["state_dict"])

                    torch.save(best_state_dict, model_file)
                            
                    save_blackbox(total_epoch)
                    imp_str = ', '.join(improved_strategies)
                    print(f"  🏆 ĐỈNH MỚI CHO CHIẾN THUẬT: [{imp_str}]. MaxTh={max_thresh:.2f} "
                          + " | ".join(f">{t*100:.0f}%: {wrs[i]*100:.1f}%({totals_t[i]}L)"
                                        for i, t in enumerate(thresholds)))
                else:
                    epochs_no_improve += 1
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= MAX_STAGNATE:
                phoenix_count += 1
                if phoenix_count > MAX_PHOENIX:
                    print(f"\n🦅 [PHOENIX] Đã tái sinh {MAX_PHOENIX} lần mà không vượt đỉnh {global_best_score*100:.1f}%.")
                    break

                valid_cfgs = [c for c in top_configs.values() if c is not None]
                chosen_cfg = random.choice(valid_cfgs) if valid_cfgs else {"score": global_best_score, "state_dict": best_state_dict}
                
                print(f"\n🔁 [PHOENIX #{phoenix_count}] Kẹt {epochs_no_improve} epoch. Tái sinh ngẫu nhiên về cấu hình tốt nhất của 1 chiến thuật (Score={chosen_cfg['score']*100:.1f}%)...")
                model.load_state_dict(copy.deepcopy(chosen_cfg['state_dict']))
                epochs_no_improve = 0
                need_reload_loader = apply_perturbation(phoenix_count)
                print(f"   → Tiếp tục khám phá (còn {MAX_PHOENIX - phoenix_count} lần tái sinh)\n")

    except KeyboardInterrupt:
        print("\n⚡ [KHẨN CẤP] Dừng khẩn cấp. Đang lưu Hộp đen...")
        save_blackbox(total_epoch, is_interrupted=True)
        model.load_state_dict(best_state_dict)
        torch.save(best_state_dict, model_file)

    print(f"\n✅ HOÀN TẤT → Best Score (L3/L4/Vloss): {global_best_score*100:.1f}% | Lưu: {model_file}")


if __name__ == "__main__":
    import sys
    import json

    BASE_PROJ_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    config_path = None
    for arg in sys.argv[1:]:
        if arg.endswith('.json'):
            config_path = arg if os.path.isabs(arg) else os.path.join(BASE_PROJ_DIR, arg)
            break
    if not config_path:
        for candidate in ["data/bot_config_xau.json", "data/bot_config.json"]:
            p = os.path.join(BASE_PROJ_DIR, candidate)
            if os.path.exists(p):
                config_path = p
                break

    TARGET_PREFIX = "XAUUSD"
    CONFIG_ID = "DEFAULT"
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            TARGET_PREFIX = cfg.get("TARGET_PREFIX", "XAUUSD")
            CONFIG_ID = cfg.get("CONFIG_ID", "DEFAULT")

    print(f"[INIT] Config: {config_path}")
    print(f"[INIT] TARGET_PREFIX: {TARGET_PREFIX}")

    data_path = "C:/argo/data"
    features_path = os.path.join(data_path, f"final_features_{TARGET_PREFIX}.parquet")
    target_path   = os.path.join(data_path, f"target_direction_{TARGET_PREFIX}.parquet")

    if not os.path.exists(target_path):
        fallback_target = os.path.join(data_path, "target_direction.parquet")
        if os.path.exists(fallback_target):
            target_path = fallback_target

    print(f"[INIT] Tìm file features: {features_path}")

    # === [DIAGNOSTIC] ===
    print("\n🔍 --- CHẨN ĐOÁN DỮ LIỆU ĐẦU VÀO TẠI CLIENT ---")
    print(f"  [>] Config đang dùng: {os.path.basename(config_path) if config_path else 'None'} | CONFIG_ID: {CONFIG_ID}")
    if config_path:
        print(f"  [>] DATASET_SUFFIX: {cfg.get('DATA_SOURCE', {}).get('DATASET_SUFFIX', 'UNKNOWN')}")
    import glob
    raw_files = glob.glob(os.path.join(data_path, "*_1m_*.parquet"))
    print(f"  [>] Tồn tại cục dữ liệu thô (Parquet) trong data/:")
    if not len(raw_files):
        print(f"     (Không có file dữ liệu gốc)")
    else:
        for f in raw_files:
            sz = os.path.getsize(f) / (1024*1024)
            print(f"     - {os.path.basename(f)} ({sz:.1f} MB)")
    if os.path.exists(features_path):
        fsz = os.path.getsize(features_path) / (1024*1024)
        print(f"  [>] File Features đã gộp: {os.path.basename(features_path)} ({fsz:.1f} MB)")
    print("-------------------------------------------------\n")


    if os.path.exists(features_path):
        features = pd.read_parquet(features_path)
        targets  = pd.read_parquet(target_path)
        num_features = features.shape[1]

        run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_clean = TARGET_PREFIX.lower().replace("_", "")
        run_name = f"run_{run_timestamp}_{target_clean}_{CONFIG_ID}_TRANSFORMER"
        base_runs_dir = "C:/argo/logs/runs"
        run_dir  = os.path.join(base_runs_dir, run_name)
        os.makedirs(run_dir, exist_ok=True)
        
        class TeeLogger:
            def __init__(self, filename):
                self.terminal = sys.stdout
                self.log = open(filename, "w", encoding="utf-8", buffering=1)
            def write(self, message):
                self.terminal.write(message)
                self.log.write(message)
            def flush(self):
                self.terminal.flush()
                self.log.flush()
        sys.stdout = TeeLogger(os.path.join(run_dir, "train.log"))
        
        print(f"📁 Tạo thư mục run: {run_name}")

        import glob, shutil
        
        scaler_src = os.path.join(data_path, "scaler.pkl")
        if os.path.exists(scaler_src):
            shutil.copy(scaler_src, os.path.join(run_dir, "scaler.pkl"))
            print(f"📦 Đã đóng gói kèm scaler.pkl (Bộ Kính Data) vào thư mục Run.")
            print("☁️ Đang đồng bộ CẤP TỐC scaler.pkl lên Đám mây HuggingFace để mồi sẵn cho Live Bot...")
            try:
                src_path = os.path.join(BASE_PROJ_DIR, "src")
                if src_path not in sys.path:
                    sys.path.insert(0, src_path)
                from orchestration.hf_sync import _load_config
                from huggingface_hub import HfApi
                hf_cfg = _load_config()
                if hf_cfg and "hf_token" in hf_cfg and "hf_repo_id" in hf_cfg:
                    api = HfApi(token=hf_cfg["hf_token"])
                    target_repo_path = f"runs/{run_name}/scaler.pkl"
                    api.upload_file(
                        path_or_fileobj=os.path.join(run_dir, "scaler.pkl"),
                        path_in_repo=target_repo_path,
                        repo_id=hf_cfg["hf_repo_id"],
                        repo_type="dataset",
                        commit_message=f"bot: Đẩy NHANH scaler.pkl lên mồi trước phục vụ Live Bot ({run_name})"
                    )
                    print(f"✅ Đã tải NHANH scaler.pkl thành công vào: '{target_repo_path}' !")
                else:
                    print("⚠️ Cảnh báo: Thiếu config HuggingFace (hf_token), bỏ qua upload.")
            except Exception as e:
                print(f"❌ Lỗi khi tải sơ khai scaler.pkl lên HuggingFace: {e}")
        else:
            print(f"⚠️ CẢNH BÁO MẤT ROOT SCALER: Không tìm thấy {scaler_src}")

        old_dir = os.path.join(base_runs_dir, "old")
        os.makedirs(old_dir, exist_ok=True)
        type_folders = [d for d in glob.glob(os.path.join(base_runs_dir, f"run_*_{target_clean}_*TRANSFORMER")) if os.path.isdir(d)]
        type_folders.sort(reverse=True)
        move_folders = type_folders[3:]
        for folder in move_folders:
            folder_name = os.path.basename(folder)
            dest = os.path.join(old_dir, folder_name)
            try:
                shutil.move(folder, dest)
                print(f"🧹 Đã di chuyển bản cũ vào kho lưu trữ (Archive): {folder_name}")
            except Exception as e:
                pass

        train_unified_model(features, targets, num_features, run_dir, target_prefix=TARGET_PREFIX)

        print("☁️ KẾT THÚC TRAIN: Đang đồng bộ fallback toàn bộ phiên bản trọng số cuối cùng lên HuggingFace...")
        try:
            src_path = os.path.join(BASE_PROJ_DIR, "src")
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            from orchestration.hf_sync import push_runs
            push_runs()
        except Exception as e:
            print(f"❌ Lỗi khi tải bản chốt sổ lên HuggingFace: {e}")

    else:
        print(f"❌ Chưa có file features ({features_path})! Hãy chạy feature_engineering.py trước.")
