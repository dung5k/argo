import os
import sys
import io
import time
import json
import threading
import psutil

if sys.stdout is not None:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass
import tkinter as tk
from datetime import datetime, timezone

safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.bot_v3.cloud_manager_v3 import V3CloudManager
from src.bot_v3.data_processor_v3 import V3DataProcessor
from src.bot_v3.inference_engine_v3 import V3InferenceEngine
from src.bot_v3.trade_manager_v3 import V3TradeManager
from src.bot_v3.binance_trade_manager_v3 import BinanceTradeManagerV3
from src.bot_v3.binance_spot_trade_manager_v3 import BinanceSpotTradeManagerV3
from src.bot_v3.simulated_trade_manager_v3 import SimulatedTradeManagerV3
from src.bot_v3.config_loader_v3 import V3ConfigLoader
from src.core.mt5_data_manager import MT5DataManager
import logging

log_dir = os.path.join(safe_script_dir, "workspaces", "shared_meta", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"trade_bot_v3_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
bot_start_time = time.time()
G_CURRENT_PRICE = 0.0

def kill_old_instances():
    """Kill other processes running bot_v3.py with the same config file using a PID file."""
    current_pid = os.getpid()
    target_config = ""
    if len(sys.argv) > 1:
        json_args = [arg for arg in sys.argv if arg.endswith('.json')]
        if json_args:
            target_config = os.path.basename(json_args[0])
    
    if not target_config:
        return

    pid_dir = os.path.join(safe_script_dir, "temp")
    os.makedirs(pid_dir, exist_ok=True)
    pid_file = os.path.join(pid_dir, f"bot_{target_config}.pid")

    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            
            if psutil.pid_exists(old_pid) and old_pid != current_pid:
                proc = psutil.Process(old_pid)
                cmdline = proc.cmdline()
                # Verify it's the same bot and config
                if any('bot_v3.py' in arg for arg in cmdline) and any(target_config in arg for arg in cmdline):
                    print(f"[PROCESS] ⚠️ Đang KILL tiến trình cũ PID {old_pid} ({target_config})")
                    proc.kill()
                    print(f"[PROCESS] ✅ Đã KILL {old_pid}")
        except Exception as e:
            print(f"[PROCESS] ⚠️ Lỗi khi xử lý PID cũ: {e}")

    try:
        with open(pid_file, "w") as f:
            f.write(str(current_pid))
    except Exception as e:
        print(f"[PROCESS] ⚠️ Không thể ghi PID file: {e}")

kill_old_instances()

def custom_print(*args, **kwargs):
    msg = " ".join(map(str, args))
    
    # 0. Chặn Cứng Log Rác (Luôn luôn bỏ qua dù trong bất kỳ hoàn cảnh nào)
    spam_kws = ["Chu kỳ #", "Quét các cổng MT5", "Nến M1 Mới"]
    if any(k in msg for k in spam_kws):
        return

    # 1. Force log cho các sự kiện CỰC QUAN TRỌNG (Lỗi, Mở/Đóng lệnh)
    force_print_kws = ["❌", "⚠️", "✅", "FATAL", "Exception", "Lỗi", "ĐÃ BẮN LỆNH", "CHỐT", "ĐẢO CHIỀU", "Bắt đầu Pipeline", "Kêt quả | Hành động", "Binance", "TradeManager", "🟢", "🔴"]
    if any(k in msg for k in force_print_kws):
        logging.info(msg)
        return

    # 2. Thời gian đầu khởi động (300 giây đầu tiên tương đương 5 phút)
    if time.time() - bot_start_time < 300:
        logging.info(msg)
        return

    # Biến toàn cục từ core
    tm = globals().get('trade_manager')
    g_probs = globals().get('gui_probs')
    cfg = globals().get('CONFIG', {})

    # 3. Thời gian đang có vị thế (Đang giữ lệnh)
    has_position = False
    if tm and hasattr(tm, 'active_trade_loggers'):
        if len(tm.active_trade_loggers) > 0:
            has_position = True

    if has_position:
        pnl_report = ""
        if hasattr(tm, 'get_active_positions_report'):
            # Lấy chuỗi mô tả vị thế hiện tại và thay thế xuống dòng bằng dấu phân cách
            pnl_report = tm.get_active_positions_report().replace('\n', ' | ')
        if hasattr(tm, '_get_daily_pnl'):
            try:
                daily_pnl = tm._get_daily_pnl()
                pnl_report += f" | Tổng Lãi/Lỗ ngày: {daily_pnl:+.2f}$"
            except Exception:
                pass
                
        if pnl_report:
            logging.info(f"{msg} | {pnl_report}")
        else:
            logging.info(msg)
        return

    # 4. Thời gian giá gần đến ngưỡng (Xác suất BUY/SELL >= 80% của Ngưỡng yêu cầu)
    is_close_to_thr = False
    if g_probs and cfg:
        prob_thr = cfg.get("LIVE_BOT", {}).get("MIN_PROBABILITY_THRESH", 0.50)
        near_thr = prob_thr * 0.8
        
        # Kiểm tra xem AI đã chớm "nóng" chưa
        if g_probs.get('buy', 0.0) >= near_thr or g_probs.get('sell', 0.0) >= near_thr:
            is_close_to_thr = True

    if is_close_to_thr:
        logging.info(msg)
        return

    # Bỏ qua lưu file cho tất cả các log lặp lại nhàm chán (Idle Mode)
    pass

print = custom_print

try:
    from src.orchestration.tg_helper import TelegramBot
    with open(os.path.join(safe_script_dir, "tg_config.json"), "r", encoding='utf-8') as f:
        tg_cfg = json.load(f)
    tg_bot = TelegramBot(tg_cfg.get("bot_token", "")) if tg_cfg.get("bot_token") else None
    tg_chat_id = tg_cfg.get("allowed_chat_ids", [])[0] if tg_cfg.get("allowed_chat_ids") else None
except Exception:
    tg_bot, tg_chat_id = None, None

tg_brain_count = 0

def _send_raw_tg(msg):
    if tg_bot and tg_chat_id:
        # Thêm thông tin giá và P/L nếu có
        tm = globals().get('trade_manager')
        report = ""
        if G_CURRENT_PRICE > 0:
            report += f"\n💰 Giá hiện tại: {G_CURRENT_PRICE:,.2f}"
        
        if tm and hasattr(tm, 'get_active_positions_report'):
            pnl_report = tm.get_active_positions_report()
            if pnl_report:
                report += f"\n📊 {pnl_report}"
        
        full_msg = msg + report
        try: tg_bot.send_message(tg_chat_id, full_msg)
        except: pass

def tg_notify(msg):
    """
    Hệ thống thông báo Telegram thông minh - Đã siết chặt theo yêu cầu người dùng.
    Chỉ gửi khi: Khởi động, Chạm ngưỡng (Action != HOLD), hoặc Đang giữ lệnh.
    """
    # 1. Luôn cho phép các thông báo hệ thống quan trọng (Khởi động, Lỗi, Khớp lệnh)
    force_tg_kws = ["KHỞI ĐỘNG", "Khởi động", "ĐÃ BẮN LỆNH", "CHỐT", "ĐẢO CHIỀU", "❌", "⚠️", "✅"]
    if any(k in msg for k in force_tg_kws):
        _send_raw_tg(msg)
        return

    tm = globals().get('trade_manager')
    cfg = globals().get('CONFIG', {})
    
    # 2. Kiểm tra trạng thái vị thế (Đang giữ lệnh)
    has_position = False
    if tm and hasattr(tm, 'active_trade_loggers') and len(tm.active_trade_loggers) > 0:
        has_position = True

    # 3. Kiểm tra xem AI có ra quyết định thực thi không (Chạm ngưỡng)
    # Tín hiệu dự đoán thường có dạng "Hành động: BUY/SELL/HOLD"
    is_signal = False
    if "Hành động: BUY" in msg or "Hành động: SELL" in msg:
        is_signal = True

    # QUY TẮC LỌC:
    # Nếu là tín hiệu thực thi (BUY/SELL) -> Gửi.
    # Nếu đang giữ lệnh -> Gửi (để cập nhật tình hình).
    # Mọi trường hợp khác (HOLD, Idle) -> Bỏ qua.
    if is_signal or has_position:
        _send_raw_tg(msg)
        return
        
    # Chặn đứng các nội dung khác (No Signal, Periodic Heartbeat)
    pass

config_file = os.path.join(safe_script_dir, "workspaces", "CFG_XAU_NY_V3_5", "base_config.json")
if len(sys.argv) > 1:
    args_json = [arg for arg in sys.argv if arg.endswith('.json')]
    if len(args_json) >= 1:
        config_file = args_json[0]

# Khởi tạo Config Loader
config_loader = V3ConfigLoader(config_file, log_callback=print)
CONFIG = config_loader.load_base_config()

TARGET_SYMBOL = CONFIG.get("TARGET_SYMBOL", "XAUUSD")
TARGET_PREFIX = CONFIG.get("TARGET_PREFIX", "XAUUSD")

TRADE_PLATFORM = CONFIG.get("LIVE_BOT", {}).get("TRADE_PLATFORM", "MT5")

if TRADE_PLATFORM == "BINANCE_SPOT":
    trade_manager = BinanceSpotTradeManagerV3(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)
elif TRADE_PLATFORM == "BINANCE":
    trade_manager = BinanceTradeManagerV3(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)
elif TRADE_PLATFORM == "SIMULATED":
    # Paper trading manager — giả lập đầy đủ có vị thế, SL/TP, P&L
    trade_manager = SimulatedTradeManagerV3(
        TARGET_SYMBOL, CONFIG,
        log_callback=print,
        tg_notify_callback=tg_notify,
        get_price_fn=lambda: G_CURRENT_PRICE,
    )
    print(f"[BOT V3] 🎭 Trade Platform: SIMULATED (Paper Trading — có lệnh ảo, SL/TP, P&L thật)")
else:
    trade_manager = V3TradeManager(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)

gui_status = "Đang Sưởi Ấm Radar V3..."
gui_prediction = "Chờ Tín Hiệu..."
gui_probs = {'buy': 0.0, 'sell': 0.0, 'loss': 0.0}
gui_time = "00:00:00"
gui_session = "Phiên: Đang khởi chạy..."
gui_market_data = []
gui_brain_tooltip = "Chưa tải não..."  # Tooltip thành tích đào tạo

def _load_brain_metrics(run_id: str, config_id: str) -> str:
    """Đọc training metrics từ local cache hoặc HF để tạo tooltip."""
    import glob as _glob
    base = os.path.join(safe_script_dir, 'workspaces', 'workspaces', config_id, 'runs', run_id, 'results')
    metric_file = os.path.join(base, 'training_metrics_v3.json')
    
    if not os.path.isfile(metric_file):
        # Thử tải từ HF cache
        cache_base = os.path.expanduser('~/.cache/huggingface/hub/datasets--dung5k--argo_workspaces')
        pattern = os.path.join(cache_base, '**', 'workspaces', config_id, 'runs', run_id, 'results', 'training_metrics_v3.json')
        found = _glob.glob(pattern, recursive=True)
        if found:
            metric_file = found[0]
        else:
            return f"🧠 Não: {run_id}\n📊 Không tìm thấy metrics"
    
    try:
        with open(metric_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sessions = data.get('sessions', {})
        lines = [f"🧠 Não: {run_id}"]
        
        # Thông tin trading platform
        platform = CONFIG.get("LIVE_BOT", {}).get("TRADE_PLATFORM", "?")
        exec_sym = CONFIG.get("EXECUTION_SYMBOL", CONFIG.get("TARGET_SYMBOL", "?"))
        if platform == "BINANCE":
            is_demo = os.getenv("BINANCE_FUTURES_DEMO", "True").lower() == "true"
            lines.append(f"💹 Trade: Binance {'DEMO' if is_demo else 'REAL'} | {exec_sym}")
        elif platform == "BINANCE_SPOT":
            lines.append(f"💹 Trade: Binance Spot | {exec_sym}")
        else:
            mt5_path = CONFIG.get("MT5_PATH", "")
            mt5_name = os.path.basename(os.path.dirname(mt5_path)) if mt5_path else "?"
            lines.append(f"💹 Trade: MT5 {mt5_name} | {exec_sym}")
        lines.append("─" * 28)
        for sess_name, sess_data in sessions.items():
            best = sess_data.get('BEST_VLOSS', {})
            score = best.get('composite_score', 0)
            val_loss = best.get('val_loss', 0)
            epoch = best.get('epoch', 0)
            
            best_wr, best_thr, best_sigs = 0, 0, 0
            for tm in best.get('threshold_metrics', []):
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                if wr > best_wr and sigs >= 10:
                    best_wr = wr
                    best_thr = tm.get('threshold', 0)
                    best_sigs = sigs
            
            lines.append(f"📊 Phiên: {sess_name.upper()}")
            lines.append(f"⭐ Score: {score:.4f}")
            lines.append(f"🎯 WR: {best_wr:.1%} @thr={best_thr:.3f}")
            lines.append(f"📈 Signals: {best_sigs} | Epoch: {epoch}")
            lines.append(f"📉 Val Loss: {val_loss:.4f}")
        return '\n'.join(lines)
    except Exception as e:
        return f"🧠 Não: {run_id}\n❌ Lỗi đọc metrics: {e}"

def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_session, gui_market_data, CONFIG, gui_probs, gui_brain_tooltip
    print("[BOT V3] ===== Khởi động OOP Modules V3.0 (MASTER SCHEDULER) =====")
    
    engine = V3InferenceEngine(log_callback=print)
    mt5_manager = MT5DataManager(log_callback=print, target_sym=TARGET_SYMBOL, config_path=config_file)
    
    if TRADE_PLATFORM in ("BINANCE", "BINANCE_SPOT"):
        trade_manager.init_client()
    else:
        trade_manager.init_mt5()
        
    processor = None
    cloud = None
    
    arch = CONFIG.get("TRAINING", {})
    window_size     = CONFIG.get("FEATURE_ENGINEERING", {}).get("WINDOW_SIZE", 60)
    d_model         = arch.get("D_MODEL", 128)
    nhead           = arch.get("N_HEAD", 8)
    num_attn_layers = arch.get("NUM_LAYERS", 4)
    
    mt5_init_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not os.path.exists(mt5_init_path):
        backup_path = mt5_init_path.replace(r"C:\Program Files", r"D:\mt5").replace("C:\\Program Files", "D:\\mt5")
        if os.path.exists(backup_path): mt5_init_path = backup_path
        
    gui_status = "Đang kết nối MT5 (Dữ liệu)..."
    import MetaTrader5 as mt5
    if not mt5.initialize(path=mt5_init_path):
        gui_status = "❌ Mất Kết Nối MT5 Terminal!"
        print("[BOT V3] ❌ FATAL: Không thể khởi tạo kết nối MT5.")
        return
        
    last_tick_err_time = 0
    brain_loaded = False
    active_run_id = None
    cycle_count = 0
    last_candle_time = None
    
    trade_manager.sync_existing_positions()
    
    # Lấy báo cáo vị thế hiện tại để gửi cùng tin nhắn khởi động
    pos_report = ""
    if hasattr(trade_manager, 'get_active_positions_report'):
        pos_report = trade_manager.get_active_positions_report()
    
    if TRADE_PLATFORM == "BINANCE_SPOT":
        mode_info = "Spot (Giao ngay)"
    elif TRADE_PLATFORM == "BINANCE":
        mode_info = "Futures (Phái sinh)"
    else:
        mode_info = "MT5"
    startup_msg = f"🤖 [BOT V3 MASTER KHỞI ĐỘNG]\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n💹 Mã: {TARGET_SYMBOL} | Chế độ: {mode_info}\nConfig: {os.path.basename(config_file)}"
    if pos_report:
        startup_msg += f"\n\n{pos_report}"
    else:
        startup_msg += "\n\nℹ️ Không có vị thế nào đang mở."
        
    print(startup_msg)
    tg_notify(startup_msg)

    while True:
        cycle_count += 1
        gui_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n[BOT V3] ────── Chu kỳ #{cycle_count} | {gui_time} ──────")
        
        # 1. Hot-reload Config & Schedule
        base_cfg = config_loader.load_base_config()
        if base_cfg:
            CONFIG = base_cfg
            
        sess_name, sinfo, global_mt5 = config_loader.get_current_schedule(CONFIG)
        if sinfo:
            CONFIG = config_loader.apply_schedule_overrides(CONFIG, sinfo, global_mt5)
            
        trade_manager.config = CONFIG
        mt5_manager.config = CONFIG
        trade_manager.update_gui_threshold()
        
        bot_cfg = CONFIG.get("LIVE_BOT", {})
        engine.mse_threshold = bot_cfg.get("MSE_THRESHOLD_PERCENTILE", 70.0)
        engine.prob_threshold = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.70)
            
        target_run_id = CONFIG.get("HF_RUN_ID", "")
        cfg_id = CONFIG.get("CONFIG_ID", "")

        if target_run_id and target_run_id != active_run_id:
            msg = f"🔄 Chuyển đổi Khung Giờ (Phiên {sess_name})!\nĐang tiến hành Hủy Não [{active_run_id}] để tải Não mới [{target_run_id}]..."
            print(f"[BOT V3] {msg}")
            tg_notify(msg)
            brain_loaded = False
            # Re-init cloud to fetch new config specs like DATASET_REPO
            cloud = V3CloudManager(TARGET_SYMBOL, TARGET_PREFIX, "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", CONFIG, log_callback=print)
            
        if not brain_loaded and cloud is not None:
            print(f"[BOT V3] Bắt đầu tải não AAMT...")
            gui_status = "Đang Tải NÃO từ Cloud..."
            try:
                m_path, s_path, i_feats, n_feat = cloud.sync_session_model(cfg_id)
                active_run_id = target_run_id
                
                engine.load_weights(m_path, n_feat, d_model, nhead, num_attn_layers, window_size)
                actual_input_dim = engine.num_features
                
                # Đồng bộ feature list với model weights
                dp_feats = i_feats  # Mặc định dùng feature list từ scaler
                if actual_input_dim != n_feat:
                    print(f"[BOT V3] ⚠️ Model input_dim={actual_input_dim} khác scaler n_feat={n_feat}. Đồng bộ...")
                    dp_feats = list(range(actual_input_dim))
                processor = V3DataProcessor(s_path, dp_feats, window_size, config=CONFIG, log_callback=print)
                # MT5 manager chỉ cần feature names (strings) để cào data, dùng i_feats gốc
                mt5_manager.force_reload_dynamic_features(i_feats)
                
                brain_loaded = True
                gui_status = "✅ Lắp Ráp NÃO V3 Thành Công!"
                
                # Sửa lỗi hiển thị "Unknown" - Fallback về SESSION trong config chính
                display_sess = sess_name if sess_name else CONFIG.get("SESSION", "Unknown")
                gui_session = f"PHIÊN {display_sess.upper()} (Não: {os.path.basename(m_path)[:10]})"
                
                # Tải training metrics cho tooltip
                gui_brain_tooltip = _load_brain_metrics(target_run_id, cfg_id)
                
                msg_done = f"✅ Lắp ráp NÃO V3 Xong!\nKhởi tạo thành công Mạng Nơ-ron (Loss %: {bot_cfg.get('MSE_THRESHOLD_PERCENTILE', 70)})\nBot đang nghe ngóng thị trường..."
                print(f"[BOT V3] {msg_done}")
                tg_notify(msg_done)
            except Exception as ce:
                gui_status = f"❌ Lỗi Thay Não: {str(ce)[:30]}"
                print(f"[BOT V3] ❌ Lỗi tải não: {ce}")
                time.sleep(5)
                continue
                
        if not brain_loaded:
            print("[BOT V3] Chưa có Bộ Não nào được cấu hình hợ lệ. Đợi 5s...")
            time.sleep(5)
            continue
            
        print("[BOT V3] Quét các cổng MT5...")
        mt5_manager.scan_terminals_and_map()
        
        trading_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if mt5_manager.current_connected_path != trading_path:
            mt5.shutdown()
            mt5.initialize(path=trading_path)
            mt5_manager.current_connected_path = trading_path

        mt5_exec_sym = CONFIG.get("EXECUTION_SYMBOL", TARGET_SYMBOL)
        actual_sym = mt5_manager.IN_MEMORY_SYMBOL_HINT.get(mt5_exec_sym, mt5_exec_sym)
        
        global G_CURRENT_PRICE
        is_crypto = CONFIG.get("FEATURE_ENGINEERING", {}).get("CRYPTO_MODE", False)
        if TRADE_PLATFORM in ("BINANCE", "BINANCE_SPOT", "SIMULATED") and is_crypto:
            try:
                import ccxt
                if not hasattr(bot_background_loop, '_sim_exchange'):
                    bot_background_loop._sim_exchange = ccxt.binance()
                ex = bot_background_loop._sim_exchange
                if hasattr(trade_manager, 'exchange') and trade_manager.exchange:
                    ex = trade_manager.exchange
                fmt_sym = TARGET_SYMBOL.replace("USDT", "/USDT")
                ticker = ex.fetch_ticker(fmt_sym)
                G_CURRENT_PRICE = ticker.get('last', 0)
                staleness_secs = 0
            except Exception as e:
                if time.time() - last_tick_err_time > 10:
                    print(f"[BOT V3] ⚠️ LỖI TICK BINANCE: {e}")
                    last_tick_err_time = time.time()
                time.sleep(1)
                continue
        else:
            mt5.symbol_select(actual_sym, True)
            tick = mt5.symbol_info_tick(actual_sym)
            if tick is None:
                if time.time() - last_tick_err_time > 10:
                    print(f"[BOT V3] ⚠️ LỖI TICK: {actual_sym} = None! Reconnect...")
                    last_tick_err_time = time.time()
                mt5_manager.current_connected_path = None
                time.sleep(1)
                continue
            G_CURRENT_PRICE = tick.bid if tick.bid > 0 else tick.last
            staleness_secs = time.time() - tick.time
            
        if staleness_secs > 300:
            gui_status = f"Giá Freeze ({int(staleness_secs/60)}p)..."
            time.sleep(10)
            continue
            
        current_candle_time = int(time.time() // 60) * 60
        if current_candle_time == last_candle_time:
            time.sleep(1)
            continue
            
        last_candle_time = current_candle_time
        print(f"[BOT V3] 🕒 Nến M1 Mới | {datetime.fromtimestamp(current_candle_time, timezone.utc).strftime('%H:%M')} UTC")

        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
        merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=1500)
        mt5_manager.current_connected_path = None
        
        if err_msg or merged_df is None or len(merged_df) == 0:
            gui_status = err_msg or "Dữ liệu rỗng"
            time.sleep(2)
            continue
            
        gui_market_data = sorted(sym_data, key=lambda x: x[0])
        gui_status = "Chạy Pipeline Giải thuật V3..."
        
        t_seq, p_err = processor.ingest_and_scale(merged_df)
        if p_err:
            gui_status = f"Pipeline Từ Chối: {p_err[:40]}"
            time.sleep(2)
            continue
            
        gui_status = "Đang Trích Xuất Phân Rã Không Gian V3..."
        action, mse, probs = engine.predict(t_seq)
        if action is None:
            gui_status = "Động Cơ AI Sập"
            time.sleep(2)
            continue
            
        gui_prediction = f"B:{probs['buy']:.2f} S:{probs['sell']:.2f} (Loss:{mse:.3f})"
        gui_probs = {'buy': probs['buy'], 'sell': probs['sell'], 'loss': mse}

        # Tính hành động hiển thị thực tế (có xét vị thế đang giữ)
        display_action = action
        if hasattr(trade_manager, 'active_trade_loggers') and trade_manager.active_trade_loggers:
            for ticket, pos in trade_manager.active_trade_loggers.items():
                side = pos.get('side', '')
                if (side == 'SELL' and action == 'SELL') or (side == 'BUY' and action == 'BUY'):
                    display_action = f"GIỮ LỆNH {side} (#{ticket})"
                    break

        msg_pred = (
            f"🎯 ĐÃ KẾT THÚC PIPELINE DỰ ĐOÁN:\n"
            f"Thời gian: Nến {gui_time}\n"
            f"Giá trị Loss hiện tại: {mse:.4f} (Threshold: {engine.mse_threshold:.4f})\n"
            f"Tỷ lệ Cược: BUY={probs['buy']:.2%} | SELL={probs['sell']:.2%}\n"
            f"Hành động: {display_action}"
        )

        # Nối thông tin vị thế + P&L ngày (nếu trade_manager hỗ trợ)
        if hasattr(trade_manager, 'get_active_positions_report'):
            pos_rpt = trade_manager.get_active_positions_report()
            if pos_rpt:
                msg_pred += f"\n{pos_rpt}"
        if hasattr(trade_manager, 'get_daily_pnl_summary'):
            msg_pred += f"\n{trade_manager.get_daily_pnl_summary()}"

        print(f"[BOT V3] {msg_pred}")
        # Gửi output hiện tại của mô hình qua Telegram (theo yêu cầu của user)
        # Để tránh spam, tg_notify đã được cấu hình chỉ gửi tin quan trọng
        tg_notify(msg_pred)
        
        trading_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if mt5_manager.current_connected_path != trading_path:
            mt5.shutdown()
            mt5.initialize(path=trading_path)
            mt5_manager.current_connected_path = trading_path
            
        trade_manager.execute_trade(action, probs, mse, actual_target_sym=actual_sym)
        gui_status = f"Khóa Mốc. Hành động: {action}"
        time.sleep(1)

def update_ui(root, lbl_time, lbl_session, canvas_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target=None):
    if lbl_target: lbl_target.config(text=TARGET_SYMBOL)
    lbl_time.config(text=f"🕒 {gui_time}")
    lbl_session.config(text=f"🌐 {gui_session}")
    lbl_action.config(text=f"🎯 Chiến thuật: {trade_manager.gui_action}")
    lbl_status.config(text=f"⚙️ {gui_status}")
    lbl_thr.config(text=trade_manager.gui_thr_text)
    
    for item in tree.get_children():
        tree.delete(item)
    for sym, price, change, t_str, source_name, is_delayed in gui_market_data:
        change_text = f"🟢 {change:+.2f}" if change >= 0 else f"🔴 {change:+.2f}"
        color = "delayed" if is_delayed else "normal"
        tree.insert("", "end", values=(sym, f"{price:,.2f}", change_text, t_str), tags=(color,))
        
    tree.tag_configure("normal", foreground="white")
    tree.tag_configure("delayed", foreground="#ffaa00")
    
    canvas_pred.delete("all")
    w = canvas_pred.winfo_width()
    if w < 10: w = 330
    
    # Lấy ngưỡng vào hiện tại
    prob_thr = CONFIG.get("LIVE_BOT", {}).get("MIN_PROBABILITY_THRESH", 0.50)
    
    # Lấy độ tin cậy
    buy_p = gui_probs.get('buy', 0.0)
    sell_p = gui_probs.get('sell', 0.0)
    
    bw = int(w * buy_p)
    sw = int(w * sell_p)
    
    # Màu sắc thay đổi nếu vượt ngưỡng
    buy_color = "#00ff77" if buy_p >= prob_thr else "#007733"
    sell_color = "#ff3333" if sell_p >= prob_thr else "#882222"
    
    # Vẽ thanh
    canvas_pred.create_rectangle(0, 0, bw, 24, fill=buy_color, outline="")
    canvas_pred.create_rectangle(w - sw, 0, w, 24, fill=sell_color, outline="")
    
    # Vẽ Vạch Ngưỡng (Threshold Lines)
    buy_thr_x = int(w * prob_thr)
    sell_thr_x = int(w - w * prob_thr)
    
    # Vẽ 2 vạch kẻ dọc đứt nét
    canvas_pred.create_line(buy_thr_x, 0, buy_thr_x, 24, fill="#ffcc00", dash=(2, 2))
    canvas_pred.create_line(sell_thr_x, 0, sell_thr_x, 24, fill="#ffcc00", dash=(2, 2))
    
    txt = f"BUY {buy_p:.1%} | SELL {sell_p:.1%}"
    if buy_p == 0.0 and sell_p == 0.0:
        txt = "Chờ Tín Hiệu..."
    canvas_pred.create_text(w/2, 12, text=txt, fill="white", font=("Consolas", 10, "bold"))
    
    root.after(500, update_ui, root, lbl_time, lbl_session, canvas_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target)

class ToolTip:
    """Tooltip nhỏ gọn cho tkinter widget — hiển thị khi di chuột qua."""
    def __init__(self, widget, text_func):
        self.widget = widget
        self.text_func = text_func  # Callable trả về text động
        self.tipwindow = None
        widget.bind('<Enter>', self.show)
        widget.bind('<Leave>', self.hide)

    def show(self, event=None):
        if self.tipwindow:
            return
        text = self.text_func() if callable(self.text_func) else str(self.text_func)
        if not text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.attributes('-topmost', True)
        tw.wm_geometry(f"+{x}+{y}")
        
        frame = tk.Frame(tw, bg='#1a1a2e', bd=1, relief=tk.SOLID, highlightbackground='#00ffff', highlightthickness=1)
        frame.pack()
        label = tk.Label(frame, text=text, justify=tk.LEFT, bg='#1a1a2e', fg='#e0e0e0',
                         font=('Consolas', 9), padx=8, pady=6)
        label.pack()

    def hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

def start_overlay_dashboard():
    root = tk.Tk()
    root.title(f"AAMT TERMINATOR V3 - {TARGET_SYMBOL}")
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.92) 
    
    screen_h = root.winfo_screenheight()
    root.geometry(f"360x450+10+{screen_h - 500}")
    root.configure(bg='#080b12') 
    
    root.x, root.y = 0, 0
    def do_move(event):
        if root.x is None or root.y is None: return
        root.geometry(f"+{root.winfo_x() + event.x - root.x}+{root.winfo_y() + event.y - root.y}")
        
    root.bind("<ButtonPress-1>", lambda e: setattr(root, 'x', e.x) or setattr(root, 'y', e.y))
    root.bind("<ButtonRelease-1>", lambda e: setattr(root, 'x', None) or setattr(root, 'y', None))
    root.bind("<B1-Motion>", do_move)
    
    tk.Label(root, text=f"🌌 {TARGET_SYMBOL} MASTER V3 🌌", fg="#00ffff", bg="#080b12", font=("Consolas", 11, "bold")).pack(pady=5)
    lbl_session = tk.Label(root, text="🌐 Phiên: Đang khởi chạy", fg="#aa66ff", bg="#080b12", font=("Consolas", 9), cursor="hand2")
    lbl_session.pack()
    # Tooltip thành tích đào tạo — hiển thị khi di chuột qua tên não
    ToolTip(lbl_session, lambda: gui_brain_tooltip)
    canvas_pred = tk.Canvas(root, height=24, bg="#1a2235", highlightthickness=0)
    canvas_pred.pack(pady=3, fill=tk.X, padx=15)
    lbl_action = tk.Label(root, text="🎯 Chiến thuật: Đang ngủ", fg="#ffcc00", bg="#080b12", font=("Consolas", 9))
    lbl_action.pack()
    lbl_thr = tk.Label(root, text="⚖️ Ngưỡng L4: Chờ Load", fg="#ff55bb", bg="#080b12", font=("Consolas", 9))
    lbl_thr.pack()
    
    from tkinter import ttk
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#111625", foreground="white", fieldbackground="#111625", borderwidth=0)
    style.configure("Treeview.Heading", background="#1a2235", foreground="#00ffff", font=("Consolas", 8, "bold"))
    
    def toggle_board():
        if frame_data.winfo_ismapped():
            frame_data.pack_forget()
            btn_toggle.config(text="⬇ Mở Rộng Bảng Giá")
        else:
            frame_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            btn_toggle.config(text="⬆ Thu Gọn Bảng Giá")
            
    btn_toggle = tk.Button(root, text="⬆ Thu Gọn Bảng Giá", command=toggle_board, bg="#1a2235", fg="#00ffff", relief=tk.FLAT, font=("Consolas", 8, "bold"))
    btn_toggle.pack(pady=2)

    frame_data = tk.Frame(root, bg="#080b12")
    frame_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    tree = ttk.Treeview(frame_data, columns=("Symbol", "Price", "Change", "Time"), show="headings", height=8)
    tree.heading("Symbol", text="Mã")
    tree.heading("Price", text="Giá")
    tree.heading("Change", text="Biến Động")
    tree.heading("Time", text="Giờ")
    for c, w in zip(("Symbol", "Price", "Change", "Time"), (80, 65, 65, 60)): tree.column(c, width=w, anchor="e" if c != "Symbol" else "w")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    lbl_status = tk.Label(root, text="⚙️ Đang Khởi Đoạt Mạng", fg="#aaaaaa", bg="#080b12", font=("Consolas", 8))
    lbl_status.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
    lbl_time = tk.Label(root, text="🕒 00:00:00", fg="#888888", bg="#080b12", font=("Consolas", 8))
    lbl_time.pack(side=tk.BOTTOM)
    
    update_ui(root, lbl_time, lbl_session, canvas_pred, lbl_action, lbl_status, tree, lbl_thr)
    root.mainloop()

if __name__ == "__main__":
    t = threading.Thread(target=bot_background_loop)
    t.daemon = True
    t.start()
    start_overlay_dashboard()
