"""
train_v1_5.py - Version 1.5.1: V1 Core + V2 MOE Sessions + Curriculum Learning Masking
========================================================================================
- Data Pipeline & Models: TransformerModel (V1)
- Loss & Evaluation: CrossEntropyLoss (V1) + L3/L4 Win Rate Calculations
- Architecture: 100% MOE v2 (chia dữ liệu ra 3 Sessions: Asia, London, NY)
- v1.5.1: Curriculum Learning Data Masking (zero-out theo config CURRICULUM_MASKING)
"""
import sys
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
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

RUN_VERSION_DESC = "Focal Loss & Thông báo Telegram chi tiết (v1.5)"

class FocalLoss(nn.Module):
    def __init__(self, weight=None, gamma=2.0, label_smoothing=0.0):
        super().__init__()
        self.weight = weight
        self.gamma = gamma
        self.label_smoothing = label_smoothing

    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, weight=self.weight, reduction='none', label_smoothing=self.label_smoothing)
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# Import Core Model V1
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.legacy.train_ga import TransformerModel, device
from src.orchestration.hf_sync import push_runs
from src.training_v1_5.curriculum_masking import apply_curriculum_mask, resolve_masked_indices

# ============================================================
# Dataset V1.5: Lấy Labels V1 x Tách Phiên V2
# ============================================================
class TimeSeriesDatasetV1_5(Dataset):
    def __init__(self, features: pd.DataFrame, targets: pd.DataFrame, window_size: int = 60):
        self.window_size = window_size
        
        # Mapping Sessions
        hours = features.index.tz_convert('UTC').hour.values
        session_arr = np.zeros_like(hours, dtype=np.int64) # 0: Asia (0-7h)
        session_arr[(hours >= 8) & (hours < 13)] = 1       # 1: London (8-12h)
        session_arr[(hours >= 13)] = 2                     # 2: NY (13-23h)
        
        # Data tensors
        self.features_tensor = torch.tensor(features.values, dtype=torch.float32).to(device)
        self.labels_tensor = torch.tensor(targets['target'].values, dtype=torch.long).to(device)
        self.session_tensor = torch.tensor(session_arr, dtype=torch.long).to(device)
        
    def __len__(self):
        return len(self.features_tensor) - self.window_size
        
    def __getitem__(self, idx):
        x = self.features_tensor[idx : idx + self.window_size]
        target_idx = idx + self.window_size - 1
        y = self.labels_tensor[target_idx]
        s = self.session_tensor[target_idx]
        return x, y, s

