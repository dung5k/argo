"""
train_unified.py - Unified Model v5.1: Transformer + Deep Phoenix
=================================================================
- Transformer (Multi-Head Attention), Label Smoothing, AdamW
- Phoenix Restart với Meta-AI heuristic và LLM Supervisor
- Curriculum Masking với dynamic window expansion
"""
import sys
# Bắt buộc UTF-8 stdout để chạy được trên mọi máy Windows
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
import matplotlib
matplotlib.use('Agg')  # Ép backend thread-safe trước mọi import pyplot
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legacy.train_ga import TransformerModel, TimeSeriesDataset, device
from training_v1_5.curriculum_masking import apply_curriculum_mask, resolve_masked_indices

_ROOT = Path(__file__).resolve().parent.parent.parent

from core.training.config_loader import TrainingConfig
from core.training.data_pipeline import split_train_val, compute_class_weights, make_dataloaders
from core.training.evaluation import (
    find_max_threshold, build_thresholds, compute_winrates, calc_strategy_scores,
)
from core.training.checkpoint_manager import CheckpointManager
from core.training.llm_supervisor import LLMSupervisor, TrainingState

# Set bởi __main__
is_reset: bool = False

RUN_VERSION_DESC = "Hiển thị Tên Máy Chủ (Hostname) & LLM Supervisor OTA"


# ─────────────────────────────────────────────────────────────────────
# Private training primitives — đơn giản, testable
# ─────────────────────────────────────────────────────────────────────

def _train_one_epoch(model, loader, criterion, optimizer,
                     cm_enabled, cm_active_window, cm_masked_indices, grad_clip_norm):
    """Train 1 epoch. Returns avg_train_loss (float)."""
    model.train()
    dev = next(model.parameters()).device
    total_loss = 0.0
    for batch_x, batch_y in loader:
        batch_x = batch_x.to(dev)
        batch_y = batch_y.view(-1).to(dev)
        if cm_enabled:
            batch_x = apply_curriculum_mask(batch_x, cm_active_window, cm_masked_indices)
        optimizer.zero_grad()
        out  = model(batch_x)
        loss = criterion(out, batch_y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip_norm)
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader) if len(loader) > 0 else 0.0


def _evaluate_epoch(model, loader, criterion):
    """Validate 1 epoch. Returns (avg_val_loss, val_acc, all_probs, all_labels)."""
    model.eval()
    dev = next(model.parameters()).device
    val_loss, correct, total = 0.0, 0, 0
    all_probs, all_labels = [], []
    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(dev)
            batch_y = batch_y.view(-1).to(dev)
            out  = model(batch_x)
            loss = criterion(out, batch_y)
            val_loss += loss.item()
            _, predicted = torch.max(out.data, 1)
            total   += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
            probs = F.softmax(out.data, dim=1)
            all_probs.append(probs[:, 1].cpu())
            all_labels.append(batch_y.cpu())
    all_probs  = torch.cat(all_probs)
    all_labels = torch.cat(all_labels)
    return (
        val_loss / len(loader) if len(loader) > 0 else 0.0,
        correct / total if total > 0 else 0.0,
        all_probs, all_labels,
    )


# ─────────────────────────────────────────────────────────────────────
# PhoenixMetaAI — heuristic strategy selector
# ─────────────────────────────────────────────────────────────────────

class PhoenixMetaAI:
    """
    Phân tích trend Loss/WR để chọn chiến lược perturbation khi stagnate.
    Đồng thời quản lý việc mở rộng Curriculum Masking window.
    """

    def __init__(self, start_cm_window: int, max_window: int, max_stagnate: int = 10):
        self.history = []
        self.cm_window = start_cm_window
        self.max_window = max_window
        self.max_stagnate = max_stagnate
        self.cm_expanded_count = 0

    def record_epoch(self, val_loss: float, wr: float) -> None:
        """Ghi nhận metrics của 1 epoch."""
        self.history.append({"loss": val_loss, "wr": wr})
        if len(self.history) > self.max_stagnate * 2:
            self.history.pop(0)

    def decide_strategy(self):
        """
        Trả về (strategy, expand_masking).
        strategy: 'A' (LR Spike) | 'B' (Noise) | 'C' (Fine-tune) | 'D' (Batch Shuffle)
        expand_masking: True nếu cm_window được mở rộng thêm 10.
        """
        if len(self.history) < 2:
            return 'D', False
        recent = self.history[-self.max_stagnate:]
        dloss  = recent[-1]['loss'] - recent[0]['loss']
        dwr    = recent[-1]['wr']   - recent[0]['wr']
        avg_wr = sum(h['wr'] for h in recent) / len(recent)

        expand = False
        if dwr <= 0 and self.cm_window < self.max_window:
            self.cm_window = min(self.max_window, self.cm_window + 10)
            self.cm_expanded_count += 1
            expand = True

        if dloss > 0.05 and dwr < 0:          return 'B', expand  # Overfit
        if abs(dloss) < 0.01 and abs(dwr) < 0.01: return 'A', expand  # Local minima
        if avg_wr > 0.55 and dwr <= 0:        return 'C', expand  # Fine-tune
        return 'D', expand                                          # Batch shuffle


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

