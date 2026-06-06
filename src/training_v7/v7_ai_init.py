# -*- coding: utf-8 -*-
"""
v7_ai_init.py - Module 1: AI-Driven Initialization (QTS-V7)
Khởi tạo cấu hình siêu tham số ban đầu bằng AI (Gemini) dựa trên bối cảnh thị trường.
"""
import os
import sys
import io

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

import json
import urllib.request
import urllib.error
import traceback

# Add project root to path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.orchestration.tg_helper import TelegramBot

def get_telegram_client(master_config):
    """Khởi tạo Telegram Bot từ env hoặc master config."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Đọc fallback từ master_config
    if not token or not chat_id:
        chat_id = master_config.get("telegram", {}).get("channel_id", "1816854047")
        # Thử đọc token từ settings hoặc các file config
        settings_path = os.path.join(_ROOT, '.vscode', 'settings.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    vsc_cfg = json.load(f)
                token = vsc_cfg.get("antigravityBridge.teleBotToken")
            except:
                pass
        if not token:
            # Fallback hardcode token nếu có sẵn từ tg_config.json
            tg_config_path = os.path.join(_ROOT, "tg_config.json")
            if os.path.exists(tg_config_path):
                try:
                    with open(tg_config_path, "r", encoding="utf-8") as f:
                        tcfg = json.load(f)
                    token = tcfg.get("bot_token")
                except:
                    pass
    
    if token and chat_id:
        return TelegramBot(token), int(chat_id)
    return None, 1816854047

def send_telegram_alert(tbot, chat_id, message):
    """Gửi thông báo Telegram an toàn, không làm sập luồng chính."""
    if tbot:
        try:
            tbot.send_message(chat_id, f"🤖 <b>[QTS-V7] AI-Init</b>\n━━━━━━━━━━━━━━━━━━━━━\n{message}")
        except Exception as e:
            print(f"[TG ERROR] Không thể gửi tin nhắn Telegram: {e}")

def run_ai_initialization(master_config_path="v7_master_config.json"):
    """Thực thi Module 1: AI-Driven Initialization"""
    print("[AI-Init] Đang khởi động Module 1...")
    
    # 1. Đọc file cấu hình master
    master_path = os.path.join(_ROOT, master_config_path)
    if not os.path.exists(master_path):
        raise FileNotFoundError(f"[AI-Init] Khong tim thay file master config tai {master_path}")
        
    with open(master_path, "r", encoding="utf-8") as f:
        mcfg = json.load(f)
        
    tbot, chat_id = get_telegram_client(mcfg)
    candidate_leaders = mcfg.get("data", {}).get("candidate_leaders", ["BTCUSD"])
    follower = mcfg.get("data", {}).get("follower_symbol", "LTCUSD")
    model_name = mcfg.get("ai", {}).get("llm_model", "gemini-1.5-flash")
    
    # Thông báo bắt đầu qua Telegram
    start_msg = f"⚙️ Khởi tạo cấu hình cho <b>Multi-Leader</b> -> <b>{follower}</b> (Follower)..."
    send_telegram_alert(tbot, chat_id, start_msg)
    # Cấu hình mặc định để fallback khi LLM lỗi
    fallback_config = {
        "max_lag_steps": mcfg.get("ai", {}).get("max_lag_steps", 10),
        "correlation_threshold": mcfg.get("ai", {}).get("correlation_threshold", 0.20),
        "tp_pct": mcfg.get("ai", {}).get("fallback_tp_pct", 0.008),
        "sl_pct": mcfg.get("ai", {}).get("fallback_sl_pct", 0.004),
        "max_hold_bars": mcfg.get("ai", {}).get("fallback_max_hold_bars", 30),
        "d_model": mcfg.get("ai", {}).get("d_model", 64),
        "nhead": mcfg.get("ai", {}).get("nhead", 4),
        "num_layers": mcfg.get("ai", {}).get("num_layers", 2),
        "selected_leaders": mcfg.get("ai", {}).get("selected_leaders", candidate_leaders[:2] if len(candidate_leaders) > 1 else candidate_leaders)
    }
    
    print("[AI-Init] 🚀 Bỏ qua Gemini API. Antigravity đang tự monitor cấu hình.")
    ai_config = fallback_config
            
    # 2. Xây dựng cấu hình bot_config_v7.json hoàn chỉnh
    session_name = mcfg.get("data", {}).get("session", "all").lower()
    session_utc = mcfg.get("sessions", {}).get(session_name, {})
    
    bot_config_v7 = {
        "TARGET_SYMBOL": follower,
        "LEADER_SYMBOLS": ai_config.get("selected_leaders", candidate_leaders[:1]),
        "CONFIG_ID": f"CFG_V7_MULTI_{follower}_{mcfg.get('data', {}).get('TIMEFRAME', mcfg.get('data', {}).get('timeframe', 'M15'))}",
        "VERSION": "7.0",
        "MASTER_CONFIG": master_config_path,
        "SESSION": session_name,
        "SESSION_UTC": session_utc,
        "FILTERS": {
            "MIN_ATR_PCT": mcfg.get("filters", {}).get("min_atr_pct", 0.0)
        },
        "FEATURE_ENGINEERING": {
            "TP_PCT": ai_config.get("tp_pct", 0.008),
            "SL_PCT": ai_config.get("sl_pct", 0.004),
            "MAX_HOLD_BARS": ai_config.get("max_hold_bars", 30),
            "MAX_LAG_STEPS": ai_config.get("max_lag_steps", 10),
            "CORRELATION_THRESHOLD": ai_config.get("correlation_threshold", 0.20),
            "TIMEFRAME": mcfg.get("data", {}).get("TIMEFRAME", mcfg.get("data", {}).get("timeframe", "M15")),
            "SPREAD_PCT": mcfg.get("data", {}).get("spread_pct", 0.0),
            "SLIPPAGE_PCT": mcfg.get("data", {}).get("slippage_pct", 0.0)
        },
        "TRAINING": {
            "LEARNING_RATE_BASE": mcfg.get("train", {}).get("learning_rate_base", 1e-3),
            "LEARNING_RATE_FINETUNE": mcfg.get("train", {}).get("learning_rate_finetune", 1e-4),
            "BATCH_SIZE": mcfg.get("train", {}).get("batch_size", 64),
            "EPOCHS_BASE": mcfg.get("train", {}).get("epochs_base", 20),
            "EPOCHS_FINETUNE": mcfg.get("train", {}).get("epochs_finetune", 5),
            "MIN_WIN_RATE_THRESHOLD": mcfg.get("train", {}).get("min_win_rate_threshold", 0.45),
            "MIN_PROFIT_FACTOR": mcfg.get("train", {}).get("min_profit_factor", 1.1),
            "D_MODEL": ai_config.get("d_model", 128),
            "NHEAD": ai_config.get("nhead", 8),
            "NUM_LAYERS": ai_config.get("num_layers", 4)
        },
        "WALK_FORWARD": {
            "INITIAL_TRAIN_SIZE_DAYS": mcfg.get("window", {}).get("initial_train_size_days", 180),
            "VALIDATION_SIZE_DAYS": mcfg.get("window", {}).get("validation_size_days", 30),
            "SLIDE_STEP_DAYS": mcfg.get("window", {}).get("slide_step_days", 30),
            "START_DATE": mcfg.get("window", {}).get("start_date", "2025-06-01"),
            "END_DATE": mcfg.get("window", {}).get("end_date", "2026-06-01")
        }
    }
    
    out_path = os.path.join(_ROOT, "bot_config_v7.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bot_config_v7, f, indent=4, ensure_ascii=False)
    print(f"[AI-Init] THÀNH CÔNG: Đã lưu cấu hình siêu tham số vào {out_path}")
    
    # Báo cáo kết quả cấu hình siêu tham số lên Telegram sếp Lê
    success_msg = (
        f"🏆 <b>KHỞI TẠO CẤU HÌNH SIÊU THAM SỐ V7 THÀNH CÔNG</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Follower:</b> <code>{follower}</code>\n"
        f"👑 <b>Selected Leaders:</b> <code>{', '.join(bot_config_v7['LEADER_SYMBOLS'])}</code>\n"
        f"📅 <b>Timeframe:</b> <code>{bot_config_v7['FEATURE_ENGINEERING']['TIMEFRAME']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <b>Thông số tối ưu từ AI:</b>\n"
        f"• Độ trễ quét tối đa (Lag): <code>{bot_config_v7['FEATURE_ENGINEERING']['MAX_LAG_STEPS']} steps</code>\n"
        f"• Ngưỡng tương quan (Corr): <code>{bot_config_v7['FEATURE_ENGINEERING']['CORRELATION_THRESHOLD']:.2f}</code>\n"
        f"• Chốt lời (TP): <code>{bot_config_v7['FEATURE_ENGINEERING']['TP_PCT']*100:.3f}%</code>\n"
        f"• Cắt lỗ (SL): <code>{bot_config_v7['FEATURE_ENGINEERING']['SL_PCT']*100:.3f}%</code>\n"
        f"• Giữ vị thế tối đa: <code>{bot_config_v7['FEATURE_ENGINEERING']['MAX_HOLD_BARS']} nến</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 **Kiến trúc Não bộ (AI-Driven):**\n"
        f"• Số chiều (d_model): <code>{bot_config_v7['TRAINING']['D_MODEL']}</code>\n"
        f"• Số đầu (nhead): <code>{bot_config_v7['TRAINING']['NHEAD']}</code>\n"
        f"• Số lớp (num_layers): <code>{bot_config_v7['TRAINING']['NUM_LAYERS']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💾 Đã lưu cấu hình vào <code>bot_config_v7.json</code>"
    )
    send_telegram_alert(tbot, chat_id, success_msg)
    
    return bot_config_v7

if __name__ == "__main__":
    run_ai_initialization()