# ============================================================
# Phoenix Restarter (Modified for V1.5)
# ============================================================
class PhoenixRestartV1_5:
    def __init__(self, model, base_lr, max_phoenix, max_stagnate):
        self.model = model
        self.base_lr = base_lr
        self.max_phoenix = max_phoenix
        self.max_stagnate = max_stagnate
        
        self.optimizer = optim.AdamW(self.model.parameters(), lr=base_lr, weight_decay=1e-3)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='max', patience=10, factor=0.5, min_lr=1e-6)
        
        self.epochs_no_improve = 0
        self.phoenix_count = 0
        self.exhausted = False

    @property
    def remaining(self):
        return self.max_phoenix - self.phoenix_count

    def notify_no_improve(self):
        self.epochs_no_improve += 1
        if self.epochs_no_improve >= self.max_stagnate:
            self.phoenix_count += 1
            if self.phoenix_count > self.max_phoenix:
                self.exhausted = True
                return False
            return True
        return False

    def reset_stagnation(self):
        self.epochs_no_improve = 0
        
    def get_lr(self):
        return self.optimizer.param_groups[0]['lr']

    def apply_perturbation(self, fallback_state_dict, s_name=None, history_buffer=None):
        self.model.load_state_dict(copy.deepcopy(fallback_state_dict))
        self.reset_stagnation()
        
        strat = 'A'
        try:
            if s_name and history_buffer:
                from src.training_v1_5.ai_supervisor import ask_ai_for_phoenix_strategy
                ai_decision = ask_ai_for_phoenix_strategy(s_name, history_buffer, str(_ROOT))
                if ai_decision:
                    strat = ai_decision.get("strategy", "A")
                    print(f"  ↪ 🤖 [AI Quyết Định Phoenix] Chọn Strategy {strat}: {ai_decision.get('reason')}")
                    tel_msg = ai_decision.get("telegram_message")
                    if tel_msg:
                        try:
                            import requests
                            tg_cfg_path = os.path.join(str(_ROOT), "tg_config.json")
                            if os.path.exists(tg_cfg_path):
                                with open(tg_cfg_path, "r", encoding='utf-8') as f:
                                    tg_cfg = json.load(f)
                                bot_token = tg_cfg.get("bot_token")
                                chat_ids = tg_cfg.get("allowed_user_ids", [])
                                if bot_token and chat_ids:
                                    tele_content = f"🤖 <b>[PHOENIX AI - {s_name.upper()}]</b>\n\n{tel_msg}"
                                    for chat_id in chat_ids:
                                        requests.post(
                                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                            data={"chat_id": chat_id, "text": tele_content, "parse_mode": "HTML"},
                                            timeout=5
                                        )
                        except Exception as e:
                            print(f"[TELEGRAM ERROR in Phoenix] {e}")
            else:
                strat = random.choice(['A', 'B', 'C', 'D'])
        except Exception as e:
            print(f"[PHOENIX] Lỗi gọi AI, fallback random: {e}")
            strat = random.choice(['A', 'B', 'C', 'D'])

        action = ""
        if strat == 'A':
            spike_lr = random.uniform(2e-4, 8e-4)
            self.optimizer = optim.AdamW(self.model.parameters(), lr=spike_lr, weight_decay=1e-3)
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='max', patience=10, factor=0.5, min_lr=1e-6)
            action = f"🔥 Spike LR={spike_lr:.1e}"
        elif strat == 'B':
            noise_sigma = random.uniform(0.001, 0.005)
            with torch.no_grad():
                for param in self.model.parameters():
                    param.add_(torch.randn_like(param) * noise_sigma)
            self.optimizer = optim.AdamW(self.model.parameters(), lr=self.base_lr, weight_decay=1e-3)
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='max', patience=10, factor=0.5, min_lr=1e-6)
            action = f"🌊 Noise σ={noise_sigma:.4f}"
        elif strat == 'C':
            fine_lr = random.uniform(5e-5, 2e-4)
            self.optimizer = optim.AdamW(self.model.parameters(), lr=fine_lr, weight_decay=random.uniform(1e-3, 5e-3))
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='max', patience=10, factor=0.5, min_lr=1e-6)
            action = f"🎯 Fine-Tune LR={fine_lr:.1e}"
        elif strat == 'D':
            action = "🎲 Batch Shuffle (Logic retained upstream)"
        return action