# ─────────────────────────────────────────────────────────────────────
# Main training function
# ─────────────────────────────────────────────────────────────────────

def train_unified_model(features, targets, num_features, run_dir, target_prefix="XAU_USD"):
    """
    Train 1 Transformer model Unified V2.

    Args:
        features      : DataFrame features có DatetimeIndex với timezone.
        targets       : DataFrame targets với cột 'target'.
        num_features  : Số features (features.shape[1]).
        run_dir       : Thư mục lưu kết quả run hiện tại.
        target_prefix : Tên symbol (VD: 'XAUUSD').
    """
    import time

    # ── Performance Mode ──────────────────────────────────────────
    perf_mode = os.environ.get("PERFORMANCE_MODE", "MAX").upper()
    if perf_mode == "LIGHT":
        import multiprocessing
        t = max(1, multiprocessing.cpu_count() // 2)
        torch.set_num_threads(t)
        print(f"[{perf_mode} MODE] 🌿 Giới hạn {t} CPU luồng.")
    else:
        print(f"[{perf_mode} MODE] 🚀 Tối đa hiệu suất.")

    print("=======================================================")
    print("🧠 TRANSFORMER UNIFIED MODEL v5.1 (Deep Phoenix)     ")
    print("=======================================================")
    try:
        hw = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only"
        print(f"🖥️  {hw}")
    except Exception:
        pass

    # ── 1. Load Config ────────────────────────────────────────────
    cfg = TrainingConfig.load(base_proj=str(_ROOT))
    for i, a in enumerate(sys.argv):
        if a == "--session" and i + 1 < len(sys.argv):
            cfg.session = sys.argv[i + 1].lower()

    print(f"🤖 [ARCH] d_model={cfg.d_model}, nhead={cfg.nhead}, "
          f"layers={cfg.num_attn_layers}, win={cfg.window_size}, session={cfg.session.upper()}")

    MAX_STAGNATE           = cfg.max_stagnate
    MAX_PHOENIX            = cfg.max_phoenix
    MIN_SIGNALS            = cfg.min_signals
    BASE_LR                = cfg.base_lr
    AI_SUPERVISOR_INTERVAL = cfg.ai_supervisor_interval
    batch_size             = cfg.batch_size

    # ── 2. Data split ─────────────────────────────────────────────
    print(f"\n📅 Train {cfg.train_start.strftime('%Y-%m-%d')} → "
          f"{cfg.train_end.strftime('%Y-%m-%d')} | "
          f"Val → {cfg.val_end.strftime('%Y-%m-%d')}")

    tr_feat, tr_tgt, val_feat, val_tgt = split_train_val(
        features, targets,
        cfg.train_start, cfg.train_end, cfg.val_start, cfg.val_end,
    )
    
    train_loader, val_loader, train_dataset, val_dataset = make_dataloaders(
        tr_feat, tr_tgt, val_feat, val_tgt, cfg.window_size, batch_size,
        session=cfg.session
    )

    print(f"  Train: {len(train_dataset):,} | Val: {len(val_dataset):,} nến (Session: {cfg.session.upper()})")
    if len(tr_feat) <= cfg.window_size or len(val_feat) <= cfg.window_size:
        print("⚠️ Dữ liệu quá cạn!")
        return

    class_weights = compute_class_weights(tr_tgt["target"].values, device)
    n_sell = int((tr_tgt["target"].values == 0).sum())
    n_buy  = int((tr_tgt["target"].values == 1).sum())
    print(f"⚖️ SELL={class_weights[0]:.3f} BUY={class_weights[1]:.3f} "
          f"({n_sell:,} SELL | {n_buy:,} BUY)")


    # ── 3. Curriculum Masking setup ───────────────────────────────
    cm_enabled        = cfg.cm_enabled
    cm_active_window  = cfg.cm_active_window
    cm_masked_names   = cfg.cm_masked_features
    feature_col_names = list(features.columns)
    cm_masked_indices = resolve_masked_indices(feature_col_names, cm_masked_names) if cm_enabled else []

    print("\n" + "══" * 28)
    if cm_enabled:
        print(f"[CURRICULUM] BẬT | Window: {cm_active_window}/{cfg.window_size} nến")
    else:
        print(f"[CURRICULUM] TẮT | Symbol: {target_prefix}")
    print("══" * 28 + "\n")

    # ── 4. Build model ────────────────────────────────────────────
    meta_path = os.path.join(cfg.argo_data_dir, f"feature_meta_{target_prefix}.json")
    num_xau_features = None
    target_name = target_prefix.lower().replace("_", "")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        num_xau_features = meta.get("num_xau_features")
        target_name = meta.get("target_prefix", target_prefix).lower().replace("_", "")
        print(f"🧬 TARGET={num_xau_features} | Macro={num_features - (num_xau_features or 0)}")

    model = TransformerModel(
        num_features, d_model=cfg.d_model, nhead=cfg.nhead,
        num_layers=cfg.num_attn_layers, dropout_rate=cfg.dropout_rate,
        num_xau_features=num_xau_features,
    ).to(device)

    # ── 5. Checkpoint ─────────────────────────────────────────────
    ckpt = CheckpointManager(
        run_dir=run_dir,
        runs_base=os.path.join(cfg.argo_logs_dir, "runs"),
        target_name=target_name,
        cfg_id=cfg.config_id,
        device=device,
    )
    ckpt_candidates = ckpt.find_candidates()

    global_best_score    = 0.0
    global_best_val_loss = float("inf")
    best_thresholds = [0.50] * 4
    best_wrs        = [0.0]  * 4
    best_totals     = [0]    * 4
    best_max_thresh = 0.50
    top_configs: dict = {
        "L3_1.4_L4_1.0": None,
        "L3_1.1_L4_1.0": None,
        "BEST_VLOSS":     None,
    }

    if is_reset and ckpt_candidates:
        print(f"\n🧹 [RESET] Dọn {len(ckpt_candidates)} checkpoint rác...")
        ckpt.delete_candidates(ckpt_candidates)
        ckpt_candidates = []

    resumed = False
    best_state_dict = copy.deepcopy(model.state_dict())

    if ckpt_candidates:
        latest = ckpt_candidates[int(len(ckpt_candidates) > 1)]
        print(f"\n♻️  Checkpoint: {latest}")
        resumed = ckpt.load_transfer(model, latest)
        model = model.to(device)
        if resumed:
            base_crit = FocalLoss(weight=class_weights, gamma=2.0, label_smoothing=0.15).to(device)
            bvloss, _, bprobs, blabels = _evaluate_epoch(model, val_loader, base_crit)
            max_t = find_max_threshold(bprobs, MIN_SIGNALS)
            thrs  = build_thresholds(max_t)
            wrs, tots = compute_winrates(bprobs, blabels, thrs)
            if tots[3] >= MIN_SIGNALS:
                bscores = calc_strategy_scores(wrs, bvloss)
                for sn, sv in bscores.items():
                    top_configs[sn] = {
                        "score": sv, "epoch": 0,
                        "state_dict": copy.deepcopy(model.state_dict()),
                        "thresholds": thrs[:], "wrs": wrs[:],
                        "totals": tots[:], "max_thresh": max_t,
                    }
                global_best_score    = bscores["L3_1.4_L4_1.0"]
                global_best_val_loss = bvloss
                best_wrs, best_totals, best_thresholds, best_max_thresh = wrs, tots, thrs, max_t
                best_state_dict = copy.deepcopy(model.state_dict())
                thr_str = " | ".join(f">{t*100:.0f}%: {wrs[i]*100:.1f}%({tots[i]}L)"
                                     for i, t in enumerate(thrs))
                print(f"    📊 Baseline: {global_best_score*100:.1f}% VLoss={bvloss:.4f}")
                print(f"    {thr_str}")
    else:
        print("\n📌 Không có checkpoint. Khởi tạo model mới.")

    sess_suffix = f"_{cfg.session}" if cfg.session != "all" else ""
    model_file = os.path.join(run_dir, f"{target_name}_unified_weights{sess_suffix}.pth")
    if resumed and global_best_score > 0:
        ckpt.save_best_weights(best_state_dict)
        for sn in top_configs:
            ckpt.save_ranked_weights(model, sn)
        ckpt.save_blackbox(0, global_best_score, global_best_val_loss,
                           best_max_thresh, best_thresholds, best_wrs, best_totals,
                           top_configs, target_prefix)
        print("    💾 Đã lưu baseline.")

    # ── 6. Optimizer / Criterion helpers ─────────────────────────
    def make_optimizer(lr=BASE_LR):
        return torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)

    def make_scheduler(opt):
        return torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, mode="max", patience=10, factor=0.5, min_lr=1e-6)

    def make_criterion(label_smoothing=0.15):
        return FocalLoss(
            weight=class_weights, gamma=2.0, label_smoothing=label_smoothing).to(device)

    optimizer      = make_optimizer()
    scheduler      = make_scheduler(optimizer)
    criterion      = make_criterion()
    grad_clip_norm = 1.0

    # ── 7. Meta-AI + perturbation ─────────────────────────────────
    meta_ai = PhoenixMetaAI(
        start_cm_window=cm_active_window if cm_enabled else cfg.window_size,
        max_window=cfg.window_size,
        max_stagnate=MAX_STAGNATE,
    )

    def apply_perturbation(_phoenix_num):
        """Áp dụng chiến lược đột biến sau Phoenix restart. Returns False."""
        nonlocal optimizer, scheduler, batch_size, cm_active_window, BASE_LR, train_loader
        strat, expanded = meta_ai.decide_strategy()
        if expanded and cm_enabled:
            cm_active_window = meta_ai.cm_window
            print(f"  👁️ [META-AI] Mở rộng tầm nhìn → {cm_active_window} nến")
        if strat == 'A':
            lr = random.uniform(2e-4, 8e-4)
            optimizer = make_optimizer(lr=lr)
            scheduler = make_scheduler(optimizer)
            print(f"  🧠 [META-AI] Local Minima → A: LR Spike ({lr:.1e})")
        elif strat == 'B':
            sigma = random.uniform(0.002, 0.008)
            with torch.no_grad():
                for p in model.parameters():
                    p.add_(torch.randn_like(p) * sigma)
            optimizer = make_optimizer(lr=BASE_LR)
            scheduler = make_scheduler(optimizer)
            print(f"  🧠 [META-AI] Overfit → B: Noise σ={sigma:.4f}")
        elif strat == 'C':
            lr = random.uniform(1e-5, 8e-5)
            optimizer = torch.optim.AdamW(
                model.parameters(), lr=lr,
                weight_decay=random.uniform(5e-3, 1e-2))
            scheduler = make_scheduler(optimizer)
            print(f"  🧠 [META-AI] Chững WR → C: Fine-tune {lr:.1e}")
        elif strat == 'D':
            new_bs = random.choice([128, 256, 384, 512])
            batch_size = new_bs
            train_loader = DataLoader(train_dataset, batch_size=new_bs, shuffle=True)
            print(f"  🧠 [META-AI] Nhiễu loạn → D: Batch {new_bs}")
        return False

    # ── 8. LLM Supervisor ─────────────────────────────────────────
    sv_path = str(_ROOT / "src" / "training_v1_5" / "ai_supervisor.py")
    llm_sv  = LLMSupervisor(sv_path, str(_ROOT), target_prefix)

    # ── 9. Training Loop ──────────────────────────────────────────
    model = model.to(device)
    epochs_no_improve  = 0
    phoenix_count      = 0
    total_epoch        = 0
    need_reload_loader = False

    try:
        while phoenix_count <= MAX_PHOENIX:
            epoch_start = time.time()

            if need_reload_loader:
                train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
                need_reload_loader = False

            # Train
            avg_train_loss = _train_one_epoch(
                model, train_loader, criterion, optimizer,
                cm_enabled, cm_active_window, cm_masked_indices, grad_clip_norm,
            )

            # Diagnostic batch (chỉ epoch đầu)
            if total_epoch == 0:
                s = next(iter(train_loader))[0]
                print(f"[DIAG] Batch shape: {list(s.shape)}")
                if cm_enabled:
                    print(f"[DIAG] Active window last {cm_active_window} nến, "
                          f"sample[-1,:4]: {s[0,-1,:4].tolist()}")

            # Evaluate
            avg_val_loss, val_acc, all_probs, all_labels = _evaluate_epoch(
                model, val_loader, criterion,
            )
            max_thresh = find_max_threshold(all_probs, MIN_SIGNALS)
            thresholds = build_thresholds(max_thresh)
            wrs, totals_t = compute_winrates(all_probs, all_labels, thresholds)

            cur_lr = optimizer.param_groups[0]["lr"]
            total_epoch += 1
            meta_ai.record_epoch(avg_val_loss, val_acc)

            p_tag    = f"[P{phoenix_count}]" if phoenix_count > 0 else ""
            thr_str  = " | ".join(f">{t*100:.0f}%: {wrs[i]*100:.1f}%({totals_t[i]}L)"
                                   for i, t in enumerate(thresholds))
            elapsed  = time.time() - epoch_start
            print(f"Epoch {total_epoch:04d} {p_tag}| "
                  f"TLoss:{avg_train_loss:.4f} VLoss:{avg_val_loss:.4f} "
                  f"LR:{cur_lr:.2e} WR:{val_acc*100:.1f}% MaxTh:{max_thresh:.2f} [{elapsed:.1f}s]")
            print(f"  {thr_str}")

            scheduler.step(wrs[3] if totals_t[3] > 0 else avg_val_loss)
            if avg_val_loss < global_best_val_loss:
                global_best_val_loss = avg_val_loss

            # Cập nhật top_configs nếu hợp lệ
            current_scores      = calc_strategy_scores(wrs, avg_val_loss)
            improved_strategies = []

            if totals_t[3] >= MIN_SIGNALS:
                for sn, sv in current_scores.items():
                    if top_configs[sn] is None or sv > top_configs[sn]["score"]:
                        top_configs[sn] = {
                            "score": sv, "epoch": total_epoch,
                            "state_dict": copy.deepcopy(model.state_dict()),
                            "thresholds": thresholds[:], "wrs": wrs[:],
                            "totals": totals_t[:], "max_thresh": max_thresh,
                        }
                        ckpt.save_ranked_weights(model, sn)
                        improved_strategies.append(sn)

                if improved_strategies:
                    epochs_no_improve = 0
                    valid_cfgs = [c for c in top_configs.values() if c is not None]
                    best_cfg   = max(valid_cfgs, key=lambda x: x["score"])
                    global_best_score = best_cfg["score"]
                    best_thresholds   = best_cfg["thresholds"]
                    best_wrs          = best_cfg["wrs"]
                    best_totals       = best_cfg["totals"]
                    best_max_thresh   = best_cfg["max_thresh"]
                    best_state_dict   = copy.deepcopy(best_cfg["state_dict"])
                    ckpt.save_best_weights(best_state_dict)
                    ckpt.save_blackbox(
                        total_epoch, global_best_score, global_best_val_loss,
                        best_max_thresh, best_thresholds, best_wrs, best_totals,
                        top_configs, target_prefix,
                    )
                    thr_details = " | ".join(f">{t*100:.0f}%: {w*100:.1f}%({totals_t[i]}L)"
                                             for i, (t, w) in enumerate(zip(thresholds, wrs)))
                    peak_msg = (f"  🏆 ĐỈNH MỚI CHO TIÊU CHÍ: [{', '.join(improved_strategies)}] "
                                f"MaxTh={max_thresh:.2f} | {thr_details}")
                    try:
                        import matplotlib.pyplot as plt
                        chart_path = os.path.join(run_dir, f"peak_chart_ep{total_epoch}.png")
                        
                        plot_thresholds = [x / 100.0 for x in range(50, 101)]
                        plot_wrs, plot_totals = compute_winrates(all_probs, all_labels, plot_thresholds)
                        
                        plt.figure(figsize=(10, 5))
                        valid_x, valid_y, valid_tot = [], [], []
                        for t, w, tot in zip(plot_thresholds, plot_wrs, plot_totals):
                            if tot > 0:
                                valid_x.append(t*100)
                                valid_y.append(w*100)
                                valid_tot.append(tot)
                                
                        plt.plot(valid_x, valid_y, marker='o', linestyle='-', color='indigo', linewidth=2)
                        
                        latest_xv = -100
                        for xv, yv, tot in zip(valid_x, valid_y, valid_tot):
                            if xv - latest_xv >= 2.5 or abs((xv/100) - max_thresh) < 0.01:
                                plt.text(xv, yv + 0.5, f"{yv:.1f}%\n({tot}L)", fontsize=8, ha='center', va='bottom')
                                latest_xv = xv
                                
                        plt.title(f"[{target_prefix}] Epoch {total_epoch} | MaxTh={max_thresh:.2f}\nTiêu chí: {', '.join(improved_strategies)}", fontsize=11, pad=12, fontweight='bold', color='darkred')
                        plt.xlabel("Threshold (%)")
                        plt.ylabel("Win Rate (%)")
                        plt.grid(True, linestyle='--', alpha=0.6)
                        if valid_y:
                            plt.ylim(min(45, min(valid_y)-5), max(85, max(valid_y)+5))
                        if valid_x:
                            plt.xlim(49, max(valid_x) + 1)
                        plt.tight_layout()
                        plt.savefig(chart_path)
                        plt.close()
                        
                        # In đồng thời để tránh lỗi Agent đọc log bị "cắt khúc" và gửi sai/thiếu Chart
                        print(f"{peak_msg}\n[CHART] {chart_path}")
                    except Exception as e:
                        print(f"{peak_msg}")
                        print(f"  [ERROR] Lỗi vẽ chart: {e}")
                else:
                    epochs_no_improve += 1
            else:
                epochs_no_improve += 1

            # Phoenix restart
            if epochs_no_improve >= MAX_STAGNATE:
                phoenix_count += 1
                if phoenix_count > MAX_PHOENIX:
                    print(f"\n🦅 [PHOENIX] Đã tái sinh {MAX_PHOENIX} lần.")
                    break
                valid_cfgs = [c for c in top_configs.values() if c is not None]
                chosen     = (random.choice(valid_cfgs) if valid_cfgs
                              else {"score": 0, "state_dict": best_state_dict})
                print(f"\n🔁 [PHOENIX #{phoenix_count}] Kẹt {epochs_no_improve} epoch "
                      f"(Score={chosen['score']*100:.1f}%)...")
                model.load_state_dict(copy.deepcopy(chosen["state_dict"]))
                epochs_no_improve = 0
                apply_perturbation(phoenix_count)
                print(f"   → Còn {MAX_PHOENIX - phoenix_count} lần\n")

            # LLM Supervisor
            if total_epoch > 0 and total_epoch % AI_SUPERVISOR_INTERVAL == 0:
                print(f"\n🤖 [LLM SUPERVISOR] Phân tích epoch {total_epoch}...")
                ll_state = TrainingState(
                    history=list(meta_ai.history),
                    lr=cur_lr, base_lr=BASE_LR,
                    weight_decay=optimizer.param_groups[0].get("weight_decay", 1e-3),
                    min_signals=MIN_SIGNALS,
                    cm_active_window=cm_active_window,
                    window_size=cfg.window_size,
                    patience=scheduler.patience,
                    label_smoothing=(criterion.label_smoothing
                                     if hasattr(criterion, "label_smoothing") else 0.15),
                    batch_size=batch_size,
                    grad_clip=grad_clip_norm,
                    masked_features=cm_masked_names,
                    totals_t=totals_t,
                    phoenix_count=phoenix_count,
                )
                ctx  = llm_sv.build_context(ll_state, total_epoch)
                resp = llm_sv.call(ctx, total_epoch)
                if resp:
                    print(f"🤖 {resp.get('analysis_report', '')}")
                    tel = resp.get("telegram_message", "")
                    if tel:
                        print(f"  Telegram: {tel}")
                        llm_sv.send_telegram(tel)
                    ll_state = llm_sv.apply_actions(
                        resp, ll_state, optimizer, scheduler,
                        make_criterion, resolve_masked_indices, feature_col_names,
                        class_weights, device, nn,
                    )
                    # Đồng bộ lại từ LLM state
                    BASE_LR          = ll_state.base_lr
                    MIN_SIGNALS      = ll_state.min_signals
                    cm_active_window = ll_state.cm_active_window
                    meta_ai.cm_window = cm_active_window
                    cm_masked_names  = ll_state.masked_features
                    if hasattr(ll_state, "_new_masked_indices"):
                        cm_masked_indices = ll_state._new_masked_indices
                    if hasattr(ll_state, "_new_criterion"):
                        criterion = ll_state._new_criterion
                    grad_clip_norm   = ll_state.grad_clip
                    if ll_state.need_reload_loader:
                        batch_size   = ll_state.batch_size
                        train_loader = DataLoader(
                            train_dataset, batch_size=batch_size, shuffle=True)
                    if ll_state.force_phoenix:
                        epochs_no_improve = MAX_STAGNATE

    except KeyboardInterrupt:
        print("\n⚡ [KHẨN CẤP] Ctrl+C. Lưu hộp đen...")
        ckpt.save_blackbox(
            total_epoch, global_best_score, global_best_val_loss,
            best_max_thresh, best_thresholds, best_wrs, best_totals,
            top_configs, target_prefix, is_interrupted=True,
        )
        model.load_state_dict(best_state_dict)
        ckpt.save_best_weights(best_state_dict)

    print(f"\n✅ HOÀN TẤT → Best Score: {global_best_score*100:.1f}% | Lưu: {model_file}")


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

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
    CONFIG_ID     = "DEFAULT"
    cfg_raw: dict = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg_raw = json.load(f)
            TARGET_PREFIX = cfg_raw.get("TARGET_PREFIX", "XAUUSD")
            CONFIG_ID     = cfg_raw.get("CONFIG_ID", "DEFAULT")

    is_reset = "--reset" in sys.argv
    session_arg = "all"
    for i, a in enumerate(sys.argv):
        if a == "--session" and i + 1 < len(sys.argv):
            session_arg = sys.argv[i + 1].lower()

    if is_reset:
        print("[INIT] KÍCH HOẠT DỌN RÁC (--reset): Sẽ xóa checkpoint rác.")

    print(f"[INIT] Config: {config_path}")
    print(f"[INIT] TARGET_PREFIX: {TARGET_PREFIX} | SESSION: {session_arg.upper()}")

    _proj_data = os.path.join(BASE_PROJ_DIR, "data")
    _proj_logs = os.path.join(BASE_PROJ_DIR, "logs")
    if os.name == 'nt':
        _proj_data = "C:\\argo\\data"
        _proj_logs = "C:\\argo\\logs"
        
    ARGO_DATA_DIR = cfg_raw.get("ARGO_DATA_DIR",
                                os.environ.get("ARGO_DATA_DIR", _proj_data))
    ARGO_LOGS_DIR = cfg_raw.get("ARGO_LOGS_DIR",
                                os.environ.get("ARGO_LOGS_DIR", _proj_logs))
    data_path = ARGO_DATA_DIR

    # Sync dữ liệu từ HuggingFace
    try:
        sys.path.insert(0, os.path.join(str(_ROOT), "src", "orchestration"))
        from hf_sync import pull_data, pull_runs
        print("☁️ [TRAIN] Đồng bộ HF theo REQUIRED_PARQUETS và Runs cụ thể...")
        pull_data(config_path=config_path)
        
        target_clean = TARGET_PREFIX.lower().replace("_", "")
        pull_runs(target_prefix=target_clean, config_id=CONFIG_ID)
    except Exception as e:
        print(f"⚠️ [TRAIN] Bỏ qua đồng bộ HF: {e}")
        
    # ===== INHERIT CONFIG FROM HF =====
    base_runs_dir = os.path.join(ARGO_LOGS_DIR, "runs")
    target_clean = TARGET_PREFIX.lower().replace("_", "")
    try:
        import glob
        folders = glob.glob(os.path.join(base_runs_dir, f"run_*_{target_clean}_{CONFIG_ID}_*"))
        folders.sort(reverse=True)
        for folder in folders:
            if glob.glob(os.path.join(folder, "*.pth")):
                inherited_cfg = os.path.join(folder, f"config_{CONFIG_ID}.json")
                if os.path.exists(inherited_cfg):
                    print(f"🔄 [INIT] PHÁT HIỆN KẾ THỪA: Đang ghi đè cấu hình hiện tại bằng cấu hình từ HF ({inherited_cfg})")
                    with open(inherited_cfg, "r", encoding="utf-8") as f:
                        cfg_raw.update(json.load(f))
                        TARGET_PREFIX = cfg_raw.get("TARGET_PREFIX", TARGET_PREFIX)
                        CONFIG_ID     = cfg_raw.get("CONFIG_ID", CONFIG_ID)
                    config_path = inherited_cfg
                break
    except Exception as e:
        print(f"⚠️ [INIT] Lỗi khi kiểm tra cấu hình kế thừa: {e}")
    # ==================================

    features_path = os.path.join(data_path, CONFIG_ID, f"final_features_{CONFIG_ID}.parquet")
    target_path   = os.path.join(data_path, CONFIG_ID, f"target_direction_{CONFIG_ID}.parquet")

    if not os.path.exists(target_path):
        fallback = os.path.join(data_path, CONFIG_ID, "target_direction.parquet")
        if os.path.exists(fallback):
            target_path = fallback

    # Diagnostic
    print(f"\n[INIT] Features: {features_path}")
    print("\n🔍 --- CHẨN ĐOÁN DỮ LIỆU ---")
    print(f"  Config: {os.path.basename(config_path) if config_path else 'None'} | ID: {CONFIG_ID}")
    import glob
    raw_files = glob.glob(os.path.join(data_path, "*_1m_*.parquet"))
    for fp in raw_files:
        sz = os.path.getsize(fp) / (1024 * 1024)
        print(f"  - {os.path.basename(fp)} ({sz:.1f} MB)")
    if os.path.exists(features_path):
        fsz = os.path.getsize(features_path) / (1024 * 1024)
        print(f"  Features đã gộp: {os.path.basename(features_path)} ({fsz:.1f} MB)")
    print("-" * 50 + "\n")

    if not os.path.exists(features_path):
        print(f"❌ Chưa có file features ({features_path})! Hãy chạy feature_engineering.py trước.")
        sys.exit(1)

    features     = pd.read_parquet(features_path)
    targets_data = pd.read_parquet(target_path)
    num_features = features.shape[1]

    run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_clean  = TARGET_PREFIX.lower().replace("_", "")
    run_name      = f"run_{run_timestamp}_{target_clean}_{CONFIG_ID}_TRANSFORMER"
    base_runs_dir = os.path.join(ARGO_LOGS_DIR, "runs")
    run_dir       = os.path.join(base_runs_dir, run_name)
    os.makedirs(run_dir, exist_ok=True)

    class TeeLogger:
        """Ghi stdout ra cả terminal và file log."""
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
    print(f"📁 Run dir: {run_name}")
    print(f"[VERSION_INFO] Tích hợp tính năng: {RUN_VERSION_DESC}")

    # Copy config to run_dir so it gets pushed to HF next time
    import shutil
    try:
        if config_path and os.path.exists(config_path):
            shutil.copy(config_path, os.path.join(run_dir, f"config_{CONFIG_ID}.json"))
    except Exception:
        pass

    # Copy scaler
    import shutil
    scaler_src = os.path.join(data_path, CONFIG_ID, f"scaler_{CONFIG_ID}.pkl")
    if os.path.exists(scaler_src):
        shutil.copy(scaler_src, os.path.join(run_dir, f"scaler_{CONFIG_ID}.pkl"))
        print(f"📦 Đóng gói scaler_{CONFIG_ID}.pkl vào run dir.")
    else:
        print(f"⚠️ Không tìm thấy scaler: {scaler_src}")

    # Archive run cũ
    old_dir = os.path.join(base_runs_dir, "old")
    os.makedirs(old_dir, exist_ok=True)
    type_folders = [d for d in glob.glob(
        os.path.join(base_runs_dir, f"run_*_{target_clean}_*TRANSFORMER"))
        if os.path.isdir(d)]
    type_folders.sort(reverse=True)
    for folder in type_folders[3:]:
        dest = os.path.join(old_dir, os.path.basename(folder))
        try:
            shutil.move(folder, dest)
            print(f"🧹 Archive: {os.path.basename(folder)}")
        except Exception:
            pass

    # Train
    print("[INIT] Calling train_unified_model...")
    sys.stdout.flush()
    try:
        train_unified_model(features, targets_data, num_features, run_dir, target_prefix=TARGET_PREFIX)
    except Exception as e:
        import traceback
        msg = f"[CRASH DETECTED] {traceback.format_exc()}"
        sys.__stderr__.write(msg)
        sys.__stderr__.flush()
        print(msg)
        sys.exit(1)

    # Final HF sync
    print("☁️ KẾT THÚC TRAIN: Đồng bộ cuối lên HuggingFace...")
    try:
        src_path = os.path.join(BASE_PROJ_DIR, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        from orchestration.hf_sync import push_runs
        push_runs()
    except Exception as e:
        print(f"❌ Lỗi sync cuối: {e}")
