import os
import sys
import io
import time
import json
import threading
import tkinter as tk
from datetime import datetime, timezone

if sys.stdout is not None:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.core.mt5_data_manager import MT5DataManager
import logging

log_dir = os.path.join(safe_script_dir, "data", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"trade_bot_master_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
def custom_print(*args, **kwargs):
    logging.info(" ".join(map(str, args)))
print = custom_print

try:
    from src.orchestration.tg_helper import TelegramBot
    with open(os.path.join(safe_script_dir, "tg_config.json"), "r", encoding='utf-8') as f:
        tg_cfg = json.load(f)
    tg_bot = TelegramBot(tg_cfg.get("bot_token", "")) if tg_cfg.get("bot_token") else None
    tg_chat_id = tg_cfg.get("allowed_chat_ids", [])[0] if tg_cfg.get("allowed_chat_ids") else None
except Exception:
    tg_bot, tg_chat_id = None, None

def tg_notify(msg):
    if tg_bot and tg_chat_id:
        try: tg_bot.send_message(tg_chat_id, msg)
        except: pass

config_file = os.path.join(safe_script_dir, "data", "bot_config_xau_ny_v3_5.json")
schedule_file = None
if len(sys.argv) > 1:
    args_json = [arg for arg in sys.argv if arg.endswith('.json')]
    if len(args_json) >= 1:
        config_file = args_json[0]
    if len(args_json) >= 2:
        schedule_file = args_json[1]

# Cấu hình BASE ban đầu
CONFIG = {}
if os.path.exists(config_file):
    with open(config_file, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)

# DETECT BOT VERSION FROM CONFIG
BOT_VERSION = CONFIG.get("VERSION", "").lower().strip()
if not BOT_VERSION:
    cfg_id = CONFIG.get("CONFIG_ID", "").lower()
    if "v2" in cfg_id:
        BOT_VERSION = "v2"
    else:
        BOT_VERSION = "v3"
        
if BOT_VERSION.startswith("2"):
    BOT_VERSION = "v2"
elif BOT_VERSION.startswith("3"):
    BOT_VERSION = "v3"

print(f"[BOT MASTER] Phát hiện mã phiên bản BOT_VERSION = {BOT_VERSION.upper()} từ {os.path.basename(config_file)}")

if not schedule_file:
    schedule_file = os.path.join(safe_script_dir, "data", f"bot_{BOT_VERSION}_brain_schedule.json")

# IMPORTS DYNAMIC TỪNG VERSION
if BOT_VERSION == "v3":
    from src.bot_v3.cloud_manager_v3 import V3CloudManager as CloudManager
    from src.bot_v3.data_processor_v3 import V3DataProcessor as DataProcessor
    from src.bot_v3.inference_engine_v3 import V3InferenceEngine as InferenceEngine
    from src.bot_v3.trade_manager_v3 import V3TradeManager as TradeManager
    from src.bot_v3.config_loader_v3 import V3ConfigLoader as ConfigLoader
else:
    from src.bot_v2.cloud_manager_v2 import V2CloudManager as CloudManager
    from src.bot_v2.data_processor_v2 import V2DataProcessor as DataProcessor
    from src.bot_v2.inference_engine_v2 import V2InferenceEngine as InferenceEngine
    from src.bot_v2.trade_manager_v2 import V2TradeManager as TradeManager
    from src.bot_v2.config_loader_v2 import V2ConfigLoader as ConfigLoader

# Khởi tạo Config Loader theo từng phiên bản
config_loader = ConfigLoader(config_file, schedule_file, log_callback=print) if BOT_VERSION == "v3" else ConfigLoader(config_file, schedule_file)

if hasattr(config_loader, "load_base_config"):
    CONFIG = config_loader.load_base_config()

TARGET_SYMBOL = CONFIG.get("TARGET_SYMBOL", "XAUUSD")
TARGET_PREFIX = CONFIG.get("TARGET_PREFIX", "XAUUSD")

trade_manager = TradeManager(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)

gui_status = f"Đang Sưởi Ấm Radar {BOT_VERSION.upper()}..."
gui_prediction = "Chờ Tín Hiệu..."
gui_time = "00:00:00"
gui_session = "Phiên: Đang khởi chạy..."
gui_market_data = []

def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_session, gui_market_data, CONFIG
    print(f"[BOT MASTER] ===== Khởi động OOP Modules {BOT_VERSION.upper()} (UNIFIED) =====")
    
    engine = InferenceEngine(log_callback=print)
    mt5_manager = MT5DataManager(log_callback=print, target_sym=TARGET_SYMBOL, config_path=config_file)
    trade_manager.init_mt5()
    processor = None
    cloud = None
    if BOT_VERSION == "v2":
        cloud = CloudManager(TARGET_SYMBOL, TARGET_PREFIX, "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", log_callback=print)
    
    mt5_init_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    gui_status = "Đang kết nối MT5..."
    if not trade_manager.mt5.initialize(path=mt5_init_path):
        gui_status = "❌ Mất Kết Nối MT5 Terminal!"
        print("[BOT MASTER] ❌ FATAL: Không thể khởi tạo kết nối MT5.")
        return
        
    last_tick_err_time = 0
    brain_loaded = False
    active_run_id = None
    cycle_count = 0
    last_candle_time = None
    startup_msg_sent = False
    tele_msg_count = 0
    
    global gui_v3_probs, gui_action
    gui_v3_probs = {"buy": 0, "sell": 0, "hold": 1}
    gui_action = "N/A"
    
    trade_manager.sync_existing_positions()

    while True:
        cycle_count += 1
        gui_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n[BOT MASTER] ────── Chu kỳ #{cycle_count} | {gui_time} ──────")
        
        # 1. Hot-reload Config & Schedule
        if hasattr(config_loader, "load_base_config"):
            base_cfg = config_loader.load_base_config()
            if base_cfg:
                CONFIG = base_cfg
                
        if BOT_VERSION == "v3":
            sess_name, sinfo, global_mt5 = config_loader.get_current_schedule()
        else:
            sess_name, sinfo, global_mt5 = config_loader.get_current_schedule()
        
        target_run_id = None
        if sinfo:
            if BOT_VERSION == "v3":
                CONFIG = config_loader.apply_schedule_overrides(CONFIG, sinfo, global_mt5)
            else:
                CONFIG = config_loader.apply_schedule_overrides(CONFIG, sinfo, global_mt5)
            target_run_id = sinfo.get("run_id") if BOT_VERSION == "v2" else CONFIG.get("HF_RUN_ID", "")
        else:
            if BOT_VERSION == "v2": target_run_id = "unified"
            
        trade_manager.config = CONFIG
        mt5_manager.config = CONFIG
        trade_manager.update_gui_threshold()
        
        # Ngưỡng V3 check
        if BOT_VERSION == "v3":
            bot_cfg = CONFIG.get("LIVE_BOT", {})
            engine.mse_threshold = bot_cfg.get("MSE_THRESHOLD_PERCENTILE", 70.0)
            engine.prob_threshold = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.70)
            target_run_id = CONFIG.get("HF_RUN_ID", "")
            
        if not startup_msg_sent:
            startup_msg = f"🤖 [BOT {BOT_VERSION.upper()} MASTER SẴN SÀNG]\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n🌐 Phiên gốc: {sess_name.upper() if sess_name else 'Mặc định'}\n💹 Mã: {TARGET_SYMBOL} | Config Active: {CONFIG.get('CONFIG_ID', 'UNKNOWN')}"
            tg_notify(startup_msg)
            startup_msg_sent = True
            
        cfg_id = CONFIG.get("CONFIG_ID", "")

        if target_run_id and target_run_id != active_run_id:
            msg = f"🔄 Chuyển đổi Khung Giờ (Phiên {sess_name})!\nĐang Hủy Não [{active_run_id}] để tải Não mới [{target_run_id}]..."
            print(f"[BOT MASTER] {msg}")
            tg_notify(msg)
            brain_loaded = False
            if BOT_VERSION == "v3":
                cloud = CloudManager(TARGET_SYMBOL, TARGET_PREFIX, "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", CONFIG, log_callback=print)
            
        if not brain_loaded and cloud is not None:
            print(f"[BOT MASTER] Bắt đầu tải não AAMT...")
            gui_status = "Đang Tải NÃO từ Cloud..."
            try:
                if BOT_VERSION == "v3":
                    m_path, s_path, i_feats, n_feat = cloud.sync_session_model(cfg_id)
                    active_run_id = target_run_id
                    
                    arch = CONFIG.get("TRAINING", {})
                    window_size = CONFIG.get("FEATURE_ENGINEERING", {}).get("WINDOW_SIZE", 60)
                    d_model = arch.get("D_MODEL", 128)
                    nhead = arch.get("N_HEAD", 8)
                    num_attn_layers = arch.get("NUM_LAYERS", 4)
                    
                    engine.load_weights(m_path, n_feat, d_model, nhead, num_attn_layers, window_size)
                    processor = DataProcessor(s_path, i_feats, window_size, config=CONFIG, log_callback=print)
                    mt5_manager.force_reload_dynamic_features(i_feats)
                    
                    brain_loaded = True
                    gui_status = "✅ Lắp Ráp NÃO V3 Thành Công!"
                    gui_session = f"PHIÊN {sess_name.upper() if sess_name else 'UNKNOWN'} (Não V3: {os.path.basename(m_path)[:10]})"
                    msg_done = f"✅ Lắp ráp NÃO V3 Xong!\nKhởi tạo thành công Mạng Nơ-ron (Loss %: {bot_cfg.get('MSE_THRESHOLD_PERCENTILE', 70)})\nBot đang nghe ngóng thị trường..."
                    tg_notify(msg_done)
                else: # V2
                    w_file = sinfo.get("weight_file", CONFIG.get("WEIGHT_FILE", "unified_weights.pth")) if sinfo else CONFIG.get("WEIGHT_FILE")
                    if sinfo:
                        m_path, a_name, num_xau, n_feat, i_feats = cloud.sync_explicit_model(target_run_id, w_file, cfg_id)
                    else:
                        m_path, a_name, num_xau, n_feat, i_feats = cloud.sync_session_model(w_file, "unified")
                    
                    active_run_id = target_run_id
                    arch = CONFIG.get("TRAINING", {}).get("ARCH", {})
                    window_size = arch.get("win", 60)
                    engine.load_weights(m_path, n_feat, arch.get("d_model", 256), arch.get("heads", 8), arch.get("layers", 3), arch.get("dropout", 0.2), num_xau)
                    
                    scaler_path = os.path.join(safe_script_dir, "data", f"scaler_{cfg_id}.pkl")
                    processor = DataProcessor(scaler_path, i_feats, window_size, log_callback=print)
                    mt5_manager.force_reload_dynamic_features(i_feats)
                    
                    brain_loaded = True
                    gui_status = f"✅ Lắp Ráp NÃO V2 [{sess_name.upper()}] Thành Công!"
                    gui_session = f"PHIÊN {sess_name.upper() if sess_name else 'UNIFIED'} (Não V2)"
            except Exception as ce:
                gui_status = f"❌ Lỗi Thay Não: {str(ce)[:30]}"
                print(f"[BOT MASTER] ❌ Lỗi tải não: {ce}")
                import traceback; print(traceback.format_exc())
                time.sleep(5)
                continue
                
        if not brain_loaded:
            print("[BOT MASTER] Chưa có Bộ Não nào được cấu hình hợ lệ. Đợi 5s...")
            time.sleep(5)
            continue
            
        print("[BOT MASTER] Quét các cổng MT5...")
        mt5_manager.scan_terminals_and_map()
        
        trading_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if mt5_manager.current_connected_path != trading_path:
            trade_manager.mt5.shutdown()
            trade_manager.mt5.initialize(path=trading_path)
            mt5_manager.current_connected_path = trading_path

        actual_sym = mt5_manager.IN_MEMORY_SYMBOL_HINT.get(TARGET_SYMBOL, TARGET_SYMBOL)
        trade_manager.mt5.symbol_select(actual_sym, True)
        
        tick = trade_manager.mt5.symbol_info_tick(actual_sym)
        if tick is None:
            if time.time() - last_tick_err_time > 10:
                print(f"[BOT MASTER] ⚠️ LỖI TICK: {actual_sym} = None! Reconnect...")
                last_tick_err_time = time.time()
            mt5_manager.current_connected_path = None
            time.sleep(1)
            continue
            
        staleness_secs = time.time() - tick.time
        if staleness_secs > 300:
            gui_status = f"Giá Freeze ({int(staleness_secs/60)}p)..."
            time.sleep(10)
            continue
            
        current_candle_time = int(time.time() // 10) * 10
        if current_candle_time == last_candle_time:
            time.sleep(1)
            continue
            
        last_candle_time = current_candle_time
        print(f"[BOT MASTER] 🕒 Nến M1 Mới | {datetime.fromtimestamp(current_candle_time, timezone.utc).strftime('%H:%M')} UTC")

        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
        merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=120)
        mt5_manager.current_connected_path = None
        
        if err_msg or merged_df is None or len(merged_df) == 0:
            gui_status = err_msg or "Dữ liệu rỗng"
            time.sleep(2)
            continue
            
        gui_market_data = sorted(sym_data, key=lambda x: x[0])
        gui_status = f"Chạy Pipeline Giải thuật {BOT_VERSION.upper()}..."
        
        t_seq, p_err = processor.ingest_and_scale(merged_df)
        if p_err:
            gui_status = f"Pipeline Từ Chối: {p_err[:40]}"
            time.sleep(2)
            continue
            
        gui_status = "Đang Trích Xuất Phân Rã Không Gian..."
        
        if BOT_VERSION == "v3":
            action, mse, probs = engine.predict(t_seq)
            if action is None:
                gui_status = "Động Cơ AI Sập"
                time.sleep(2)
                continue
            
            gui_v3_probs = probs
            gui_action = action
            
            gui_prediction = f"B:{probs['buy']*100:.1f}%  S:{probs['sell']*100:.1f}%  (Loss:{mse:.3f})"
            msg_pred = f"🎯 KẾT QUẢ DỰ ĐOÁN:\nNến {gui_time} | L: {mse:.4f}\n(Thresh: {engine.mse_threshold:.4f})\nTỷ lệ: BUY={probs['buy']:.2%} | SELL={probs['sell']:.2%}\nHành động: {action}"
            print(f"[BOT MASTER] {msg_pred}")
            
            # Gửi 3 lần đầu hoặc khi vươn tới sát ngưỡng (vd: mấp mé ngưỡng 15%)
            is_approaching = max(probs['buy'], probs['sell']) >= (engine.prob_threshold - 0.15)
            is_trade_action = action in ["BUY", "SELL"]
            
            if tele_msg_count < 3 or is_approaching or is_trade_action:
                prefix = "⚠️ [SẮP ĐẠT NGƯỠNG] " if (is_approaching and not is_trade_action) else ("🔥 [TÍN HIỆU] " if is_trade_action else "📊 [CẬP NHẬT ĐỊNH KỲ] ")
                tg_notify(prefix + msg_pred)
                if not (is_approaching or is_trade_action):
                    tele_msg_count += 1
                    
            trade_manager.manage_mt5_positions(action, probs, mse, actual_target_sym=actual_sym)
            gui_status = f"Khóa Mốc. Hành động: {action}"
        else: # V2
            pred, logits = engine.predict(t_seq)
            if pred is None:
                gui_status = "Động Cơ Torch Sập"
                time.sleep(2)
                continue
            gui_prediction = f"{pred*100:.2f}%"
            print(f"[BOT MASTER] Lực Bò={gui_prediction}")
            trade_manager.manage_mt5_positions(pred, actual_target_sym=actual_sym)
            gui_status = "Khóa Mốc. Hoàn tất chu kỳ."

        time.sleep(1)

