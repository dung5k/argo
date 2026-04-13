"""
train_v2.py — Training Entry Point V2
=======================================
Tích hợp 5 cải tiến toán học so với train_unified.py (V1):

    1. Soft Labels        : y = sigmoid(k · log_return_T+5)
    2. QuantileTransformer: kháng Fat-tails, giới hạn outlier
    3. FocalLoss V2       : tập trung gradient vào mẫu khó
    4. Phoenix V2         : Magnitude-aware Noise (Δw ~ N(0,(α·|w|)²))
    5. EV Evaluation      : Expected Value thay Win Rate thuần túy

Tương thích hoàn toàn với bot_config_xau.json.
Output lưu vào runs/ với suffix _V2 để phân biệt với V1.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import copy
import json
import time
import random
import datetime
import threading
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# ── Thêm thư mục gốc vào sys.path để import legacy model ──────────────────
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.models.transformer import TransformerModel
import torch

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

from src.training_v2.label_generator import SoftLabelGenerator
from src.training_v2.feature_pipeline_v2 import FeaturePipelineV2
from src.training_v2.focal_loss import build_focal_loss
from src.training_v2.phoenix_v2 import PhoenixRestartV2
from src.training_v2.evaluator_v2 import EVEvaluator, EpochEvalResult


# ============================================================
# Dataset V2: hỗ trợ soft labels + log_returns cho EV
# ============================================================
class TimeSeriesDatasetV2(Dataset):
    """
    Dataset kế thừa TimeSeriesDataset nhưng trả về thêm log_return thực tế.

    Parameters
    ----------
    features : pd.DataFrame
        Features đã scaled.
    soft_labels : pd.Series (float)
        Soft labels ∈ (0,1).
    log_returns : pd.Series (float)
        Log return T+5 thực tế (dùng cho EV evaluation).
    window_size : int
        Số nến trong mỗi cửa sổ trượt.
    """

    def __init__(
        self,
        features: pd.DataFrame,
        soft_labels: pd.Series,
        log_returns: pd.Series,
        window_size: int = 60,
    ):
        self.window_size = window_size

        # Lọc cửa sổ có quá nhiều Nến Ma (> 15%)
        self.valid_indices = []
        if 'is_imputed_flag' in features.columns:
            flags = features['is_imputed_flag'].values
            for i in range(len(features) - window_size):
                if flags[i: i + window_size].sum() <= 0.15 * window_size:
                    self.valid_indices.append(i)
        else:
            self.valid_indices = list(range(len(features) - window_size))

        n_dropped = (len(features) - window_size) - len(self.valid_indices)
        print(
            f"[DatasetV2] Tổng {len(features)-window_size:,} cửa sổ. "
            f"Loại {n_dropped:,} cửa sổ Nến Ma > 15%."
        )

        # Tính toán danh mục phiên (Session Routing ID)
        # Giả định features.index là mốc thời gian UTC (DatetimeIndex)
        hours = features.index.hour.values
        session_arr = np.zeros_like(hours, dtype=np.int64) # Mặc định 0: Phiên Á (0-7h)
        session_arr[(hours >= 8) & (hours < 13)] = 1       # 1: Phiên Âu (8-12h)
        session_arr[(hours >= 13)] = 2                     # 2: Phiên Mỹ (13-23h)

        # Đẩy lên GPU nếu có
        self.features_tensor = torch.tensor(
            features.values, dtype=torch.float32
        ).to(device)
        self.labels_tensor = torch.tensor(
            soft_labels.values, dtype=torch.float32
        ).to(device)
        self.returns_tensor = torch.tensor(
            log_returns.values, dtype=torch.float32
        ).to(device)
        self.session_tensor = torch.tensor(
            session_arr, dtype=torch.long
        ).to(device)

    def __len__(self) -> int:
        return len(self.valid_indices)

    def __getitem__(self, raw_idx: int):
        idx = self.valid_indices[raw_idx]
        x = self.features_tensor[idx: idx + self.window_size]
        target_idx = idx + self.window_size - 1
        y = self.labels_tensor[target_idx]
        r = self.returns_tensor[target_idx]
        s = self.session_tensor[target_idx]
        return x, y, r, s


# ============================================================
# Utility: đọc config từ bot_config_*.json
# ============================================================
def _load_config(config_path: str) -> dict:
    if not config_path or not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_date_range(cfg: dict):
    """Đọc khoảng thời gian train/val từ config."""
    date_keys = {}
    for k in ["TRAIN_FROM", "TRAIN_TO", "VAL_TO", "TRAIN_START", "TRAIN_END", "VAL_END"]:
        if k in cfg:
            date_keys[k] = cfg[k]
    if "TRAINING" in cfg:
        for k in ["TRAIN_FROM", "TRAIN_TO", "VAL_TO", "TRAIN_START", "TRAIN_END", "VAL_END"]:
            if k in cfg["TRAINING"]:
                date_keys[k] = cfg["TRAINING"][k]

    t_start = date_keys.get("TRAIN_START") or date_keys.get("TRAIN_FROM")
    t_end   = date_keys.get("TRAIN_END")   or date_keys.get("TRAIN_TO")
    v_end   = date_keys.get("VAL_END")     or date_keys.get("VAL_TO")
    return t_start, t_end, v_end


# ============================================================
# HuggingFace sync (non-blocking)
# ============================================================
def _hf_sync_async(run_dir: str):
    def _worker():
        try:
            src_path = os.path.join(_ROOT, "src")
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            from orchestration.hf_sync import push_runs
            if push_runs():
                pass
                # print("    [HF] Đã đồng bộ trọng số V2 lên HuggingFace.")
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()


# ============================================================
# Hàm lưu blackbox metrics
# ============================================================
def _save_blackbox(
    run_dir: str,
    target_name: str,
    top_configs: dict,
    current_epoch: int,
    best_ev: float,
    best_val_loss: float,
    is_interrupted: bool = False,
):
    top_meta = []
    for s_name, cfg in top_configs.items():
        if cfg is not None:
            m_list = cfg.get("eval_result")
            ev_composite = m_list.composite_score() if m_list else 0.0
            top_meta.append({
                "strategy": s_name,
                "score": ev_composite * 10000,
                "max_thresh": cfg.get("max_thresh", 0.5),
                "thresholds": [m.threshold for m in (m_list.threshold_metrics if m_list else [])],
                "win_rates": [m.win_rate * 100 for m in (m_list.threshold_metrics if m_list else [])],
                "totals": [m.total_signals for m in (m_list.threshold_metrics if m_list else [])]
            })

    data = {
        "target": target_name,
        "version": "V2",
        "status": "STOPPED" if is_interrupted else "RUNNING_OR_DONE",
        "epochs_trained": current_epoch,
        "best_ev_composite_pip": best_ev * 10000,
        "best_val_loss": best_val_loss,
        "top_configs_saved": top_meta,
    }
    path = os.path.join(run_dir, "training_metrix_v2.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

    _hf_sync_async(run_dir)


# ============================================================
# MAIN TRAINING FUNCTION
# ============================================================
def train_v2(
    features: pd.DataFrame,
    soft_labels: pd.Series,
    log_returns: pd.Series,
    num_features: int,
    run_dir: str,
    target_prefix: str = "XAUUSD",
    config = None,
    max_epoch_override = None,
    config_path = None,
):
    """
    Huấn luyện Transformer V2 với 5 cải tiến toán học.

    Parameters
    ----------
    features : pd.DataFrame
        Features đã qua QuantileTransform (scaler_v2.pkl).
    soft_labels : pd.Series
        Soft labels float ∈ (0,1) từ SoftLabelGenerator.
    log_returns : pd.Series
        Log return T+5 thực tế, aligned với soft_labels.index.
    num_features : int
        Số lượng features (chiều input model).
    run_dir : str
        Thư mục lưu trọng số và metadata.
    target_prefix : str
        Tiền tố mã giao dịch.
    config : dict
        Config từ bot_config_*.json.
    max_epoch_override : int | None
        Nếu không None, dừng sau số epoch này (dùng để smoke test).
    """
    cfg = config or {}
    print("=" * 60)
    print("  TRANSFORMER V2 — 5 cải tiến toán học (EV + FocalLoss)")
    print("=" * 60)

    try:
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        print(f"[HARDWARE] {gpu_name}")
    except Exception:
        pass

    # ── Chế độ Hiệu suất (Performance Mode) ────────────────────
    perf_mode = os.environ.get("PERFORMANCE_MODE", cfg.get("TRAINING", {}).get("PERFORMANCE_MODE", "MAX")).upper()
    if perf_mode == "LIGHT":
        import multiprocessing
        cores = multiprocessing.cpu_count()
        threads = max(1, cores // 2)
        torch.set_num_threads(threads)
        print(f"[{perf_mode} MODE] 🌿 Chế độ nhẹ nhàng: Giới hạn PyTorch dùng {threads}/{cores} CPU luồng để chạy ẩn.")
    else:
        print(f"[{perf_mode} MODE] 🚀 Chế độ Tối đa: Mở khóa hiệu suất chiếm dụng toàn bộ thiết bị.")

    # ── Hyperparameters ────────────────────────────────────────
    WINDOW_SIZE      = 60
    D_MODEL          = 256
    NHEAD            = 8
    NUM_ATTN_LAYERS  = 3
    DROPOUT_RATE     = 0.2
    BASE_LR          = 1e-4
    
    # [GPU MAXIMIZATION] Auto-scale Batch Size theo cấu hình hoặc đẩy thẳng lên 4096 để ép cháy cuda cores
    if cfg and cfg.get("TRAINING", {}).get("BATCH_SIZE"):
        BATCH_SIZE = cfg["TRAINING"]["BATCH_SIZE"]
    else:
        BATCH_SIZE = 512 if perf_mode == "LIGHT" else 4096
        
    # [GPU MAXIMIZATION] Bật bộ tối ưu tĩnh CUDNN để Pytorch tự compile hàm tích chập (Convolution) tối ưu nhất theo phần cứng
    if torch.cuda.is_available() and perf_mode != "LIGHT":
        torch.backends.cudnn.benchmark = True
        
    MAX_STAGNATE     = 10
    MAX_PHOENIX      = 40
    MIN_SIGNALS      = 30
    EPOCHS           = max_epoch_override or 10000

    print(
        f"[V2 ARCH] d_model={D_MODEL}, nhead={NHEAD}, "
        f"layers={NUM_ATTN_LAYERS}, window={WINDOW_SIZE}"
    )

    # ── Khoảng thời gian train/val ─────────────────────────────
    t_start, t_end, v_end = _parse_date_range(cfg)
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

    print(f"  Train : {train_start.date()} → {train_end.date()}")
    print(f"  Val   : {val_start.date()} → {val_end.date()}")

    # ── Align features/labels về UTC ──────────────────────────
    feat_utc = features.copy()
    if feat_utc.index.tz is None:
        feat_utc.index = feat_utc.index.tz_localize('UTC')
    else:
        feat_utc.index = feat_utc.index.tz_convert('UTC')

    labels_utc = soft_labels.copy()
    if labels_utc.index.tz is None:
        labels_utc.index = labels_utc.index.tz_localize('UTC')
    else:
        labels_utc.index = labels_utc.index.tz_convert('UTC')

    rets_utc = log_returns.copy()
    if rets_utc.index.tz is None:
        rets_utc.index = rets_utc.index.tz_localize('UTC')
    else:
        rets_utc.index = rets_utc.index.tz_convert('UTC')

    # Đảm bảo 3 series cùng index
    common_idx = feat_utc.index.intersection(labels_utc.index).intersection(rets_utc.index)
    feat_utc    = feat_utc.loc[common_idx]
    labels_utc  = labels_utc.loc[common_idx]
    rets_utc    = rets_utc.loc[common_idx]

    train_mask = (feat_utc.index >= train_start) & (feat_utc.index < train_end)
    val_mask   = (feat_utc.index >= val_start)   & (feat_utc.index < val_end)

    tr_feat  = feat_utc[train_mask];   tr_lbl = labels_utc[train_mask];  tr_ret = rets_utc[train_mask]
    val_feat = feat_utc[val_mask];     val_lbl = labels_utc[val_mask];   val_ret = rets_utc[val_mask]

    print(f"  → Train: {len(tr_feat):,} nến | Val: {len(val_feat):,} nến")

    if len(tr_feat) <= WINDOW_SIZE or len(val_feat) <= WINDOW_SIZE:
        print("[ERROR] Dữ liệu quá ít. Kiểm tra lại phạm vi thời gian.")
        return

    # ── Build datasets ─────────────────────────────────────────
    train_dataset = TimeSeriesDatasetV2(tr_feat, tr_lbl, tr_ret, WINDOW_SIZE)
    val_dataset   = TimeSeriesDatasetV2(val_feat, val_lbl, val_ret, WINDOW_SIZE)
    # === [GPU AUTO-TUNE BATCH SIZE] ===
    print(f"\n[GPU AUTO-TUNE] Bắt đầu dò chuẩn Batch Size tối đa cho VRAM (Mặc định: {BATCH_SIZE})...")
    _test_batch = BATCH_SIZE
    try:
        num_target_features = num_features # approximate for dummy
        dummy_model = TransformerModel(
            num_features, d_model=D_MODEL, nhead=NHEAD,
            num_layers=NUM_ATTN_LAYERS, dropout_rate=DROPOUT_RATE,
            num_xau_features=38, # DUMMY
        ).to(device)
        dummy_optimizer = torch.optim.Adam(dummy_model.parameters(), lr=1e-4)
        while _test_batch >= 128:
            try:
                torch.cuda.empty_cache()
                dummy_loader = DataLoader(train_dataset, batch_size=_test_batch, shuffle=True)
                x, y, r, s = next(iter(dummy_loader))
                dummy_model.train()
                dummy_optimizer.zero_grad()
                out = dummy_model(x)
                loss = F.mse_loss(out.squeeze(), y)
                loss.backward()
                dummy_optimizer.step()
                
                # Thành công:
                del x, y, r, s, out, loss, dummy_loader
                print(f"  -> ✅ Chốt mức Batch Size Tối đa an toàn: {_test_batch}")
                BATCH_SIZE = _test_batch
                break
            except Exception as e:
                err_str = str(e).lower()
                if "out of memory" in err_str or "oom" in err_str or "cuda error" in err_str:
                    torch.cuda.empty_cache()
                    print(f"  -> ⚠️ Batch {_test_batch} quá lớn gây Tràn bộ nhớ (OOM). Đang giảm xuống kích cỡ an toàn...")
                    _test_batch = int(_test_batch * 0.75) if _test_batch >= 2048 else _test_batch // 2
                    _test_batch = (_test_batch // 64) * 64 # align 64
                else:
                    raise e
        del dummy_model, dummy_optimizer
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"[GPU AUTO-TUNE] Bỏ qua auto-tune do lỗi khởi tạo định lượng: {e}")
    # ==================================
    
    train_loader  = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader    = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)

    # ── Class balance cho FocalLoss ────────────────────────────
    hard_train = (tr_lbl >= 0.5).values
    n_buy  = int(hard_train.sum())
    n_sell = int(len(hard_train) - n_buy)
    print(f"[Class Balance] BUY={n_buy:,} | SELL={n_sell:,}")

    criterion = build_focal_loss(
        n_buy=n_buy, n_sell=n_sell,
        gamma=2.0, use_soft_labels=True, device=device
    )

    # ── Build 3 Independent Models ─────────────────────────────
    meta_path = os.path.join(
        _ROOT, "data", f"feature_meta_{target_prefix}.json"
    )
    num_target_features = None
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
            num_target_features = meta.get("num_xau_features") or meta.get("num_target_features")

    target_name = target_prefix.lower().replace("_", "")
    
    # Session ID maps: 0: Asia, 1: London, 2: NY
    SESSIONS = {0: "asia", 1: "london", 2: "ny"}
    
    # 1. Models
    models = {s_id: TransformerModel(
        num_features, d_model=D_MODEL, nhead=NHEAD,
        num_layers=NUM_ATTN_LAYERS, dropout_rate=DROPOUT_RATE,
        num_xau_features=num_target_features,
    ).to(device) for s_id in SESSIONS}

    # 2. Phoenix Restarters
    phoenixes = {s_id: PhoenixRestartV2(
        model=models[s_id],
        base_lr=BASE_LR,
        weight_decay=1e-3,
        max_phoenix=MAX_PHOENIX,
        max_stagnate=MAX_STAGNATE,
        min_signals=MIN_SIGNALS,
    ) for s_id in SESSIONS}

    # 3. Evaluators
    evaluators = {s_id: EVEvaluator(min_signals=MIN_SIGNALS, n_thresholds=4) for s_id in SESSIONS}

    # 4. Top configs tracking per session
    CONFIG_NAMES = ["EV_L3_1.4_L4_1.0", "EV_L3_1.1_L4_1.0", "BEST_VLOSS"]
    top_configs = {s_id: {k: None for k in CONFIG_NAMES} for s_id in SESSIONS}

    global_best_ev   = {s_id: 0.0 for s_id in SESSIONS}
    global_best_vloss = {s_id: float('inf') for s_id in SESSIONS}
    
    # 5. Kế thừa trọng số cũ
    import glob
    print("\n[INHERIT] Đang tìm trọng số cũ để kế thừa...")
    for s_id, s_name in SESSIONS.items():
        pattern = os.path.join(_ROOT, "runs", "**", f"{target_name}_{s_name}_weights_*.pth")
        all_files = glob.glob(pattern, recursive=True)
        if all_files:
            latest_file = max(all_files, key=os.path.getmtime)
            try:
                models[s_id].load_state_dict(torch.load(latest_file, map_location=device, weights_only=True))
                print(f"  ↪ Mạng {s_id} ({s_name.upper()}): {os.path.basename(latest_file)}")
            except Exception as e:
                print(f"  ↪ Lỗi kế thừa Mạng {s_id}: {e}")
        else:
            print(f"  ↪ Mạng {s_id} ({s_name.upper()}): Khởi tạo ngẫu nhiên từ đầu")

    total_epoch = -1  # Epoch -1 dùng để Evaluate cấu hình kế thừa ban đầu

    def _get_score(result: EpochEvalResult, strategy: str) -> float:
        if strategy == "EV_L3_1.4_L4_1.0":
            return result.composite_score(w_l3=1.4, w_l4=1.0, weight_sum=2.4)
        elif strategy == "EV_L3_1.1_L4_1.0":
            return result.composite_score(w_l3=1.1, w_l4=1.0, weight_sum=2.1)
        elif strategy == "BEST_VLOSS":
            return -result.val_loss
        return 0.0

    current_active_mode = perf_mode
    
    # ── Training loop ──────────────────────────────────────────
    try:
        while any(not phx.exhausted for phx in phoenixes.values()) and total_epoch < EPOCHS:
            # ── [HOT-SWAP] Đọc lại config mỗi epoch ──
            if config_path and os.path.exists(config_path):
                try:
                    import multiprocessing
                    with open(config_path, "r", encoding="utf-8") as _fc:
                        _hcfg = json.load(_fc)
                    new_mode = _hcfg.get("TRAINING", {}).get("PERFORMANCE_MODE", current_active_mode).upper()
                    if new_mode in ["MAX", "LIGHT"] and new_mode != current_active_mode:
                        print(f"\n[HOT-SWAP] Chuyển đổi Performance Mode on-the-fly: {current_active_mode} ➜ {new_mode}")
                        current_active_mode = new_mode
                        if new_mode == "LIGHT":
                            torch.set_num_threads(max(1, multiprocessing.cpu_count() // 2))
                        else:
                            torch.set_num_threads(multiprocessing.cpu_count())
                except Exception:
                    pass

            epoch_t0 = time.time()
            epoch_has_improvement = False

            # TRAIN
            for m in models.values(): m.train()
            train_loss = {s_id: 0.0 for s_id in SESSIONS}
            valid_train_batches = {s_id: 0 for s_id in SESSIONS}
            
            if total_epoch >= 0:
                total_batches = 0
                for batch_x, batch_y, _, batch_s in train_loader:
                    batch_y = batch_y.view(-1)
                    batch_s = batch_s.view(-1)
                    
                    for s_id in SESSIONS:
                        if phoenixes[s_id].exhausted: continue
                        mask = (batch_s == s_id)
                        if not mask.any(): continue
                            
                        phoenixes[s_id].optimizer.zero_grad()
                        outputs = models[s_id](batch_x[mask])
                        loss = criterion(outputs, batch_y[mask])
                        loss.backward()
                        torch.nn.utils.clip_grad_norm_(models[s_id].parameters(), max_norm=1.0)
                        phoenixes[s_id].optimizer.step()
                        
                        train_loss[s_id] += loss.item()
                        valid_train_batches[s_id] += 1
                    
                    total_batches += 1
                    if total_batches % 15 == 0:
                        print(f"  [TRAIN] Đang xử lý... ({total_batches} batches)")

            avg_train_loss = {s_id: train_loss[s_id] / max(valid_train_batches[s_id], 1) for s_id in SESSIONS}

            # VAL
            for m in models.values(): m.eval()
            val_loss_total = {s_id: 0.0 for s_id in SESSIONS}
            all_probs_up = {s_id: [] for s_id in SESSIONS}
            all_hard_labels = {s_id: [] for s_id in SESSIONS}
            all_log_returns = {s_id: [] for s_id in SESSIONS}
            valid_val_batches = {s_id: 0 for s_id in SESSIONS}

            with torch.no_grad():
                for batch_x, batch_y, batch_r, batch_s in val_loader:
                    batch_y = batch_y.view(-1)
                    batch_s = batch_s.view(-1)
                    for s_id in SESSIONS:
                        if phoenixes[s_id].exhausted: continue
                        mask = (batch_s == s_id)
                        if not mask.any(): continue
                        
                        outputs = models[s_id](batch_x[mask])
                        loss_v = criterion(outputs, batch_y[mask])
                        val_loss_total[s_id] += loss_v.item()
                        valid_val_batches[s_id] += 1
                        
                        probs = F.softmax(outputs, dim=1)
                        all_probs_up[s_id].append(probs[:, 1].cpu())
                        all_hard_labels[s_id].append((batch_y[mask] >= 0.5).long().cpu())
                        all_log_returns[s_id].append(batch_r[mask].cpu())

            avg_val_loss = {s_id: val_loss_total[s_id] / max(valid_val_batches[s_id], 1) for s_id in SESSIONS}

            for s_id in SESSIONS:
                s_name = SESSIONS[s_id]
                if phoenixes[s_id].exhausted or len(all_probs_up[s_id]) == 0: 
                    continue

                probs_t = torch.cat(all_probs_up[s_id])
                hard_t = torch.cat(all_hard_labels[s_id])
                ret_t = torch.cat(all_log_returns[s_id])
                
                # Evaluate EV separate per session
                result = evaluators[s_id].evaluate(
                    probs_up=probs_t,
                    hard_labels=hard_t,
                    log_returns=ret_t,
                    val_loss=avg_val_loss[s_id],
                )

                # Check L4 valid
                valid = evaluators[s_id].is_statistically_valid(result)

                # Track and save Models
                global_best_ev[s_id] = max(global_best_ev[s_id], result.best_ev)
                global_best_vloss[s_id] = min(global_best_vloss[s_id], avg_val_loss[s_id])

                improved = []
                for cfg_name in CONFIG_NAMES:
                    score = _get_score(result, cfg_name)
                    if top_configs[s_id][cfg_name] is None or score > top_configs[s_id][cfg_name]["score"]:
                        top_configs[s_id][cfg_name] = {
                            "score": score,
                            "epoch": total_epoch,
                            "state_dict": {k: v.cpu() for k, v in models[s_id].state_dict().items()},
                            "eval_result": result,
                        }
                        # LƯU CHÍNH THỨC XUỐNG ĐỊA ĐĨA THEO PHIÊN
                        _f = os.path.join(run_dir, f"{target_name}_{s_name}_weights_{cfg_name}.pth")
                        torch.save(models[s_id].state_dict(), _f)
                        improved.append(cfg_name)
                        
                        l3 = result.threshold_metrics[2] if len(result.threshold_metrics) > 2 else None
                        l4 = result.threshold_metrics[3] if len(result.threshold_metrics) > 3 else None
                        l3_str = f"L3(>55): WR {l3.win_rate*100:.1f}% ({l3.total_signals} lệnh) EV {l3.ev_score:.5f}" if l3 else ""
                        l4_str = f"L4(>57): WR {l4.win_rate*100:.1f}% ({l4.total_signals} lệnh) EV {l4.ev_score:.5f}" if l4 else ""
                        print(f"[{s_name.upper()}] ⭐ ĐỈNH MỚI: {cfg_name} | {l3_str} | {l4_str} | VLoss: {avg_val_loss[s_id]:.5f}")

                phx = phoenixes[s_id]
                action_str = ""
                
                # Cập nhật Scheduler
                phx.scheduler.step(result.best_ev)

                if improved:
                    phx.notify_improved()
                    epoch_has_improvement = True
                else:
                    should_restart = phx.notify_no_improve()
                    if should_restart:
                        valid = [c for c in top_configs[s_id].values() if c is not None]
                        import random
                        chosen = random.choice(valid)["state_dict"] if valid else models[s_id].state_dict()
                        print(f"\n[PHOENIX #{phx.phoenix_count}] Mạng {s_id} kẹt {phx.max_stagnate} epoch. Tái sinh! (còn {phx.remaining} lần)")
                        phx.apply_perturbation(chosen)
                        action_str = "PERTURB TRIGGERED"
                    
                if str(total_epoch).endswith("0") or total_epoch == -1:
                    dt = time.time() - epoch_t0
                    ep_str = f"Ep {total_epoch}" if total_epoch >= 0 else "Ep Kế Thừa (-1)"
                    print(f"\n[Phiên {s_name.upper()} | Mạng {s_id}] {ep_str} ({dt:.1f}s) — TrLoss: {avg_train_loss[s_id]:.4f} | VLoss: {avg_val_loss[s_id]:.4f}")
                    if action_str:
                        print(f"  ↪ {action_str}")
                    print(evaluators[s_id].format_summary(result))

            total_epoch += 1

            # Save Blackbox metrics combined
            _save_blackbox_multi(run_dir, target_name, top_configs, num_target_features, num_features)
            
            # Đồng bộ lên HuggingFace nếu có bất kỳ mô hình nào được cải thiện
            if epoch_has_improvement:
                # print(f"\n[HF] Phát hiện mẫu tốt hơn. Kích hoạt đồng bộ HF...")
                try:
                    from src.orchestration.hf_sync import push_runs
                    push_runs()
                except Exception as e:
                    print(f"[HF] Lỗi sync định kỳ: {e}")
            
    except KeyboardInterrupt:
        print("\n[EMERGENCY] Dừng khẩn cấp. Đang lưu blackbox...")
        _save_blackbox_multi(run_dir, target_name, top_configs, num_target_features, num_features)

    print(f"\n[DONE] Hoàn tất quá trình Train 3 Mô Hình Độc Lập cho Phiên Á/Âu/Mỹ. | Saved to: {run_dir}")

def _save_blackbox_multi(run_dir, target_name, top_configs, num_target_features, num_features):
    """Lưu trữ metadata tổng hợp chung cho 3 Networks"""
    meta_file = os.path.join(run_dir, "training_metrix_v2.json")
    out = {
        "target": target_name,
        "version": "Independent_Multi_Session_v2.0",
        "dimensions": {
            "num_features_target": num_target_features or 0,
            "num_features_macro": (num_features - num_target_features) if num_target_features is not None else num_features,
        },
        "sessions": {}
    }
    
    for s_id, s_name in {0: "asia", 1: "london", 2: "ny"}.items():
        sess_data = {}
        for k, v in top_configs[s_id].items():
            if v is not None:
                eval_res = v.get("eval_result")
                if eval_res:
                    metrics_list = []
                    for m in eval_res.threshold_metrics:
                        metrics_list.append({
                            "threshold": m.threshold,
                            "total_signals": m.total_signals,
                            "win_rate": m.win_rate * 100,
                            "avg_win_return": m.avg_win_return,
                            "avg_loss_return": m.avg_loss_return,
                            "ev_score": m.ev_score,
                            "sharpe_score": getattr(m, 'sharpe_score', 0.0)
                        })
                    
                    sess_data[k] = {
                        "epoch": v["epoch"],
                        "max_threshold": eval_res.max_threshold,
                        "composite_score": v["score"],
                        "session_evs": eval_res.session_evs,
                        "best_ev": eval_res.best_ev,
                        "val_loss": eval_res.val_loss,
                        "threshold_metrics": metrics_list,
                        "win_rates": [m.win_rate * 100 for m in eval_res.threshold_metrics],
                        "thresholds": [m.threshold for m in eval_res.threshold_metrics],
                        "totals": [m.total_signals for m in eval_res.threshold_metrics]
                    }
                else:
                    sess_data[k] = {"score": v["score"], "epoch": v["epoch"]}
        out["sessions"][s_name] = sess_data

    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=4, ensure_ascii=False)


def _trigger_phoenix(phoenix, top_configs, best_state_dict, train_dataset, batch_size):
    """Helper: chọn config tốt nhất rồi trigger phoenix perturbation."""
    valid = [c for c in top_configs.values() if c is not None]
    chosen = random.choice(valid)["state_dict"] if valid else best_state_dict
    print(
        f"\n[PHOENIX #{phoenix.phoenix_count}] "
        f"Kẹt {phoenix.max_stagnate} epoch. Tái sinh... "
        f"(còn {phoenix.remaining} lần)"
    )
    need_reload, new_batch = phoenix.apply_perturbation(chosen)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import argparse

    BASE_PROJ = _ROOT
    
    def validate_startup_configs(cfg_dict, root_dir):
        """Kiểm tra cấu hình tại thời điểm khởi động"""
        errors = []
        tg_cfg_path = os.path.join(root_dir, "tg_config.json")
        if os.path.exists(tg_cfg_path):
            with open(tg_cfg_path, "r", encoding="utf-8") as f:
                tg = json.load(f)
                gemini = tg.get("gemini_api_key", cfg_dict.get("gemini_api_key", ""))
                hf = tg.get("hf_token", cfg_dict.get("hf_token", ""))
                
                # Không check gemini_api_key vì V2 không dùng AI supervisor
                
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

    parser = argparse.ArgumentParser(description="Training V2 — 5 Math Improvements")
    parser.add_argument("config", nargs="?", help="Đường dẫn bot_config_*.json")
    parser.add_argument(
        "--max-epoch", type=int, default=None,
        help="Giới hạn số epoch (dùng để smoke test)"
    )
    parser.add_argument(
        "--session", type=str, default="all",
        help="Session mode for compatibility with training agent orchestration"
    )
    args = parser.parse_args()

    # ── Tìm config ────────────────────────────────────────────
    config_path = args.config
    if not config_path:
        for candidate in ["data/bot_config_xau.json", "data/bot_config.json"]:
            p = os.path.join(BASE_PROJ, candidate)
            if os.path.exists(p):
                config_path = p
                break

    cfg = _load_config(config_path) if config_path else {}
    TARGET_PREFIX = cfg.get("TARGET_PREFIX", "XAUUSD")
    CONFIG_ID     = cfg.get("CONFIG_ID", "DEFAULT")
    DATA_PATH     = os.environ.get("ARGO_DATA_DIR", os.path.join(BASE_PROJ, "data"))
    
    validate_startup_configs(cfg, BASE_PROJ)

    print(f"[INIT] Config: {config_path}")
    print(f"[INIT] TARGET_PREFIX: {TARGET_PREFIX}")
    print(f"[RUN] {TARGET_PREFIX} | {CONFIG_ID} | V2.0")

    target_horizon = cfg.get("FEATURE_ENGINEERING", {}).get("TARGET_HORIZON", 5)

    # ── Đọc features đã có (từ feature_engineering.py V1) ─────
    # Ưu tiên kiểm tra trong thư mục con CONFIG_ID giống hf_sync, nếu không có thì tìm ở thư mục cha
    features_path_sub = os.path.join(DATA_PATH, str(CONFIG_ID), f"final_features_{CONFIG_ID}.parquet")
    features_path_parent = os.path.join(DATA_PATH, f"final_features_{CONFIG_ID}.parquet")
    features_path = features_path_sub if os.path.exists(features_path_sub) else features_path_parent
    
    target_path_sub = os.path.join(DATA_PATH, str(CONFIG_ID), f"target_direction_{CONFIG_ID}.parquet")
    target_path_parent = os.path.join(DATA_PATH, f"target_direction_{CONFIG_ID}.parquet")
    target_path = target_path_sub if os.path.exists(target_path_sub) else target_path_parent
    raw_price_path = None  # giá thô để tính label

    # Tìm file parquet chứa giá Close gốc (trước khi log-return transform)
    for candidate in [
        f"{TARGET_PREFIX}_MT5_1M_*.parquet",
        f"{TARGET_PREFIX.replace('_','')}_MT5_1M_*.parquet",
    ]:
        import glob
        matches = glob.glob(os.path.join(DATA_PATH, candidate))
        if matches:
            raw_price_path = matches[0]
            break

    if not os.path.exists(features_path):
        print(f"[ERROR] Chưa có file features: {features_path}")
        print("Hãy chạy feature_engineering.py trước để tạo dữ liệu.")
        sys.exit(1)

    print(f"\n[LOAD] Đang đọc features: {os.path.basename(features_path)}")
    features_raw = pd.read_parquet(features_path)

    # ── Áp QuantileTransformer V2 ──────────────────────────────
    pipeline = FeaturePipelineV2(
        target_prefix=TARGET_PREFIX,
        data_dir=DATA_PATH,
    )

    # Tách is_imputed_flag trước khi scale
    imputed_flag_col = None
    if 'is_imputed_flag' in features_raw.columns:
        imputed_flag_col = features_raw['is_imputed_flag'].copy()
        features_to_scale = features_raw.drop(columns=['is_imputed_flag'])
    else:
        features_to_scale = features_raw

    features_scaled = pipeline.fit_transform(features_to_scale)

    # Gắn lại is_imputed_flag
    if imputed_flag_col is not None:
        features_scaled['is_imputed_flag'] = imputed_flag_col.loc[features_scaled.index]

    num_features = features_scaled.shape[1]

    # ── Tạo Soft Labels từ giá thô ────────────────────────────
    print("\n[LABEL] Tạo Soft Labels (sigmoid return)...")

    if raw_price_path and os.path.exists(raw_price_path):
        raw_df = pd.read_parquet(raw_price_path)
        if raw_df.index.tz is None:
            raw_df.index = raw_df.index.tz_localize('UTC')
        close_col = [c for c in raw_df.columns if 'close' in c.lower()]
        close_series = raw_df[close_col[0]] if close_col else raw_df.iloc[:, 3]

        label_gen = SoftLabelGenerator(k=50.0, min_move_pct=0.0002, forecast_horizon=target_horizon)
        soft_labels, log_returns = label_gen.generate(close_series)
    elif os.path.exists(target_path):
        # Fallback: đọc target cũ, convert sang soft labels đọc từ parquet
        print("[LABEL] Fallback: Đọc binary labels V1, convert sang soft labels...")
        target_df = pd.read_parquet(target_path)
        hard_labels = target_df['target']
        # Chuyển hard → soft: BUY=0.85, SELL=0.15 (xấp xỉ)
        soft_labels = hard_labels.map({1: 0.85, 0: 0.15}).astype(np.float32)
        soft_labels.name = "soft_label"
        log_returns = pd.Series(
            np.where(hard_labels == 1, 0.001, -0.001),
            index=hard_labels.index, dtype=np.float32
        )
        print("[WARN] Đang dùng log_returns ước tính từ hard labels. EV sẽ không chính xác.")
    else:
        print("[ERROR] Không tìm thấy dữ liệu giá thô hoặc target. Dừng.")
        sys.exit(1)

    # ── Align features và labels ───────────────────────────────
    common_idx = features_scaled.index.intersection(soft_labels.index)
    features_aligned = features_scaled.loc[common_idx]
    soft_labels_aligned = soft_labels.loc[common_idx]
    log_returns_aligned = log_returns.loc[common_idx]

    print(f"[ALIGN] Dữ liệu cuối: {len(features_aligned):,} nến")

    # ── Tạo thư mục run ────────────────────────────────────────
    run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_clean  = TARGET_PREFIX.lower().replace("_", "")
    run_name = f"run_{run_timestamp}_{target_clean}_{CONFIG_ID}_TRANSFORMER_V2"
    log_base = os.environ.get("ARGO_LOGS_DIR", os.path.join(BASE_PROJ, "logs"))
    run_dir  = os.path.join(log_base, "runs", run_name)
    os.makedirs(run_dir, exist_ok=True)

    # Logger
    class _TeeLogger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "w", encoding="utf-8", buffering=1)
        def write(self, msg):
            self.terminal.write(msg)
            self.log.write(msg)
            self.flush()
        def flush(self):
            self.terminal.flush()
            self.log.flush()

    sys.stdout = _TeeLogger(os.path.join(run_dir, "train_v2.log"))

    # Lưu scaler_v2.pkl vào run_dir
    import shutil
    scaler_src = os.path.join(DATA_PATH, "scaler_v2.pkl")
    if os.path.exists(scaler_src):
        shutil.copy(scaler_src, os.path.join(run_dir, "scaler_v2.pkl"))
        print(f"[PACK] scaler_v2.pkl → {run_dir}")

    print(f"[RUN] {run_name}")

    # ── Chạy training ──────────────────────────────────────────
    try:
        train_v2(
            features=features_aligned,
            soft_labels=soft_labels_aligned,
            log_returns=log_returns_aligned,
            num_features=num_features,
            run_dir=run_dir,
            target_prefix=TARGET_PREFIX,
            config=cfg,
            max_epoch_override=args.max_epoch,
            config_path=args.config,
        )
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Quá trình train sụp đổ: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ── Sync lên HuggingFace ───────────────────────────────────
    # print("\n[HF] Đồng bộ cuối phiên lên HuggingFace...")
    try:
        from src.orchestration.hf_sync import push_runs
        push_runs()
    except Exception as e:
        print(f"[HF] Bỏ qua sync: {e}")
