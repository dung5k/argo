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

# --- KHÓI MODEL ĐỘC LẬP (ZERO-DEPENDENCY) ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class TimeSeriesDataset(torch.utils.data.Dataset):
    def __init__(self, features, targets, window_size=60):
        self.targets = targets
        self.window_size = window_size
        self.valid_indices = []
        if 'is_imputed_flag' in features.columns:
            flags_array = features['is_imputed_flag'].values
            for i in range(len(features) - window_size):
                window_flags_sum = sum(flags_array[i : i + window_size])
                if window_flags_sum <= (0.15 * window_size):
                    self.valid_indices.append(i)
        else:
            self.valid_indices = list(range(len(features) - window_size))
        print(f"-> [DATASET] Khởi tạo Cửa sổ Trượt: Tổng {len(features)-window_size:,} Mẫu. Loại bỏ {len(features) - window_size - len(self.valid_indices):,} Mẫu Rách (Nến Ma > 15%).")
        self.features_tensor = torch.tensor(features.values, dtype=torch.float32).to(device)
        self.targets_tensor = torch.tensor(targets.values, dtype=torch.long).to(device)

    def __len__(self): return len(self.valid_indices)

    def __getitem__(self, raw_idx):
        idx = self.valid_indices[raw_idx]
        x = self.features_tensor[idx : idx + self.window_size]
        y = self.targets_tensor[idx + self.window_size - 1]
        return x, y

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=200, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

