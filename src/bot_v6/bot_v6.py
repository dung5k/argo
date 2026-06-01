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
from src.bot_v6.data_processor_v6 import V6DataProcessor
from src.bot_v6.inference_engine_v6 import V6InferenceEngine
from src.bot_v3.trade_manager_v3 import V3TradeManager
from src.bot_v3.binance_trade_manager_v3 import BinanceTradeManagerV3
from src.bot_v3.binance_spot_trade_manager_v3 import BinanceSpotTradeManagerV3
from src.bot_v3.virtual_trade_manager_v3 import V3VirtualTradeManager
from src.bot_v3.config_loader_v3 import V3ConfigLoader
from src.core.mt5_data_manager import MT5DataManager
import logging

log_dir = os.path.join(safe_script_dir, "workspaces", "shared_meta", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"trade_bot_v6_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log")
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
                if any('bot_v6.py' in arg for arg in cmdline) and any(target_config in arg for arg in cmdline):
                    print(f"[PROCESS] ⚠️ Đang KILL tiến trình cũ PID {old_pid} ({target_config})")
                    
                    # Kill parent cmd.exe to prevent hanging console window from 'pause'
                    try:
                        parent = proc.parent()
                        if parent and parent.name().lower() in ['cmd.exe', 'powershell.exe', 'conhost.exe']:
                            print(f"[PROCESS] ⚠️ Đang KILL Parent Console {parent.name()} (PID: {parent.pid})")
                            parent.kill()
                    except Exception as pe:
                        print(f"[PROCESS] ⚠️ Lỗi kill parent: {pe}")
                        
                    try:
                        proc.kill()
                    except psutil.NoSuchProcess:
                        pass
                        
                    print(f"[PROCESS] ✅ Đã dọn dẹp tiến trình cũ xong.")
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
    force_print_kws = ["❌", "⚠️", "✅", "FATAL", "Exception", "Lỗi", "ĐÃ BẮN LỆNH", "CHỐT", "ĐẢO CHIỀU", "Bắt đầu Pipeline", "Kêt quả | Hành động", "Binance", "TradeManager", "🟢", "🔴", "📂"]
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
    tg_cfg = {}
    try:
        with open(os.path.join(safe_script_dir, "tg_config.json"), "r", encoding='utf-8') as f:
            tg_cfg = json.load(f)
    except:
        pass
        
    try:
        vscode_path = os.path.join(safe_script_dir, ".vscode", "settings.json")
        if os.path.exists(vscode_path):
            with open(vscode_path, "r", encoding='utf-8') as f:
                vsc = json.load(f)
            vsc_token = vsc.get("antigravityBridge.teleBotToken")
            if vsc_token:
                tg_cfg["bot_token"] = vsc_token
            vsc_chat = vsc.get("antigravityBridge.whitelistChatIds")
            if vsc_chat:
                tg_cfg["allowed_chat_ids"] = [int(x.strip()) if x.strip().isdigit() else x.strip() for x in vsc_chat.split(",")]
    except Exception:
        pass
        
    tg_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or tg_cfg.get("bot_token", "")
    tg_bot = TelegramBot(tg_bot_token) if tg_bot_token else None
    
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if tg_chat_id:
        tg_chat_id = int(tg_chat_id)
    else:
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
            
        prefix = f"[{TARGET_SYMBOL}] "
        brain_id = globals().get('CONFIG', {}).get("brain_id", "")
        brain_str = f" [Não: {brain_id}]" if brain_id else ""
        clean_msg = msg.replace(prefix, "").replace(f"[{TARGET_SYMBOL}]", "").strip()
        full_msg = f"[{TARGET_SYMBOL}]{brain_str} " + clean_msg + report
        try: tg_bot.send_message(tg_chat_id, full_msg)
        except: pass

def tg_notify(msg):
    _send_raw_tg(msg)

def log_tele(*args):
    msg = " ".join(map(str, args))
    _send_raw_tg(msg)

config_file = os.path.join(safe_script_dir, "workspaces", "CFG_XAU_NY_V3_5", "base_config.json")
schedule_file = None
if len(sys.argv) > 1:
    args_json = [arg for arg in sys.argv if arg.endswith('.json')]
    if len(args_json) >= 1:
        config_file = args_json[0]
    if len(args_json) >= 2:
        schedule_file = args_json[1]