# ============================================================
# Main Training Function V1.5
# ============================================================
def train_unified_v1_5(features, targets, num_features, run_dir, config=None, target_prefix="XAU_USD"):
    print("=======================================================")
    print(f"🧠 TRANSFORMER V1.5.1 [{target_prefix}]: MOE + CURRICULUM ")
    print("=======================================================")
    
    cfg = config or {}
    epochs         = 10000
    batch_size     = 512
    window_size    = 60
    d_model        = 256
    nhead          = 8
    num_attn_layers = 3
    dropout_rate   = 0.2
    BASE_LR        = 0.0003
    MAX_STAGNATE   = 10
    MAX_PHOENIX    = 40
    MIN_SIGNALS    = 30

    import pytz
    def parse_dates():
        dates = {}
        for k in ["TRAIN_FROM", "TRAIN_TO", "VAL_TO", "TRAIN_START", "TRAIN_END", "VAL_END"]:
            if k in cfg: dates[k] = cfg[k]
        if "TRAINING" in cfg:
            for k in ["TRAIN_FROM", "TRAIN_TO", "VAL_TO", "TRAIN_START", "TRAIN_END", "VAL_END"]:
                if k in cfg["TRAINING"]: dates[k] = cfg["TRAINING"][k]
        return dates.get("TRAIN_START") or dates.get("TRAIN_FROM"), dates.get("TRAIN_END") or dates.get("TRAIN_TO"), dates.get("VAL_END") or dates.get("VAL_TO")

    t_start, t_end, v_end = parse_dates()
    if t_start and t_end and v_end:
        train_start = pd.Timestamp(t_start, tz='UTC')
        train_end   = pd.Timestamp(t_end,   tz='UTC')
        val_start   = train_end
        val_end     = pd.Timestamp(v_end,   tz='UTC') + pd.Timedelta(days=1)
        print("[DATE RANGE FROM CONFIG]")
    else:
        now_utc     = pd.Timestamp.now(tz='UTC')
        val_end     = now_utc
        val_start   = val_end   - pd.Timedelta(days=4)
        train_end   = val_start
        train_start = train_end - pd.Timedelta(days=90)
        print("[ROLLING WINDOW SPLIT]")

    features_utc = features.tz_convert('UTC')
    targets_utc = targets.tz_convert('UTC')

    train_mask = (features_utc.index >= train_start) & (features_utc.index < train_end)
    val_mask   = (features_utc.index >= val_start)   & (features_utc.index < val_end)

    tr_feat  = features_utc[train_mask]
    tr_targ  = targets_utc[train_mask]
    val_feat = features_utc[val_mask]
    val_targ = targets_utc[val_mask]

    print(f"-> Train: {len(tr_feat):,} nến | Val: {len(val_feat):,} nến")

    train_dataset = TimeSeriesDatasetV1_5(tr_feat, tr_targ, window_size)
    val_dataset   = TimeSeriesDatasetV1_5(val_feat, val_targ, window_size)
    train_loader  = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader    = DataLoader(val_dataset,   batch_size=batch_size, shuffle=False)

    # ── Curriculum Masking Setup ──────────────────────────────
    curriculum_cfg    = cfg.get("CURRICULUM_MASKING", {})
    cm_enabled        = curriculum_cfg.get("ENABLE", False)
    cm_active_window  = curriculum_cfg.get("ACTIVE_WINDOW_SIZE", window_size)
    cm_masked_names   = curriculum_cfg.get("MASKED_FEATURES", [])
    feature_col_names = list(features.columns)
    cm_masked_indices = resolve_masked_indices(feature_col_names, cm_masked_names) if cm_enabled else []

    # ── Diagnostic Log (in ra trước khi bắt đầu epoch) ───────
    print("")
    print("══════════════════════════════════════════════════════")
    if cm_enabled:
        print(f"[CURRICULUM MODE] Symbol: {target_prefix}")
        print(f"[CURRICULUM MODE] Trạng thái: BẬT")
        print(f"[CURRICULUM MODE] Window thực tế: Chỉ học {cm_active_window} nến cuối / Tổng {window_size} nến")
        masked_display = cm_masked_names if cm_masked_names else ["(không có feature nào bị che)"]
        print(f"[CURRICULUM MODE] Features bị che (Masked): {masked_display}")
        print(f"[CURRICULUM MODE] Số features bị mask: {len(cm_masked_indices)} / {num_features}")
    else:
        print(f"[CURRICULUM MODE] Symbol: {target_prefix} | Trạng thái: TẮT — Dữ liệu đầy đủ")
    print("══════════════════════════════════════════════════════")
    print("")
    # ─────────────────────────────────────────────────────────

    train_labels = tr_targ['target'].values
    n_total = len(train_labels)
    n_buy  = (train_labels == 1).sum()
    n_sell = (train_labels == 0).sum()
    weight_sell = n_total / (2.0 * n_sell) if n_sell > 0 else 1.0
    weight_buy  = n_total / (2.0 * n_buy)  if n_buy  > 0 else 1.0
    class_weights = torch.tensor([weight_sell, weight_buy], dtype=torch.float32).to(device)
    print(f"⚖️ [Class Balance] BUY={n_buy:,} (W:{weight_buy:.2f}) | SELL={n_sell:,} (W:{weight_sell:.2f})")

    SESSIONS = {2: "ny"}
    criterion_kwargs = {"weight": class_weights, "label_smoothing": 0.15}
    criterions = {s_id: FocalLoss(**criterion_kwargs, gamma=2.0).to(device) for s_id in SESSIONS}    # Khởi tạo Hệ thống Đa não bộ
    argo_data_dir = cfg.get("ARGO_DATA_DIR", os.environ.get("ARGO_DATA_DIR", "C:/argo/data"))
    meta_path = os.path.join(argo_data_dir, f"feature_meta_{target_prefix}.json")
    num_xau_features = None
    target_name = target_prefix.lower().replace("_", "")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
            num_xau_features = meta.get("num_xau_features") or meta.get("num_target_features")
            target_name = meta.get("target_prefix", target_prefix).lower().replace("_", "")

    models = {s_id: TransformerModel(
        num_features, d_model=d_model, nhead=nhead,
        num_layers=num_attn_layers, dropout_rate=dropout_rate,
        num_xau_features=num_xau_features,
    ).to(device) for s_id in SESSIONS}

    phoenixes = {s_id: PhoenixRestartV1_5(
        models[s_id], base_lr=BASE_LR, max_phoenix=MAX_PHOENIX, max_stagnate=MAX_STAGNATE
    ) for s_id in SESSIONS}

    CONFIG_NAMES = ["L3_1.4_L4_1.0", "L3_1.1_L4_1.0", "BEST_VLOSS"]
    top_configs = {s_id: {k: None for k in CONFIG_NAMES} for s_id in SESSIONS}

    global_best_score = {s_id: 0.0 for s_id in SESSIONS}
    global_best_vloss = {s_id: float('inf') for s_id in SESSIONS}

    def calc_strats(wrs_arr, avg_v_loss):
        return {
            "L3_1.4_L4_1.0": (1.4 * wrs_arr[2] + 1.0 * wrs_arr[3]) / 2.4,
            "L3_1.1_L4_1.0": (1.1 * wrs_arr[2] + 1.0 * wrs_arr[3]) / 2.1,
            "BEST_VLOSS": -avg_v_loss
        }

    # ── In diagnostic batch đầu tiên sau khi setup xong ─────
    _first_batch_logged = False
    _last_hf_push_time = 0

    # ── Xây dựng AI History Buffer ───────────────────────────
    min_signals_dict = {s_id: MIN_SIGNALS for s_id in SESSIONS}
    cm_active_window_dict = {s_id: cm_active_window for s_id in SESSIONS}
    history_buffer = {s_id: {
        "avg_train_loss_history": [],
        "avg_val_loss_history": [],
        "win_rate_L4_history": [],
        "total_signals_L4_history": [],
        "phoenix_count": 0,
        "current_lr": BASE_LR,
        "current_weight_decay": 1e-3,
        "current_min_signals": MIN_SIGNALS,
        "current_cm_window": cm_active_window,
        "current_patience": MAX_STAGNATE,
        "current_label_smoothing": 0.15
    } for s_id in SESSIONS}

    total_epoch = 0
    import time
    while any(not phx.exhausted for phx in phoenixes.values()) and total_epoch < epochs:
        epoch_start_time = time.time()
        # TRAIN
        for m in models.values(): m.train()
        train_loss = {s_id: 0.0 for s_id in SESSIONS}
        valid_train_batches = {s_id: 0 for s_id in SESSIONS}
        
        for batch_x, batch_y, batch_s in train_loader:
            batch_y = batch_y.view(-1).long()
            batch_s = batch_s.view(-1)

            # (Curriculum Masking được apply riêng theo từng session bên dưới)

            # Diagnostic: in shape + vài giá trị batch đầu tiên
            if not _first_batch_logged:
                _first_batch_logged = True
                print(f"[CURRICULUM DIAG] Batch shape: {list(batch_x.shape)}")
                if cm_enabled:
                    print(f"[CURRICULUM DIAG] Vùng masked (nến 0..{window_size - cm_active_window - 1}), sample[0,0,:4]: {batch_x[0, 0, :4].tolist()}")
                    print(f"[CURRICULUM DIAG] Vùng active (nến -{cm_active_window}), sample[0,-1,:4]: {batch_x[0, -1, :4].tolist()}")
            
            for s_id in SESSIONS:
                if phoenixes[s_id].exhausted: continue
                mask = (batch_s == s_id)
                if not mask.any(): continue
                    
                sess_batch_x = batch_x[mask]
                if cm_enabled:
                    sess_batch_x = apply_curriculum_mask(sess_batch_x, cm_active_window_dict[s_id], cm_masked_indices)
                    
                phoenixes[s_id].optimizer.zero_grad()
                outputs = models[s_id](sess_batch_x)
                loss = criterions[s_id](outputs, batch_y[mask])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(models[s_id].parameters(), max_norm=1.0)
                phoenixes[s_id].optimizer.step()
                
                train_loss[s_id] += loss.item()
                valid_train_batches[s_id] += 1

        avg_train_loss = {s_id: train_loss[s_id] / max(valid_train_batches[s_id], 1) for s_id in SESSIONS}

        # VAL
        for m in models.values(): m.eval()
        val_loss_total = {s_id: 0.0 for s_id in SESSIONS}
        all_probs_up = {s_id: [] for s_id in SESSIONS}
        all_labels = {s_id: [] for s_id in SESSIONS}
        valid_val_batches = {s_id: 0 for s_id in SESSIONS}

        with torch.no_grad():
            for batch_x, batch_y, batch_s in val_loader:
                batch_y = batch_y.view(-1).long()
                batch_s = batch_s.view(-1)
                for s_id in SESSIONS:
                    if phoenixes[s_id].exhausted: continue
                    mask = (batch_s == s_id)
                    if not mask.any(): continue
                    
                    outputs = models[s_id](batch_x[mask])
                    loss_v = criterions[s_id](outputs, batch_y[mask])
                    val_loss_total[s_id] += loss_v.item()
                    valid_val_batches[s_id] += 1
                    
                    probs = F.softmax(outputs, dim=1)
                    all_probs_up[s_id].append(probs[:, 1].cpu())
                    all_labels[s_id].append(batch_y[mask].cpu())

        avg_val_loss = {s_id: val_loss_total[s_id] / max(valid_val_batches[s_id], 1) for s_id in SESSIONS}

        epoch_has_improvement = False
        
        for s_id in SESSIONS:
            s_name = SESSIONS[s_id]
            if phoenixes[s_id].exhausted or len(all_probs_up[s_id]) == 0: 
                continue

            probs_t = torch.cat(all_probs_up[s_id])
            labels_t = torch.cat(all_labels[s_id])
            
            # Tính max_thresh V1 logic
            max_thresh = 0.50
            for t_int in range(99, 51, -1):
                t = t_int / 100.0
                n_buy_sig  = (probs_t > t).sum().item()
                n_sell_sig = (probs_t < (1.0 - t)).sum().item()
                if (n_buy_sig + n_sell_sig) >= min_signals_dict[s_id]:
                    max_thresh = t
                    break

            step = (max_thresh - 0.50) / 3 if max_thresh > 0.50 else 0
            thresholds = [round(0.50 + step * i, 4) for i in range(4)]

            wrs, totals_t = [], []
            for t in thresholds:
                lo = 1.0 - t
                b = probs_t > t
                s = probs_t < lo
                n = b.sum().item() + s.sum().item()
                c = (labels_t[b] == 1).sum().item() + (labels_t[s] == 0).sum().item()
                wrs.append(c / n if n > 0 else 0.0)
                totals_t.append(n)

            # L4 Statistically Valid
            is_valid = totals_t[3] >= min_signals_dict[s_id]
            current_scores = calc_strats(wrs, avg_val_loss[s_id])
            
            improved_strategies = []
            if is_valid:
                for cfg_name, s_val in current_scores.items():
                    if top_configs[s_id][cfg_name] is None or s_val > top_configs[s_id][cfg_name]["score"]:
                        top_configs[s_id][cfg_name] = {
                            "score": s_val,
                            "epoch": total_epoch,
                            "state_dict": copy.deepcopy(models[s_id].state_dict()),
                            "thresholds": thresholds[:],
                            "wrs": wrs[:],
                            "totals": totals_t[:],
                            "max_thresh": max_thresh
                        }
                        
                        _f = os.path.join(run_dir, f"{target_name}_{s_name}_weights_{cfg_name}.pth")
                        torch.save(models[s_id].state_dict(), _f)
                        improved_strategies.append(cfg_name)

            if avg_val_loss[s_id] < global_best_vloss[s_id]:
                global_best_vloss[s_id] = avg_val_loss[s_id]

            action_str = ""
            if improved_strategies:
                phoenixes[s_id].reset_stagnation()
                epoch_has_improvement = True
                
                valid_cfgs = [c for c in top_configs[s_id].values() if c is not None]
                if valid_cfgs:
                    best_cfg = max(valid_cfgs, key=lambda x: x["score"])
                    global_best_score[s_id] = best_cfg["score"]

                thr_str = " | ".join(f">{t*100:.0f}%: {wrs[i]*100:.1f} ({totals_t[i]}L)" for i, t in enumerate(thresholds[-2:]))
                print(f"[{s_name.upper()}] ⭐ ĐỈNH MỚI: {','.join(improved_strategies)} | Th>={max_thresh:.2f} | {thr_str} | VLoss: {avg_val_loss[s_id]:.4f}")
                try:
                    import subprocess, time, sys
                    if time.time() - _last_hf_push_time > 60:
                        _last_hf_push_time = time.time()
                        subprocess.Popen([sys.executable, "src/orchestration/hf_sync.py", "push_runs"])
                except Exception as e:
                    print(f"  [HF] Bỏ qua sync: {e}")
            else:
                should_restart = phoenixes[s_id].notify_no_improve()
                if should_restart:
                    valid = [c for c in top_configs[s_id].values() if c is not None]
                    chosen = random.choice(valid)["state_dict"] if valid else models[s_id].state_dict()
                    print(f"\n[PHOENIX #{phoenixes[s_id].phoenix_count}] Mạng {s_id} kẹt {phoenixes[s_id].max_stagnate} epoch. Tái sinh!")
                    action_str = phoenixes[s_id].apply_perturbation(
                        chosen, 
                        s_name=s_name, 
                        history_buffer=history_buffer
                    )

            if True:
                cur_lr = phoenixes[s_id].get_lr()
                acc_total = sum([c for w, c in zip(wrs, totals_t)]) / sum(totals_t) if sum(totals_t) > 0 else 0
                print(f"  [Phiên {s_name.upper()}] Ep {total_epoch} | TLoss: {avg_train_loss[s_id]:.4f} | VLoss: {avg_val_loss[s_id]:.4f} | LR: {cur_lr:.1e}")
                if action_str: print(f"  ↪ {action_str}")
                
            phoenixes[s_id].scheduler.step(wrs[3] if totals_t[3] > 0 else avg_val_loss[s_id])
            
            # Ghi Metrics vào Buffer cho AI Supervisor
            history_buffer[s_id]["avg_train_loss_history"].append(float(avg_train_loss[s_id]))
            history_buffer[s_id]["avg_val_loss_history"].append(float(avg_val_loss[s_id]))
            history_buffer[s_id]["win_rate_L4_history"].append(float(wrs[3]) if len(wrs) > 3 else 0.0)
            history_buffer[s_id]["total_signals_L4_history"].append(int(totals_t[3]) if len(totals_t) > 3 else 0)
            history_buffer[s_id]["phoenix_count"] = phoenixes[s_id].phoenix_count
            history_buffer[s_id]["current_lr"] = float(phoenixes[s_id].get_lr())
            history_buffer[s_id]["current_weight_decay"] = float(phoenixes[s_id].optimizer.param_groups[0].get('weight_decay', 0.0))
            history_buffer[s_id]["current_min_signals"] = min_signals_dict[s_id]
            history_buffer[s_id]["current_cm_window"] = cm_active_window_dict[s_id]
            history_buffer[s_id]["current_patience"] = phoenixes[s_id].scheduler.patience
            history_buffer[s_id]["current_label_smoothing"] = criterions[s_id].label_smoothing if hasattr(criterions[s_id], 'label_smoothing') else 0.15

        total_epoch += 1
        
        # ── LLM META-OPTIMIZER TRIGGER (Mỗi 50 Epochs) ──────────
        AI_INTERVAL = 50
        if total_epoch > 0 and total_epoch % AI_INTERVAL == 0:
            print(f"\n🤖 [AI SUPERVISOR] Đang phân tích metrics sau {total_epoch} epochs...")
            try:
                from src.training_v1_5.ai_supervisor import call_llm_meta_optimizer
                resp_json = call_llm_meta_optimizer(history_buffer, total_epoch, base_dir=str(_ROOT))
                if resp_json:
                    print(f"🤖 [AI_REPORT]: {resp_json.get('analysis_report', '')}")
                    # In ra Sự Kiện và Bắn thẳng vào Telegram Group/User
                    tel_msg = resp_json.get('telegram_message', '')
                    if tel_msg: 
                        print(f"🔥 BÁO CÁO AI: {tel_msg}")
                        try:
                            import requests
                            tg_cfg_path = os.path.join(str(_ROOT), "tg_config.json")
                            if os.path.exists(tg_cfg_path):
                                with open(tg_cfg_path, "r", encoding='utf-8') as f:
                                    tg_cfg = json.load(f)
                                bot_token = tg_cfg.get("bot_token")
                                chat_ids = tg_cfg.get("allowed_user_ids", [])
                                if bot_token and chat_ids:
                                    # Format message beautifully
                                    tele_content = f"🤖 <b>[AI SUPERVISOR - {target_prefix}]</b>\n\n{tel_msg}"
                                    for chat_id in chat_ids:
                                        requests.post(
                                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                            data={"chat_id": chat_id, "text": tele_content, "parse_mode": "HTML"},
                                            timeout=5
                                        )
                        except Exception as e:
                            print(f"[TELEGRAM ERROR] {e}")
                    
                    actions = resp_json.get("actions", {})
                    for dict_key, act in actions.items():
                        if str(dict_key).isdigit(): s_id = int(dict_key)
                        elif dict_key == 'asia': s_id = 0
                        elif dict_key == 'london': s_id = 1
                        else: s_id = 2
                        
                        if s_id not in phoenixes: continue
                        
                        eval_msg = act.get("session_evaluation", "")
                        if eval_msg:
                            print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] AI Nghi: {eval_msg}")
                        
                        action_type = act.get("action_type", "continue")
                        if action_type == "force_phoenix":
                            print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] 💀 AI 강제 PHOENIX!")
                            if top_configs[s_id][CONFIG_ID] is not None:
                                action_info = phoenixes[s_id].apply_perturbation(
                                    top_configs[s_id][CONFIG_ID]["state_dict"], 
                                    s_name=SESSIONS[s_id], 
                                    history_buffer=history_buffer
                                )
                                print(f"    ↪ {action_info}")
                            else:
                                print("    ↪ Chưa có đỉnh nào, bỏ qua lệnh AI ép.")
                                phoenixes[s_id].reset_stagnation()
                            continue
                            
                        if action_type == "stop":
                            phoenixes[s_id].exhausted = True
                            print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] AI Quyết định: STOP")
                            continue
                            
                        if "new_lr" in act or "weight_decay" in act:
                            new_lr = act.get("new_lr")
                            new_wd = act.get("weight_decay")
                            for param_group in phoenixes[s_id].optimizer.param_groups:
                                if new_lr is not None and 1e-6 <= float(new_lr) <= 1e-2:
                                    param_group['lr'] = float(new_lr)
                                if new_wd is not None and 0 <= float(new_wd) <= 0.1:
                                    param_group['weight_decay'] = float(new_wd)
                            print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] Cập nhật (LR={new_lr}, WD={new_wd})")
                            
                        if "min_signals" in act:
                            val = int(act["min_signals"])
                            if 10 <= val <= 50:
                                min_signals_dict[s_id] = val
                                print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] Đổi MIN_SIGNALS = {val}")
                                
                        if "active_window_size" in act:
                            val = int(act["active_window_size"])
                            if 10 <= val <= window_size:
                                cm_active_window_dict[s_id] = val
                                print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] Mở rộng CM_WINDOW = {val}")

                        if "label_smoothing" in act:
                            val = float(act["label_smoothing"])
                            if 0.0 <= val <= 0.5:
                                criterions[s_id] = FocalLoss(weight=class_weights, label_smoothing=val, gamma=2.0).to(device)
                                print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] Đổi LABEL_SMOOTHING = {val}")

                        if "patience" in act:
                            val = int(act["patience"])
                            if 3 <= val <= 30:
                                phoenixes[s_id].scheduler.patience = val
                                print(f"  ↪ [Phiên {SESSIONS[s_id].upper()}] Đổi PATIENCE = {val}")
                                
                        if action_type == "force_phoenix":
                            valid = [c for c in top_configs[s_id].values() if c is not None]
                            chosen = random.choice(valid)["state_dict"] if valid else models[s_id].state_dict()
                            print(f"\n[PHOENIX #{phoenixes[s_id].phoenix_count}] AI Bắt Buộc Tái Sinh!")
                            a_str = phoenixes[s_id].apply_perturbation(chosen)
                            print(f"  ↪ {a_str}")
                
            except Exception as e:
                print(f"[AI SUPERVISOR ERR] {e}")
                
            # Xóa buffer đón chu kỳ mới
            for s_id in SESSIONS:
                history_buffer[s_id]["avg_train_loss_history"].clear()
                history_buffer[s_id]["avg_val_loss_history"].clear()
                history_buffer[s_id]["win_rate_L4_history"].clear()
                history_buffer[s_id]["total_signals_L4_history"].clear()
        # ────────────────────────────────────────────────────────
        
        # Ghi log json (Blackbox)
        _save_blackbox_multi(run_dir, target_name, top_configs, num_xau_features, num_features, total_epoch)

    print(f"\n✅ KẾT THÚC V1.5 Train. Dữ liệu chạy đã lưu vào {run_dir}")