def update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target=None, pred_canvas=None):
    if lbl_target: lbl_target.config(text=TARGET_SYMBOL)
    lbl_time.config(text=f"🕒 {gui_time}")
    lbl_session.config(text=f"🌐 {gui_session}")
    lbl_action.config(text=f"🎯 Chiến thuật: {trade_manager.gui_action}")
    lbl_status.config(text=f"⚙️ {gui_status}")
    lbl_thr.config(text=trade_manager.gui_thr_text)
    
    for item in tree.get_children():
        tree.delete(item)
    for data in gui_market_data:
        sym, price, change, t_str = data[0], data[1], data[2], data[3]
        change_text = f"🟢 {change:+.2f}" if change >= 0 else f"🔴 {change:+.2f}"
        
        is_delayed = data[5] if len(data) >= 6 else False
        source_display = f"⚠️ TRỄ DATA" if is_delayed else "Live MT5"
        tree.insert("", "end", values=(sym, f"{price:,.2f}", change_text, source_display, t_str), tags=("delayed" if is_delayed else "normal",))
        
    tree.tag_configure("normal", foreground="white")
    tree.tag_configure("delayed", foreground="#ff3333", background="#330000")
    
    if BOT_VERSION == "v3":
        lbl_pred.config(text=f"🧠 Tín Hiệu: {gui_prediction}", fg="#00ffcc" if gui_action == "BUY" else "#ff3366" if gui_action == "SELL" else "#cccccc")
        
        if pred_canvas:
            pred_canvas.delete("all")
            w_buy = int(300 * gui_v3_probs.get("buy", 0))
            w_sell = int(300 * gui_v3_probs.get("sell", 0))
            w_hold = int(300 * gui_v3_probs.get("hold", 0))
            
            # Left: BUY (Green), Middle: HOLD (Gray), Right: SELL (Red)
            if w_buy > 0: pred_canvas.create_rectangle(0, 0, w_buy, 15, fill="#00ffcc", outline="")
            if w_hold > 0: pred_canvas.create_rectangle(w_buy, 0, w_buy + w_hold, 15, fill="#555555", outline="")
            if w_sell > 0: pred_canvas.create_rectangle(w_buy + w_hold, 0, 300, 15, fill="#ff3366", outline="")
            
            # Borders for active action threshold if close
            if gui_action == "BUY": pred_canvas.create_rectangle(0, 0, w_buy, 15, outline="#ffffff", width=2)
            if gui_action == "SELL": pred_canvas.create_rectangle(w_buy + w_hold, 0, 300, 15, outline="#ffffff", width=2)
            
    else:
        try:
            val = float(gui_prediction.replace('%', ''))
            if val >= 55: lbl_pred.config(text=f"🧠 BÒ TỚI (TĂNG): {gui_prediction}", fg="#00ffcc") 
            elif val <= 45: lbl_pred.config(text=f"🧠 GẤU TỚI (GIẢM): {gui_prediction}", fg="#ff3366") 
            else: lbl_pred.config(text=f"🧠 LƯỠNG LỰ: {gui_prediction}", fg="#cccccc") 
        except: pass
        
    root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target, pred_canvas)