# Khởi tạo Config Loader
config_loader = V3ConfigLoader(config_file, schedule_config_path=schedule_file, log_callback=print)
CONFIG = config_loader.load_base_config()

TARGET_SYMBOL = CONFIG.get("TARGET_SYMBOL", "XAUUSD")
TARGET_PREFIX = CONFIG.get("TARGET_PREFIX", "XAUUSD")

TRADE_PLATFORM = CONFIG.get("LIVE_BOT", {}).get("TRADE_PLATFORM", "MT5")

if CONFIG.get("LIVE_BOT", {}).get("PAPER_TRADE", False):
    trade_manager = V3VirtualTradeManager(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)
elif TRADE_PLATFORM == "BINANCE_SPOT":
    trade_manager = BinanceSpotTradeManagerV3(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)
elif TRADE_PLATFORM == "BINANCE":
    trade_manager = BinanceTradeManagerV3(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)
elif TRADE_PLATFORM == "SIMULATED":
    # Dummy trade manager cho chế độ mô phỏng — chỉ log, không giao dịch thật
    class _SimulatedTM:
        def __init__(self):
            self.gui_action = "🎭 SIMULATED"
            self.gui_thr_text = "SIM"
            self.exchange = None
        def init_mt5(self): pass
        def init_client(self): pass
        def execute_trade(self, *a, **kw): print("[SIMULATED] Signal received — no real trade executed.")
        def check_positions(self, *a, **kw): return []
        def manage_positions(self, *a, **kw): pass
        def early_reversal_check(self, *a, **kw): pass
        def trailing_sl(self, *a, **kw): pass
        def sync_existing_positions(self): pass
        def update_gui_threshold(self): pass
        def get_active_positions_report(self): return "Mô phỏng (SIMULATED): Đang theo dõi, không trade thật."
    trade_manager = _SimulatedTM()
    print(f"[BOT V6] 🎭 Trade Platform: SIMULATED (chỉ giám sát, không giao dịch)")
else:
    trade_manager = V3TradeManager(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)

gui_status = "Đang Sưởi Ấm Radar V6..."
gui_prediction = "Chờ Tín Hiệu..."
gui_probs = {'buy': 0.0, 'sell': 0.0, 'loss': 0.0}
gui_time = "00:00:00"
gui_session = "Phiên: Đang khởi chạy..."
gui_market_data = []
gui_brain_tooltip = "Chưa tải não..."  # Tooltip thành tích đào tạo