def _save_blackbox_multi(run_dir, target_name, top_configs, num_target_features, num_features, epoch):
    meta_file = os.path.join(run_dir, "training_metrix_v1_5.json")
    out = {
        "target": target_name,
        "version": "Independent_Multi_Session_v1.5",
        "epochs_trained": epoch,
        "dimensions": {
            "num_features_target": num_target_features or 0,
            "num_features_macro": (num_features - num_target_features) if num_target_features is not None else num_features,
        },
        "sessions": {}
    }
    
    for s_id in top_configs.keys():
        s_name = {0: "asia", 1: "london", 2: "ny"}.get(s_id, "unknown")
        sess_data = {}
        for k, v in top_configs[s_id].items():
            if v is not None:
                sess_data[k] = {
                    "epoch": v["epoch"],
                    "composite_score": v["score"],
                    "max_thresh": v["max_thresh"],
                    "thresholds": v["thresholds"],
                    "win_rates": [wr * 100 for wr in v["wrs"]],
                    "totals": v["totals"]
                }
        out["sessions"][s_name] = sess_data

    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=4, ensure_ascii=False)


def validate_startup_configs(cfg_dict, root_dir):
    """Kiểm tra khắt khe cấu hình tại thời điểm khởi động để chống báo lỗi giữa chừng"""
    errors = []
    tg_cfg_path = os.path.join(root_dir, "tg_config.json")
    if os.path.exists(tg_cfg_path):
        with open(tg_cfg_path, "r", encoding="utf-8") as f:
            tg = json.load(f)
            # Thống nhất tập trung toàn bộ khoá API ở tg_config.json
            gemini = tg.get("gemini_api_key", cfg_dict.get("gemini_api_key", ""))
            hf = tg.get("hf_token", cfg_dict.get("hf_token", ""))
            
            # Bỏ qua check bắt buộc gemini_api_key để xài hardcode trong ai_supervisor
            # if not gemini or not gemini.startswith("AIza"):
            #     errors.append("- gemini_api_key (Chưa khai báo hoặc sai định dạng AIza...) trong tg_config.json")
                
            if not hf or not hf.startswith("hf_"):
                errors.append("- hf_token (Chưa khai báo hoặc sai định dạng hf_...) trong tg_config.json")
                
            if not tg.get("bot_token"): 
                errors.append("- bot_token (Thiếu token Telegram trong tg_config.json)")
            if not tg.get("allowed_chat_ids"): 
                errors.append("- allowed_chat_ids (Thiếu danh sách Chat ID nhận tin nhắn Telegram)")
    else:
        errors.append("- Không tìm thấy tệp tg_config.json tại thư mục gốc.")
        
    if errors:
        print("\n" + "🔥"*25)
        print("🚨 [CRITICAL LỖI KHỞI ĐỘNG] THIẾU CẤU HÌNH BẮT BUỘC 🚨")
        print("Xin hãy sửa các lỗi sau để bot có thể tải Data và gửi nhắn tin Telegram:")
        for e in errors:
            print(f"  {e}")
        print("🔥"*25 + "\n")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", help="Đường dẫn bot_config_*.json")
    args = parser.parse_args()

    config_path = args.config
    if not config_path:
        default_data_dir = os.environ.get("ARGO_DATA_DIR", "C:/argo/data")
        for candidate in [f"{default_data_dir}/bot_config_xau.json", f"{default_data_dir}/bot_config.json"]:
            p = candidate
            if os.path.exists(p):
                config_path = p
                break

    cfg = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    ARGO_DATA_DIR = cfg.get("ARGO_DATA_DIR", os.environ.get("ARGO_DATA_DIR", "C:/argo/data"))
    ARGO_LOGS_DIR = cfg.get("ARGO_LOGS_DIR", os.environ.get("ARGO_LOGS_DIR", "C:/argo/logs"))

    TARGET_PREFIX = cfg.get("TARGET_PREFIX", "XAUUSD")
    CONFIG_ID     = cfg.get("CONFIG_ID", "DEFAULT")
    DATA_PATH     = ARGO_DATA_DIR
    
    validate_startup_configs(cfg, _ROOT)
    
    # Kích hoạt tự động đồng bộ (pull) đúng dữ liệu parquet quy định trong config
    try:
        sys.path.insert(0, os.path.join(_ROOT, "src", "orchestration"))
        from hf_sync import pull_data
        print("☁️ [TRAIN] Kích hoạt đồng bộ HF theo cấu hình (REQUIRED_PARQUETS)...")
        pull_data(config_path=config_path)
    except Exception as e:
        print(f"⚠️ [TRAIN] Bỏ qua kích hoạt đồng bộ HF (Không quan trọng): {e}")

    features_path = os.path.join(DATA_PATH, f"final_features_{CONFIG_ID}.parquet")
    target_path   = os.path.join(DATA_PATH, f"target_direction_{CONFIG_ID}.parquet")

    if not os.path.exists(features_path) or not os.path.exists(target_path):
        print(f"❌ Không tìm thấy dữ liệu {features_path} hoặc target {target_path}")
        sys.exit(1)

    features = pd.read_parquet(features_path)
    targets  = pd.read_parquet(target_path)
    
    run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_clean = TARGET_PREFIX.lower().replace("_", "")
    run_name = f"run_{run_timestamp}_{target_clean}_{CONFIG_ID}_TRANSFORMER_V1_5"
    run_dir  = os.path.join(ARGO_LOGS_DIR, "runs", run_name)
    os.makedirs(run_dir, exist_ok=True)
    
    class _TeeLogger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "a", encoding="utf-8", buffering=1)
        def write(self, msg):
            self.terminal.write(msg)
            self.log.write(msg)
            self.flush()
        def flush(self):
            self.terminal.flush()
            self.log.flush()

    sys.stdout = _TeeLogger(os.path.join(run_dir, "train_v1_5.log"))
    
    print(f"📁 Run dir: {run_name}")
    print(f"[VERSION_INFO] Tích hợp tính năng: {RUN_VERSION_DESC}")
    
    # Copy scaler
    import shutil
    scaler_src = os.path.join(DATA_PATH, "scaler.pkl")
    if os.path.exists(scaler_src):
        shutil.copy(scaler_src, os.path.join(run_dir, "scaler.pkl"))

    train_unified_v1_5(features, targets, features.shape[1], run_dir, config=cfg, target_prefix=TARGET_PREFIX)