def start_overlay_dashboard():
    root = tk.Tk()
    root.title(f"AAMT TERMINATOR {BOT_VERSION.upper()} - {TARGET_SYMBOL}")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.92) 
    
    screen_h = root.winfo_screenheight()
    root.geometry(f"380x480+10+{screen_h - 520}")
    root.configure(bg='#080b12') 
    
    root.x, root.y = 0, 0
    def do_move(event):
        if root.x is None or root.y is None: return
        root.geometry(f"+{root.winfo_x() + event.x - root.x}+{root.winfo_y() + event.y - root.y}")
        
    # CUSTOM TITLE BAR
    title_bar = tk.Frame(root, bg="#111625", relief="raised", bd=1)
    title_bar.pack(expand=0, fill=tk.X)
    
    title_label = tk.Label(title_bar, text=f"🌌 {TARGET_SYMBOL} MASTER {BOT_VERSION.upper()} 🌌", fg="#00ffff", bg="#111625", font=("Consolas", 10, "bold"))
    title_label.pack(side=tk.LEFT, padx=5, pady=2)
    
    btn_frame = tk.Frame(title_bar, bg="#111625")
    btn_frame.pack(side=tk.RIGHT, padx=2)
    
    btn_min = tk.Button(btn_frame, text="—", bg="#111625", fg="white", bd=0, padx=5, command=lambda: root.geometry("380x30"), activebackground="#333333", activeforeground="white")
    btn_min.pack(side=tk.LEFT)
    btn_max = tk.Button(btn_frame, text="🗖", bg="#111625", fg="white", bd=0, padx=5, command=lambda: root.geometry(f"380x480"), activebackground="#333333", activeforeground="white")
    btn_max.pack(side=tk.LEFT)
    btn_close = tk.Button(btn_frame, text="X", bg="#ff3333", fg="white", bd=0, padx=5, command=lambda: os._exit(0), activebackground="#aa0000", activeforeground="white")
    btn_close.pack(side=tk.LEFT)
    
    title_bar.bind("<ButtonPress-1>", lambda e: setattr(root, 'x', e.x) or setattr(root, 'y', e.y))
    title_bar.bind("<ButtonRelease-1>", lambda e: setattr(root, 'x', None) or setattr(root, 'y', None))
    title_bar.bind("<B1-Motion>", do_move)
    title_label.bind("<ButtonPress-1>", lambda e: setattr(root, 'x', e.x) or setattr(root, 'y', e.y))
    title_label.bind("<ButtonRelease-1>", lambda e: setattr(root, 'x', None) or setattr(root, 'y', None))
    title_label.bind("<B1-Motion>", do_move)
    
    lbl_session = tk.Label(root, text="🌐 Phiên: Đang khởi chạy", fg="#aa66ff", bg="#080b12", font=("Consolas", 9))
    lbl_session.pack()
    lbl_pred = tk.Label(root, text="🧠 THỜI CƠ: N/A", fg="#cccccc", bg="#080b12", font=("Consolas", 10, "bold"))
    lbl_pred.pack(pady=2)
    
    pred_canvas = None
    if BOT_VERSION == "v3":
        pred_canvas = tk.Canvas(root, width=300, height=15, bg="#222222", highlightthickness=0)
        pred_canvas.pack(pady=2)
        
    lbl_action = tk.Label(root, text="🎯 Chiến thuật: Đang ngủ", fg="#ffcc00", bg="#080b12", font=("Consolas", 9))
    lbl_action.pack()
    lbl_thr = tk.Label(root, text="⚖️ Ngưỡng L4: Chờ Load", fg="#ff55bb", bg="#080b12", font=("Consolas", 9))
    lbl_thr.pack()
    
    from tkinter import ttk
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#111625", foreground="white", fieldbackground="#111625", borderwidth=0)
    style.configure("Treeview.Heading", background="#1a2235", foreground="#00ffff", font=("Consolas", 8, "bold"))
    
    frame_data = tk.Frame(root, bg="#080b12")
    
    def toggle_table():
        if frame_data.winfo_viewable():
            frame_data.pack_forget()
            btn_toggle_table.config(text="Hiển thị Bảng Giá ▼")
            root.geometry("380x180")
        else:
            frame_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, before=lbl_status_frame)
            btn_toggle_table.config(text="Thu gọn Bảng Giá ▲")
            root.geometry("380x480")
            
    btn_toggle_table = tk.Button(root, text="Thu gọn Bảng Giá ▲", bg="#1a2235", fg="#00ffff", bd=0, command=toggle_table, font=("Consolas", 8), cursor="hand2")
    btn_toggle_table.pack(pady=2)
    
    frame_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    cols = ("Symbol", "Price", "Change", "S-Status", "Time")
    tree = ttk.Treeview(frame_data, columns=cols, show="headings", height=8)
    for c in cols: tree.heading(c, text=c)
    for c, w in zip(cols, (70, 65, 65, 75, 55)): tree.column(c, width=w, anchor="e" if c != "Symbol" and c != "S-Status" else "w")
    
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    lbl_status_frame = tk.Frame(root, bg="#080b12")
    lbl_status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
    
    lbl_status = tk.Label(lbl_status_frame, text="⚙️ Đang Khởi Đoạt Mạng", fg="#aaaaaa", bg="#080b12", font=("Consolas", 8))
    lbl_status.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
    lbl_time = tk.Label(lbl_status_frame, text="🕒 00:00:00", fg="#888888", bg="#080b12", font=("Consolas", 8))
    lbl_time.pack(side=tk.BOTTOM)
    
    update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, pred_canvas=pred_canvas)
    root.mainloop()

if __name__ == "__main__":
    t = threading.Thread(target=bot_background_loop)
    t.daemon = True
    t.start()
    start_overlay_dashboard()
