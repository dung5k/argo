# -*- coding: utf-8 -*-
"""
plotter_v3.py — Đồ họa quá trình huấn luyện V3
====================================================
Vẽ biểu đồ Win Rate và MSE Loss, gửi báo cáo qua Telegram.
"""
import os
import io
import json
import matplotlib.pyplot as plt
from typing import Optional

try:
    from src.orchestration.tg_helper import TelegramBot
except ImportError:
    pass

def plot_and_notify_v3(
    eval_res, 
    cfg_name: str, 
    epoch: int,
    run_dir: str,
    tg_config_path: str = "",
    is_periodic: bool = False
):
    """
    Vẽ biểu đồ và gửi Telegram (V3 Version).
    """
    if not eval_res.threshold_metrics:
        return
        
    thresholds = [m.threshold * 100 for m in eval_res.threshold_metrics]
    win_rates = [m.win_rate * 100 for m in eval_res.threshold_metrics]
    scores = [m.balanced_score * 100 for m in eval_res.threshold_metrics]
    signals = [m.total_signals for m in eval_res.threshold_metrics]
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Trục 1: Win Rate & Score
    color_wr = 'tab:blue'
    color_sc = 'tab:orange'
    ax1.set_xlabel('Threshold Xác Suất (%)', fontweight='bold')
    ax1.set_ylabel('Tỷ lệ (%)', color=color_wr, fontweight='bold')
    
    l1, = ax1.plot(thresholds, win_rates, color=color_wr, marker='o', linewidth=2, label='Win Rate (%)')
    l2, = ax1.plot(thresholds, scores, color=color_sc, marker='^', linewidth=2, linestyle='--', label='Balanced Score')
    ax1.tick_params(axis='y', labelcolor=color_wr)
    
    # 50% Baseline
    ax1.axhline(50.0, color='gray', linestyle=':', alpha=0.5, label='50% Win Rate')
    
    # Hiển thị số lượng signal
    for i, txt in enumerate(signals):
        ax1.annotate(f"N={txt}", (thresholds[i], win_rates[i]), 
                     textcoords="offset points", xytext=(0,10), ha='center', fontsize=9,
                     bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.3))
    
    # Setup Title và Legends
    title = f"V3 Training | {cfg_name} | Epoch: {epoch}"
    plt.title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Gộp legends
    lines = [l1, l2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left')
    
    plt.tight_layout()
    
    # Save ra file
    os.makedirs(run_dir, exist_ok=True)
    chart_path = os.path.join(run_dir, f"chart_v3_{cfg_name}_ep{epoch}.png")
    plt.savefig(chart_path, dpi=120)
    plt.close()
    
    # ==========================
    # Gửi qua Telegram
    # ==========================
    # Tự tìm đúng đường dẫn tg_config nếu không truyền vào
    if not tg_config_path:
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(os.path.dirname(_this_dir))
        _candidates = [
            os.path.join(_project_root, ".agent", "telegram_bot.json"),
            os.path.join("C:/argo/.agent", "telegram_bot.json"),
            os.path.join("C:/argo", "tg_config.json"),
            "tg_config.json",
        ]
        tg_config_path = next((p for p in _candidates if os.path.exists(p)), "")

    if tg_config_path and os.path.exists(tg_config_path):
        try:
            with open(tg_config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            bot = TelegramBot(cfg["bot_token"])
            chat_id = cfg["allowed_chat_ids"][0]
            
            # Đọc client_id: ưu tiên env var → file client_id.txt → key trong tg_config → "UnknownClient"
            client_id = os.environ.get("ARGO_CLIENT_ID", "")
            if not client_id:
                _this_dir = os.path.dirname(os.path.abspath(__file__))
                _project_root = os.path.dirname(os.path.dirname(_this_dir))
                _id_candidates = [
                    os.path.join(_project_root, ".agent", "client_id.txt"),
                    os.path.join("C:/argo/.agent", "client_id.txt"),
                    os.path.join("C:/argo", "client_id.txt"),
                ]
                for _id_file in _id_candidates:
                    if os.path.exists(_id_file):
                        with open(_id_file, "r") as _f:
                            client_id = _f.read().strip()
                        break
            if not client_id:
                import socket
                client_id = cfg.get("client_id", socket.gethostname()[:8])
            
            if is_periodic:
                pfx = f"⏳ <b>AAMT_V3 [{cfg_name}]</b> Báo cáo tiến độ trên <b>{client_id}</b> (Chưa có đỉnh mới)"
            else:
                pfx = f"🚀 <b>AAMT_V3 [{cfg_name}]</b> Đã Phá Kỷ Lục trên <b>{client_id}</b>!"
            caption = (
                f"{pfx}\n"
                f"\U0001f539 <b>Epoch:</b> {epoch}\n"
                f"\U0001f539 <b>Best Score:</b> {eval_res.composite_score():.4f}\n"
                f"\U0001f539 <b>MSE Loss:</b> {eval_res.val_mse:.4f}\n"
                f"<pre>{eval_res.format_summary()}</pre>"
            )
            bot.send_photo(chat_id, photo_path=chart_path, caption=caption)
        except Exception as e:
            print(f"  \u274c Lỗi gửi Telegram Plot: {e}", flush=True)
    else:
        print(f"  \u26a0\ufe0f Không tìm thấy file cấu hình Telegram. Bỏ qua gửi Telegram.", flush=True)