class TransformerModel(nn.Module):
    def __init__(self, num_features, d_model=64, nhead=4, num_layers=2, dropout_rate=0.2, num_xau_features=None):
        super(TransformerModel, self).__init__()
        self.num_xau_features = num_xau_features if num_xau_features else max(1, num_features // 3)
        self.num_macro_features = num_features - self.num_xau_features
        if d_model % nhead != 0: d_model = (d_model // nhead) * nhead
        self.d_model = d_model
        
        self.xau_input_proj = nn.Linear(self.num_xau_features, d_model)
        self.xau_pos_enc = PositionalEncoding(d_model, dropout=dropout_rate)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout_rate, batch_first=True, norm_first=True
        )
        self.xau_transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers, enable_nested_tensor=False)
        
        macro_hidden = max(16, d_model // 4)
        self.macro_fc = nn.Sequential(
            nn.Linear(self.num_macro_features, d_model // 2), nn.GELU(),
            nn.LayerNorm(d_model // 2), nn.Dropout(dropout_rate),
            nn.Linear(d_model // 2, macro_hidden), nn.GELU()
        )
        
        merged_size = d_model + macro_hidden
        self.decision_head = nn.Sequential(
            nn.LayerNorm(merged_size), nn.Linear(merged_size, d_model),
            nn.GELU(), nn.Dropout(dropout_rate), nn.Linear(d_model, 2)
        )

    def forward(self, x):
        xau_feats = x[:, :, :self.num_xau_features]
        macro_feats = x[:, -1, self.num_xau_features:]
        
        xau_t = self.xau_input_proj(xau_feats)
        xau_t = self.xau_pos_enc(xau_t)
        xau_t = self.xau_transformer(xau_t)
        xau_signal = xau_t[:, -1, :]
        macro_signal = self.macro_fc(macro_feats)
        
        merged = torch.cat([xau_signal, macro_signal], dim=1)
        return self.decision_head(merged)
# --- KẾT THÚC KHỐI MODEL ---

def train_unified_model(features, targets, num_features, run_dir, target_prefix="XAU_USD"):
    """
    Train 1 model Transformer duy nhất trên toàn bộ data.
    v4.0: Phoenix Restart - Load best → Tái nạp + thay đổi chiến lược khi kẹt.
    """
    print("\n=======================================================")
    print("🧠 TRANSFORMER UNIFIED MODEL v5.0 (Deep Phoenix)     ")
    print("=======================================================")

    # === [HARDWARE CHECK] Tự động móc cấu hình GPU của Client ===
    try:
        if torch.cuda.is_available():
            print(f"🖥️ [HARDWARE] Phát hiện sư tử đá GPU: {torch.cuda.get_device_name(0)}")
        else:
            print(f"🖥️ [HARDWARE] Máy này KHÔNG CÓ GPU (đang chạy bằng sức trâu CPU).")
    except: pass

    # === CỐ ĐỊNH HYPERPARAMS V5 (Phá vỡ còng số 8 của genes cũ) ===
    window_size = 60
    d_model = 256
    nhead = 8
    num_attn_layers = 3
    dropout_rate = 0.2
    lr_base = 0.0003
    print(f"🤖 [V5 ARCHITECTURE] d_model={d_model}, nhead={nhead}, layers={num_attn_layers}, window={window_size}")

    # === PHOENIX HYPERPARAMS ===
    epochs         = 10000   # Vòng lặp tổng (Phoenix sẽ tự dừng trước)
    batch_size     = 512
    BASE_LR        = 1e-4    # LR bình thường
    MAX_STAGNATE   = 10      # Epoch không cải thiện → Tái Nạp
    MAX_PHOENIX    = 40      # Tái sinh tối đa 40 lần → dừng hẳn
    MIN_SIGNALS    = 30      # Số lệnh tối thiểu thống kê

    # === [ROLLING WINDOW] SPLIT ===
    import subprocess
    try:
        import pytz
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
        import pytz
    now_utc = pd.Timestamp.now(tz='UTC')
    val_end   = now_utc
    val_start = val_end   - pd.Timedelta(days=4)
    train_end = val_start
    train_start = train_end - pd.Timedelta(days=90)

    print(f"\n📅 [ROLLING WINDOW SPLIT]")
    print(f"   Train : {train_start.strftime('%Y-%m-%d')} → {train_end.strftime('%Y-%m-%d')} (~90 ngày)")
    print(f"   Test  : {val_start.strftime('%Y-%m-%d')} → {val_end.strftime('%Y-%m-%d')} (4 ngày thực chiến)")

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

    # === [CLASS WEIGHT] ===
    train_labels = train_targets['target'].values
    n_total = len(train_labels)
    n_buy  = (train_labels == 1).sum()
    n_sell = (train_labels == 0).sum()
    weight_sell = n_total / (2.0 * n_sell) if n_sell > 0 else 1.0
    weight_buy  = n_total / (2.0 * n_buy)  if n_buy  > 0 else 1.0
    class_weights = torch.tensor([weight_sell, weight_buy], dtype=torch.float32).to(device)
    print(f"⚖️ [Class Weight] SELL={weight_sell:.3f}, BUY={weight_buy:.3f}")
    print(f"   ({n_sell:,} Sell | {n_buy:,} Buy trong {n_total:,} mẫu Train)")

    # === DATASET & LOADER ===
    train_dataset = TimeSeriesDataset(train_features, train_targets, window_size)
    val_dataset   = TimeSeriesDataset(val_features,   val_targets,   window_size)
    train_loader  = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader    = DataLoader(val_dataset,   batch_size=batch_size, shuffle=False)

    # === MODEL ===
    meta_path = rf"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\feature_meta_{target_prefix}.json"
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

    # === [RESUME] LOAD CHECKPOINT + ĐỌC WIN RATE TỪ LỊCH SỬ ===
    runs_base = str(Path(__file__).resolve().parent.parent.parent / "runs")
    checkpoint_candidates = sorted(
        [p for p in Path(runs_base).glob(f"**/{target_name}_unified_weights.pth") if "old" not in p.parts],
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
        latest_ckpt = checkpoint_candidates[0]
        print(f"\n♻️  Tìm thấy checkpoint: {latest_ckpt}")
        try:
            state = torch.load(str(latest_ckpt), map_location=device, weights_only=True)
            
            # === TRANSFER LEARNING LOGIC ===
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

            # ĐÁNH GIÁ NGAY LẬP TỨC ĐỂ LẤY BASELINE KHÔNG PHỤ THUỘC LỊCH SỬ
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
                global_best_val_loss = avg_base_val_loss  # Cập nhật VLoss baseline
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

    # === RAM BUFFER: Lưu bản tốt nhất trong bộ nhớ ===
    best_state_dict = copy.deepcopy(model.state_dict())


    if 'top_configs' not in locals():
        top_configs = {
            "L3_1.4_L4_1.0": None,
            "L3_1.1_L4_1.0": None,
            "BEST_VLOSS": None
        }

    # === OPTIMIZER & LOSS ===
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.15)

    def make_optimizer(lr=BASE_LR):
        return optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)

    def make_scheduler(opt):
        return optim.lr_scheduler.ReduceLROnPlateau(opt, mode='max', patience=10, factor=0.5, min_lr=1e-6)

    optimizer = make_optimizer()
    scheduler = make_scheduler(optimizer)

    # === SAVE FUNCTIONS ===
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
            "top_configs_saved": top_configs_meta,
            "training_metadata": {
                "training_strategy": "Sử dụng mô hình Transformer v5.0 (Deep Phoenix), tự động tái nạp trọng số ngẫu nhiên từ Top 4 cấu hình tốt nhất nếu kẹt (Stagnation) sau 10 epoch. Dữ liệu Rolling Window: Train 90 ngày, Test thực chiến 4 ngày.",
                "selection_strategy": "Sử dụng weighted score đánh giá tổng hợp thay vì chỉ Accuracy. Tập trung bắt chính xác tín hiệu tại mốc L3 (trọng số 1.4) và L4 (trọng số 1.0) trên tổng 2.4. Top 4 mô hình được lưu độc lập.",
                "hyperparameters": {
                    "window_size": window_size,
                    "d_model": d_model,
                    "nhead": nhead,
                    "num_attn_layers": num_attn_layers,
                    "dropout_rate": dropout_rate,
                    "initial_learning_rate": BASE_LR
                },
                "data_features": features.columns.tolist() if 'features' in locals() and hasattr(features, 'columns') else "N/A"
            }
        }
        try:
            with open(blackbox_file, "w", encoding="utf-8") as bf:
                json.dump(data, bf, indent=4, ensure_ascii=False)
        except: pass

        # AUTO SYNC TO CLOUD (HUGGINGFACE) INSTEAD OF GIT
        def hf_sync_runs():
            import json
            from huggingface_hub import HfApi
            base_dir = Path(__file__).resolve().parent.parent.parent
            cfg_path = base_dir / "tg_config.json"
            
            try:
                if not cfg_path.exists():
                    print("    [HF] Không tìm thấy tg_config.json, bỏ qua đồng bộ Cloud.")
                    return
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                
                if "hf_token" not in cfg or "hf_repo_id" not in cfg:
                    print("    [HF] Chưa cấu hình hf_token hoặc hf_repo_id. Bỏ qua.")
                    return
                    
                token = cfg["hf_token"]
                repo_id = cfg["hf_repo_id"]
                runs_folder = base_dir / "runs"
                
                print(f"    [HF] ☁️ Đang đồng bộ Mốc Trọng Số lên {repo_id} (Zero-Git)...")
                api = HfApi()
                api.upload_folder(
                    folder_path=str(runs_folder),
                    path_in_repo="runs",
                    repo_id=repo_id,
                    repo_type="dataset",
                    token=token,
                    commit_message=f"Auto-Sync Best Weights: {target_name}"
                )
                print("    [HF] Đã đồng bộ kết quả lên Cổng Đám Mây thành công! 🚀")
            except Exception as e:
                print(f"    [HF LỖI PUSH] Bắn lên Đám mây thất bại: {e}")
        
        # Chạy đồng bộ ngầm
        import threading
        threading.Thread(target=hf_sync_runs, daemon=True).start()

    # === [BƯỚC ĐẦU] Lưu bản đầu tiên nếu đã load được Win Rate ===
    if resumed and global_best_score > 0:
        torch.save(model.state_dict(), model_file)
        for s_name in top_configs.keys():
            torch.save(model.state_dict(), os.path.join(run_dir, f"{target_name}_unified_weights_{s_name}.pth"))
        save_blackbox(0)
        print(f"    💾 Đã lưu các bản đầu tiên (baseline) vào run hiện tại.")

    # === PHOENIX PERTURBATION STRATEGIES ===
    def apply_perturbation(phoenix_num):
        """Áp dụng ngẫu nhiên 1 trong 4 chiến lược phá kẹt."""
        nonlocal optimizer, scheduler, batch_size

        strat = random.choice(['A', 'B', 'C', 'D'])

        if strat == 'A':
            # Chiến lược A: LR Spike - nhảy vọt LR để thoát local minima
            spike_lr = random.uniform(2e-4, 8e-4)
            optimizer = make_optimizer(lr=spike_lr)
            scheduler = make_scheduler(optimizer)
            print(f"  🔥 Chiến lược A: LR Spike → LR={spike_lr:.1e} (thoát local minima)")

        elif strat == 'B':
            # Chiến lược B: Noise Injection - cộng nhiễu Gaussian nhỏ vào weights
            noise_sigma = random.uniform(0.001, 0.005)
            with torch.no_grad():
                for param in model.parameters():
                    param.add_(torch.randn_like(param) * noise_sigma)
            optimizer = make_optimizer(lr=BASE_LR)
            scheduler = make_scheduler(optimizer)
            print(f"  🌊 Chiến lược B: Noise Injection σ={noise_sigma:.4f} (khám phá vùng lân cận)")

        elif strat == 'C':
            # Chiến lược C: LR thấp hơn + weight decay mạnh hơn để tinh chỉnh sâu
            fine_lr = random.uniform(5e-5, 2e-4)
            optimizer = optim.AdamW(model.parameters(), lr=fine_lr, weight_decay=random.uniform(1e-3, 5e-3))
            scheduler = make_scheduler(optimizer)
            print(f"  🎯 Chiến lược C: Fine-tune Sâu → LR={fine_lr:.1e}, WD tăng (tinh chỉnh precision)")

        elif strat == 'D':
            # Chiến lược D: Đổi batch size để gradient có variance khác
            new_batch = random.choice([128, 256, 384])
            batch_size = new_batch
            print(f"  🎲 Chiến lược D: Batch Shuffle → batch_size={new_batch} (gradient đa dạng hơn)")
            # Tạo lại loader với batch mới
            return True  # signal cần tạo lại loader

        return False

    # === TRAINING LOOP CHÍNH ===
    epochs_no_improve = 0
    phoenix_count     = 0
    total_epoch       = 0
    need_reload_loader = False

    import time
    try:
        while phoenix_count <= MAX_PHOENIX:
            epoch_start_time = time.time()

            # Tạo lại loader nếu Chiến lược D thay đổi batch_size
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

            # === ĐÁNH GIÁ ===
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

            # Tìm max_thresh
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

            # In log
            phoenix_tag = f"[P{phoenix_count}]" if phoenix_count > 0 else ""
            epoch_time = time.time() - epoch_start_time
            print(f"Epoch {total_epoch:04d} {phoenix_tag}| VLoss: {avg_val_loss:.4f} | LR: {cur_lr:.2e} | WR: {val_acc*100:.1f}% | MaxTh: {max_thresh:.2f} | Time: {epoch_time:.1f}s")
            thr_str = " | ".join(f">{t*100:.0f}%: {wrs[i]*100:.1f}%({totals_t[i]}L)" for i, t in enumerate(thresholds))
            print(f"  {thr_str}")

            # Cập nhật scheduler
            scheduler.step(wrs[3] if totals_t[3] > 0 else avg_val_loss)

            if avg_val_loss < global_best_val_loss:
                global_best_val_loss = avg_val_loss

            # === XÉT CẢI THIỆN ===
            is_statistically_valid = totals_t[3] >= MIN_SIGNALS
            
            # Tính điểm cho đa chiến thuật
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
                    
                    # Cập nhật parameters tổng quan đại diện
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

            # === PHOENIX RESTART ===
            if epochs_no_improve >= MAX_STAGNATE:
                phoenix_count += 1
                if phoenix_count > MAX_PHOENIX:
                    print(f"\n🦅 [PHOENIX] Đã tái sinh {MAX_PHOENIX} lần mà không vượt đỉnh {global_best_score*100:.1f}%.")
                    print(f"   → Khai thác cạn kiệt. Dừng huấn luyện, giữ nguyên bản tốt nhất.")
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
        # Restore bản tốt nhất
        model.load_state_dict(best_state_dict)
        torch.save(best_state_dict, model_file)
        print("💾 Đã khôi phục và lưu bản tốt nhất an toàn.")

    print(f"\n✅ HOÀN TẤT → Best WR: {global_best_score*100:.1f}% | Lưu: {model_file}")

    report_file = os.path.join(run_dir, "unified_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"Model: TRANSFORMER UNIFIED v4.0 (Phoenix Restart)\n")
        f.write(f"--- DỮ LIỆU ROLLING WINDOW ---\n")
        f.write(f"Train: {train_start.strftime('%Y-%m-%d')} → {train_end.strftime('%Y-%m-%d')} (~30 ngày)\n")
        f.write(f"Test : {val_start.strftime('%Y-%m-%d')} → {val_end.strftime('%Y-%m-%d')} (4 ngày thực chiến)\n\n")
        f.write(f"[Class Weight] SELL={weight_sell:.3f}, BUY={weight_buy:.3f}\n")
        f.write(f"Phân phối Train: {n_sell:,} Sell | {n_buy:,} Buy\n")
        f.write(f"Best Win Rate (L4): {global_best_score*100:.2f}% @ ngưỡng >{best_max_thresh*100:.0f}%\n")
        f.write(f"Phoenix Restarts: {phoenix_count}/{MAX_PHOENIX}\n")
        f.write(f"Tổng Epochs: {total_epoch}\n\n")
        f.write(f"--- 4 MỨC WIN-RATE THỰC CHIẾN ---\n")
        for i, (t, wr, n) in enumerate(zip(best_thresholds, best_wrs, best_totals)):
            f.write(f"L{i+1} >{t*100:.0f}%: {wr*100:.2f}% ({n:,} lệnh)\n")
    print(f"📊 Đã lưu báo cáo: {report_file}")


if __name__ == "__main__":
    import sys
    import json

    BASE_PROJ_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(BASE_PROJ_DIR, "data", "bot_config.json")
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.endswith('.json'):
                config_path = arg

    TARGET_PREFIX = "XAU_USD"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            TARGET_PREFIX = cfg.get("TARGET_PREFIX", "XAU_USD")

    data_path = os.path.join(BASE_PROJ_DIR, "data")
    features_path = os.path.join(data_path, f"final_features_{TARGET_PREFIX}.parquet")
    target_path   = os.path.join(data_path, f"target_direction_{TARGET_PREFIX}.parquet")

    if os.path.exists(features_path):
        features = pd.read_parquet(features_path)
        targets  = pd.read_parquet(target_path)
        num_features = features.shape[1]

        run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_clean = TARGET_PREFIX.lower().replace("_", "")
        run_name = f"run_{run_timestamp}_{target_clean}_TRANSFORMER"
        base_runs_dir = os.path.join(BASE_PROJ_DIR, "runs")
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
        old_dir = os.path.join(base_runs_dir, "old")
        os.makedirs(old_dir, exist_ok=True)
        # Lấy tất cả folder của riêng loại target_clean này
        type_folders = [d for d in glob.glob(os.path.join(base_runs_dir, f"run_*_{target_clean}_TRANSFORMER")) if os.path.isdir(d)]
        type_folders.sort(reverse=True) # Sắp xếp giảm dần theo thời gian (tên)
        move_folders = type_folders[3:] # Giữ lại 3 cái mới nhất
        for folder in move_folders:
            folder_name = os.path.basename(folder)
            dest = os.path.join(old_dir, folder_name)
            try:
                shutil.move(folder, dest)
                print(f"🧹 Đã di chuyển bản cũ vào kho lưu trữ (Archive): {folder_name}")
            except Exception as e:
                pass

        train_unified_model(features, targets, num_features, run_dir, target_prefix=TARGET_PREFIX)
    else:
        print(f"❌ Chưa có file features ({features_path})! Hãy chạy feature_engineering.py trước.")