def _load_brain_metrics(run_id: str, config_id: str, is_active: bool = False) -> tuple:
    """Đọc training metrics từ local cache hoặc HF để tạo tooltip."""
    import glob as _glob
    import os, json
    base = os.path.join(safe_script_dir, 'workspaces', config_id, 'runs', run_id, 'results')
    metric_file = os.path.join(base, 'training_metrics_v3.json')
    
    status_icon = "🟢 ACTIVE" if is_active else "⚪ QUEUE"
    header = f"{status_icon} | 🧠 {run_id}"
    
    if not os.path.isfile(metric_file):
        cache_base = os.path.expanduser('~/.cache/huggingface/hub/datasets--dung5k--argo_workspaces')
        pattern = os.path.join(cache_base, '**', 'workspaces', config_id, 'runs', run_id, 'results', 'training_metrics_v3.json')
        found = _glob.glob(pattern, recursive=True)
        if found:
            metric_file = found[0]
        else:
            return f"{header}\n📊 Không tìm thấy metrics", 0.7
            
    try:
        with open(metric_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sessions = data.get('sessions', {})
        lines = [header]
        
        platform = CONFIG.get("LIVE_BOT", {}).get("TRADE_PLATFORM", "?")
        exec_sym = CONFIG.get("EXECUTION_SYMBOL", CONFIG.get("TARGET_SYMBOL", "?"))
        lines.append(f"💹 {platform} | {exec_sym}")
        lines.append("─" * 32)
        
        fe_cfg = CONFIG.get("FEATURE_ENGINEERING", {})
        tp_pct = fe_cfg.get("TP_PCT", 0)
        sl_pct = fe_cfg.get("SL_PCT", 0)
        be_pct = 0.0
        if tp_pct > 0 and sl_pct > 0:
            be_pct = sl_pct / (tp_pct + sl_pct) * 100
        else:
            bot_cfg = CONFIG.get("LIVE_BOT", {})
            tp_pts = bot_cfg.get("TAKE_PROFIT_POINTS", 0)
            sl_pts = bot_cfg.get("STOP_LOSS_POINTS", 0)
            if tp_pts > 0 and sl_pts > 0:
                be_pct = sl_pts / (tp_pts + sl_pts) * 100

        best_thr_overall = 0.7
        for sess_name, sess_data in sessions.items():
            best = sess_data.get('BEST_VLOSS', {})
            score = best.get('composite_score', 0)
            epoch = best.get('epoch', 0)
            lines.append(f"📅 PHIÊN: {sess_name.upper()}")
            lines.append(f"⭐ Score: {score:.4f} | Epoch: {epoch}")
            lines.append("─" * 15)
            
            best_wr, best_sigs = 0, 0
            for tm in best.get('threshold_metrics', []):
                thr = tm.get('threshold', 0)
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                tus = tm.get('tus_score', 0)
                b = tm.get('total_buy', sigs // 2)
                s = tm.get('total_sell', sigs - b)
                avg = sigs / 30.0 if sigs > 0 else 0
                lines.append(f"🎯 Thr: {thr:.3f} | WR: {wr*100:.1f}% (Hòa Vốn {be_pct:.1f}%) | ({b}B/{s}S)")
                lines.append(f"   Avg: {avg:.1f}/ngày | TUS: {tus:.2f}")
                
                if wr >= best_wr and sigs >= 1:
                    best_wr = wr
                    best_thr_overall = thr
            lines.append("─" * 15)
        
        report = "\n".join(lines)
        return report, best_thr_overall
    except Exception as e:
        return f"{header}\n❌ Lỗi đọc metrics: {e}", 0.7

def _get_all_brains_report() -> str:
    """Tổng hợp báo cáo toàn bộ các bộ não trong lịch trình."""
    global CONFIG
    schedule = []
    if config_loader.schedule_config_path and os.path.exists(config_loader.schedule_config_path):
        try:
            with open(config_loader.schedule_config_path, "r", encoding="utf-8-sig") as f:
                sched_data = json.load(f)
                sched = sched_data.get("schedule", sched_data.get("SCHEDULE", {}))
                for s_name, sinfo in sched.items():
                    schedule.append((s_name, sinfo.get("run_id"), sinfo.get("config_id")))
        except: pass
    if not schedule:
        schedule = [("Default", CONFIG.get("HF_RUN_ID"), CONFIG.get("CONFIG_ID"))]

    active_run = CONFIG.get("HF_RUN_ID", "")
    reports = []
    for s_name, r_id, c_id in schedule:
        is_active = (r_id == active_run)
        report_text, _ = _load_brain_metrics(r_id, c_id, is_active)
        reports.append(report_text)
        reports.append("\n" + "="*20 + "\n")
    return "\n".join(reports)

def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_session, gui_market_data, CONFIG, gui_probs, gui_brain_tooltip
    print("[BOT V6] ===== Khởi động OOP Modules V6.0 (DUAL-ENCODER MASTER) =====")
    
    DISABLE_MT5 = (TARGET_SYMBOL in ("LTCUSDT", "LTCUSDm"))
    engine = V6InferenceEngine(log_callback=print)
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
        
    import MetaTrader5 as mt5
    if not DISABLE_MT5:
        gui_status = "Đang kết nối MT5 (Dữ liệu)..."
        if not mt5.initialize(path=mt5_init_path, timeout=5000):
            gui_status = "❌ Lỗi kết nối MT5 Terminal!"
            print("[BOT V6] ⚠️ Cảnh báo: Không thể khởi tạo kết nối MT5 Terminal. Sẽ chạy dựa trên Binance/Local.")
    else:
        gui_status = "Đang kết nối Binance (Không dùng MT5)..."
        
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
        print(f"\n[BOT V6] ────── Chu kỳ #{cycle_count} | {gui_time} ──────")
        
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
            print(f"[BOT V6] {msg}")
            tg_notify(msg)
            brain_loaded = False
            # Re-init cloud to fetch new config specs like DATASET_REPO
            cloud = V3CloudManager(TARGET_SYMBOL, TARGET_PREFIX, "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", CONFIG, log_callback=print)
            
        if not brain_loaded and cloud is not None:
            print(f"[BOT V6] Bắt đầu tải não AAMT...")
            gui_status = "Đang Tải NÃO từ Cloud..."
            try:
                m_path, s_path, i_feats, n_feat = cloud.sync_session_model(cfg_id)
                active_run_id = target_run_id
                
                # Auto-sync CONFIG with the original training config.json
                run_config_path = os.path.join(safe_script_dir, "workspaces", cfg_id, "runs", active_run_id, "config.json")
                if not os.path.exists(run_config_path):
                    run_config_path = os.path.join(os.path.dirname(os.path.dirname(m_path)), "config.json")
                if not os.path.exists(run_config_path):
                    run_config_path = os.path.join(os.path.dirname(m_path), "config.json")
                    
                if os.path.exists(run_config_path):
                    print(f"[BOT V6] 📂 Tải cấu hình huấn luyện gốc config.json từ: {run_config_path}")
                    with open(run_config_path, "r", encoding="utf-8") as rf:
                        orig_config = json.load(rf)
                    if "FEATURE_ENGINEERING" in orig_config:
                        CONFIG["FEATURE_ENGINEERING"] = orig_config["FEATURE_ENGINEERING"]
                        print("[BOT V6] ✅ Đồng bộ thành công FEATURE_ENGINEERING từ config gốc.")
                    if "TRAINING" in orig_config:
                        CONFIG["TRAINING"] = orig_config["TRAINING"]
                        print("[BOT V6] ✅ Đồng bộ thành công TRAINING từ config gốc.")
                else:
                    print(f"[BOT V6] ❌ KHÔNG TÌM THẤY config.json gốc tại {os.path.dirname(os.path.dirname(m_path))}! Bot có thể hoạt động sai lệch!")
                
                t_cfg = CONFIG.get("TRAINING", {})
                fe_cfg = CONFIG.get("FEATURE_ENGINEERING", {})
                mtf_inputs = fe_cfg.get("MTF_INPUTS", [])
                input_dims = []
                seq_lens = []
                for tf_cfg in mtf_inputs:
                    input_dims.append(len(tf_cfg.get("FEATURES", [])))
                    seq_lens.append(tf_cfg.get("WINDOW_SIZE", 60))
                
                engine.load_weights(
                    model_path=m_path,
                    input_dims=input_dims,
                    seq_lens=seq_lens,
                    d_model=t_cfg.get("D_MODEL", 128),
                    nhead=t_cfg.get("N_HEAD", 8),
                    num_attn_layers=t_cfg.get("NUM_LAYERS", 4),
                    pooling=t_cfg.get("POOLING", "mean"),
                    cls_head=t_cfg.get("CLS_HEAD", "simple")
                )
                actual_input_dim = engine.model.encoders[0].input_projection.weight.shape[1] if engine.model else n_feat
                
                # Đồng bộ feature list với model weights
                dp_feats = i_feats  # Mặc định dùng feature list từ scaler
                
                processor = V6DataProcessor(s_path, config=CONFIG, log_callback=print)
                processor._init_engines() # MUST CALL THIS to load column_orders
                # V6 MT5 manager needs ALL features across all MTF
                all_feats = []
                for co in processor.column_orders:
                    all_feats.extend(co)
                    
                # Force MT5DataManager to fetch all MTF symbols by injecting dummy features
                for mtf_cfg in CONFIG.get('FEATURE_ENGINEERING', {}).get('MTF_INPUTS', []):
                    sym = mtf_cfg.get('SYMBOL')
                    if sym:
                        all_feats.append(f"{sym}_dummy")
                        
                mt5_manager.force_reload_dynamic_features(list(set(all_feats)))
                
                brain_loaded = True
                gui_status = "✅ Lắp Ráp NÃO V6 Thành Công!"
                
                # Sửa lỗi hiển thị "Unknown" - Fallback về SESSION trong config chính
                display_sess = sess_name if sess_name else CONFIG.get("SESSION", "Unknown")
                gui_session = f"PHIÊN {display_sess.upper()} (Não: {os.path.basename(m_path)})"
                
                # Tải training metrics cho tooltip toàn diện
                gui_brain_tooltip = _get_all_brains_report()
                _, best_thr = _load_brain_metrics(target_run_id, cfg_id, True)
                
                # Ưu tiên sử dụng ngưỡng được cấu hình thủ công trong LIVE_BOT hoặc Schedule
                manual_thr = bot_cfg.get("MIN_PROBABILITY_THRESH")
                if manual_thr is not None:
                    engine.prob_threshold = manual_thr
                elif best_thr > 0:
                    engine.prob_threshold = best_thr
                print(f"[BOT V6] Đã cài đặt prob_threshold = {engine.prob_threshold}")
                
                msg_done = f"✅ Lắp ráp NÃO V6 Xong!\n{gui_brain_tooltip}\n\nNgưỡng Loss an toàn: {bot_cfg.get('MSE_THRESHOLD_PERCENTILE', 70)}%\nBot đang nghe ngóng thị trường..."
                print(f"[BOT V6] {msg_done}")
                tg_notify(msg_done)
            except Exception as ce:
                gui_status = f"❌ Lỗi Thay Não: {str(ce)[:30]}"
                print(f"[BOT V6] ❌ Lỗi tải não: {ce}")
                time.sleep(60)  # Tăng lên 60s để tránh spam log liên tục khi não chưa sẵn sàng
                continue
                
        if not brain_loaded:
            print("[BOT V6] Chưa có Bộ Não nào được cấu hình hợ lệ. Đợi 5s...")
            time.sleep(5)
            continue
            
        print("[BOT V6] Quét các cổng MT5...")
        mt5_manager.scan_terminals_and_map()
        
        trading_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if not os.path.exists(trading_path):
            backup_path = trading_path.replace(r"C:\Program Files", r"D:\mt5").replace("C:\\Program Files", "D:\\mt5")
            if os.path.exists(backup_path): trading_path = backup_path
            
        if not DISABLE_MT5 and mt5_manager.current_connected_path != trading_path:
            mt5.shutdown()
            mt5.initialize(path=trading_path)
            mt5_manager.current_connected_path = trading_path

        mt5_exec_sym = CONFIG.get("EXECUTION_SYMBOL", TARGET_SYMBOL)
        actual_sym = mt5_manager.IN_MEMORY_SYMBOL_HINT.get(mt5_exec_sym, mt5_exec_sym)
        
        global G_CURRENT_PRICE
        current_bid = G_CURRENT_PRICE
        current_ask = G_CURRENT_PRICE
        current_point = 0.01

        if TRADE_PLATFORM in ("BINANCE", "BINANCE_SPOT"):
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
                current_bid = ticker.get('bid', G_CURRENT_PRICE)
                current_ask = ticker.get('ask', G_CURRENT_PRICE)
                staleness_secs = 0
            except Exception as e:
                if time.time() - last_tick_err_time > 10:
                    print(f"[BOT V6] ⚠️ LỖI TICK BINANCE: {e}")
                    last_tick_err_time = time.time()
                time.sleep(1)
                continue
        else:
            mt5.symbol_select(actual_sym, True)
            tick = mt5.symbol_info_tick(actual_sym)
            if tick is None:
                if time.time() - last_tick_err_time > 10:
                    print(f"[BOT V6] ⚠️ LỖI TICK: {actual_sym} = None! Reconnect...")
                    last_tick_err_time = time.time()
                mt5_manager.current_connected_path = None
                time.sleep(1)
                continue
            G_CURRENT_PRICE = tick.bid if tick.bid > 0 else tick.last
            current_bid = tick.bid
            current_ask = tick.ask
            p_info = mt5.symbol_info(actual_sym)
            if p_info:
                current_point = p_info.point
            staleness_secs = time.time() - tick.time
            
        if isinstance(trade_manager, V3VirtualTradeManager):
            trade_manager.update_virtual_positions(current_bid, current_ask, current_point)
            
        if staleness_secs > 300:
            gui_status = f"Giá Freeze ({int(staleness_secs/60)}p)..."
            time.sleep(10)
            continue
            
        base_tf_str = "1m"
        mtf_inputs = CONFIG.get('FEATURE_ENGINEERING', {}).get('MTF_INPUTS', [])
        if mtf_inputs:
            base_tf_str = mtf_inputs[0].get("TIMEFRAME", "1m")
            
        tf_secs_map = {'1m': 60, '1min': 60, '5m': 300, '5min': 300, '15m': 900, '15min': 900, '30m': 1800, '30min': 1800, '1h': 3600, '1H': 3600, '4h': 14400, '4H': 14400}
        interval_seconds = tf_secs_map.get(base_tf_str, 60)

        current_candle_time = int(time.time() // interval_seconds) * interval_seconds
        if current_candle_time == last_candle_time:
            time.sleep(1)
            continue
            
        last_candle_time = current_candle_time
        print(f"[BOT V6] 🕒 Nến {base_tf_str} Mới | {datetime.fromtimestamp(current_candle_time, timezone.utc).strftime('%H:%M')} UTC")

        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
        
        max_minutes_needed = 2880 # default 2 days
        for mtf in mtf_inputs:
            tf_str = mtf.get("TIMEFRAME", "1m")
            w_size = mtf.get("WINDOW_SIZE", 60)
            tf_secs = tf_secs_map.get(tf_str, 60)
            mins_needed = int((tf_secs / 60) * w_size * 2.0) # 2.0x safety margin to ensure enough candles after resampling
            if mins_needed > max_minutes_needed:
                max_minutes_needed = mins_needed
                
        merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=max_minutes_needed)
        mt5_manager.current_connected_path = None
        
        if err_msg or merged_df is None or len(merged_df) == 0:
            gui_status = err_msg or "Dữ liệu rỗng"
            time.sleep(2)
            continue
            
        gui_market_data = sorted(sym_data, key=lambda x: x[0])
        gui_status = "Chạy Pipeline Giải thuật V6..."
        
        try:
            ok, X_list = processor.process_online([merged_df] * len(processor.tf_configs))
            if not ok or X_list is None:
                gui_status = f"Pipeline Từ Chối Dữ Liệu"
                time.sleep(2)
                continue
        except Exception as pe:
            print(f"[BOT V6] ❌ Lỗi chạy pipeline V6: {pe}")
            gui_status = f"Pipeline Từ Chối Dữ Liệu"
            time.sleep(2)
            continue
            
        gui_status = "Đang Trích Xuất Không Gian V6 MTF..."
        try:
            probs_tuple = engine.predict_probs(X_list)
            if probs_tuple is None:
                gui_status = "Động Cơ AI Sập"
                time.sleep(2)
                continue
            p_sell, p_hold, p_buy = probs_tuple
            
            action = 1
            if p_buy >= engine.prob_threshold:
                action = 2
            elif p_sell >= engine.prob_threshold:
                action = 0
                
            prediction = {
                'action': action,
                'mse': 0.0,
                'raw': [p_sell, p_hold, p_buy]
            }
        except Exception as pe:
            print(f"[BOT V6] ❌ Lỗi dự báo AI: {pe}")
            gui_status = "Động Cơ AI Sập"
            time.sleep(2)
            continue
            
        action = prediction['action']
        mse = prediction['mse']
        probs = {'buy': prediction['raw'][2], 'sell': prediction['raw'][0], 'loss': mse}
        
        if action is None:
            gui_status = "Động Cơ AI Sập"
            time.sleep(2)
            continue
            
        gui_prediction = f"B:{probs['buy']:.2f} S:{probs['sell']:.2f} (Loss:{mse:.3f})"
        gui_probs = {'buy': probs['buy'], 'sell': probs['sell'], 'loss': mse}

        # Tính hành động hiển thị thực tế (có xét vị thế đang giữ)
        if action == 2:
            display_action = "BUY"
        elif action == 0:
            display_action = "SELL"
        else:
            display_action = "HOLD"
        if hasattr(trade_manager, 'active_trade_loggers') and trade_manager.active_trade_loggers:
            for ticket, pos in trade_manager.active_trade_loggers.items():
                side = pos.get('side', '')
                if (side == 'SELL' and action == 'SELL') or (side == 'BUY' and action == 'BUY'):
                    display_action = f"GIỮ LỆNH {side} (#{ticket})"
                    break

        msg_pred = (
            f"🎯 KẾT QUẢ PIPELINE V6:\n"
            f"Nến: {gui_time}\n"
            f"Loss: {mse:.4f} (Ngưỡng: {engine.mse_threshold:.4f})\n"
            f"B/S: {probs['buy']:.1%} | {probs['sell']:.1%}\n"
            f"Action: {display_action}"
        )

        # Nối thông tin vị thế + P&L ngày (nếu trade_manager hỗ trợ)
        if hasattr(trade_manager, 'get_active_positions_report'):
            pos_rpt = trade_manager.get_active_positions_report()
            if pos_rpt:
                msg_pred += f"\n{pos_rpt}"
        if hasattr(trade_manager, '_get_daily_pnl'):
            daily_pnl = trade_manager._get_daily_pnl()
            msg_pred += f"\nLãi/Lỗ trong ngày: {daily_pnl:+.2f}$"

        print(f"[BOT V6] {msg_pred}")
        
        # [YÊU CẦU SẾP] Gửi tin nhắn Telegram khi lần đầu tiên tính được output của bộ não mới
        current_brain = CONFIG.get("HF_RUN_ID", "")
        if not hasattr(bot_background_loop, 'last_reported_brain'):
            bot_background_loop.last_reported_brain = None
            
        if current_brain != bot_background_loop.last_reported_brain:
            prefix = f"🧠 [DỰ ĐOÁN ĐẦU TIÊN - NÃO: {current_brain}]\n"
            tg_notify(prefix + msg_pred)
            bot_background_loop.last_reported_brain = current_brain
        else:
            # Gửi tin định kỳ nếu có sự kiện hoặc giãn cách (mặc định cho v6 nếu có action BUY/SELL)
            if action in [0, 2]: # BUY/SELL
                tg_notify(msg_pred)
        
        trading_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if not os.path.exists(trading_path):
            backup_path = trading_path.replace(r"C:\Program Files", r"D:\mt5").replace("C:\\Program Files", "D:\\mt5")
            if os.path.exists(backup_path): trading_path = backup_path

        if not DISABLE_MT5 and mt5_manager.current_connected_path != trading_path:
            mt5.shutdown()
            mt5.initialize(path=trading_path)
            mt5_manager.current_connected_path = trading_path
            
        if not hasattr(bot_background_loop, 'trade_execution_lock'):
            import concurrent.futures
            bot_background_loop.trade_execution_lock = threading.Lock()
            bot_background_loop.trade_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

        if bot_background_loop.trade_execution_lock.locked():
            print("[BOT V6] ⚠️ API đang xử lý lệnh trước đó, bỏ qua tín hiệu hiện tại để tránh Double Entry!")
            gui_status = "Đang xử lý API..."
        else:
            def _do_trade(t_action, t_probs, t_mse, t_bid, t_ask, t_point, t_sym):
                with bot_background_loop.trade_execution_lock:
                    try:
                        # Thêm timeout logic nếu có thể ở bên trong execute_trade
                        if isinstance(trade_manager, V3VirtualTradeManager):
                            trade_manager.execute_trade(t_action, t_probs, t_mse, t_bid, t_ask, t_point, actual_target_sym=t_sym)
                        else:
                            trade_manager.execute_trade(t_action, t_probs, t_mse, actual_target_sym=t_sym)
                    except Exception as e:
                        print(f"[BOT V6] ❌ Lỗi execute_trade: {e}")
            
            bot_background_loop.trade_executor.submit(_do_trade, display_action, probs, mse, current_bid, current_ask, current_point, actual_sym)
            gui_status = f"Đã gửi tín hiệu: {display_action}"
            
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
            root.geometry(f"360x220+{root.winfo_x()}+{root.winfo_y()}")
        else:
            frame_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            btn_toggle.config(text="⬆ Thu Gọn Bảng Giá")
            root.geometry(f"360x450+{root.winfo_x()}+{root.winfo_y()}")
            
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
