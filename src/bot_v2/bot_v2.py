import os
import sys
import io
import time
import json
import threading

# Ép hệ thống xuất Text tiếng Việt không bị Crash Console (Bắt buột trên Windows)
if sys.stdout is not None:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass
import tkinter as tk
from datetime import datetime, timezone

# Thêm đường dẫn gốc tự động
safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.bot_v2.cloud_manager_v2 import V2CloudManager
from src.bot_v2.config_loader_v2 import V2ConfigLoader
from src.bot_v2.data_processor_v2 import V2DataProcessor
from src.bot_v2.inference_engine_v2 import V2InferenceEngine
from src.bot_v2.trade_manager_v2 import V2TradeManager
from src.core.mt5_data_manager import MT5DataManager

# ----- THIẾT LẬP TELEGRAM BOT NOTIFIER -----
try:
    from src.orchestration.tg_helper import TelegramBot
    with open(os.path.join(safe_script_dir, "tg_config.json"), "r", encoding='utf-8') as f:
        tg_cfg = json.load(f)
    tg_bot_token = tg_cfg.get("bot_token", "")
    tg_chat_id = tg_cfg.get("allowed_chat_ids", [])[0] if tg_cfg.get("allowed_chat_ids") else None
    tg_bot = TelegramBot(tg_bot_token) if tg_bot_token else None
except Exception as e:
    tg_bot = None
    tg_chat_id = None

def tg_notify(msg):
    if tg_bot and tg_chat_id:
        try:
            tg_bot.send_message(tg_chat_id, msg)
        except: pass

# --- CẤU HÌNH GỐC TỪ FILE JSON ---
config_file = os.path.join(safe_script_dir, "data", "bot_config.json")
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.endswith('.json'):
            config_file = arg

TARGET_SYMBOL = "XAUUSD"
TARGET_PREFIX = "XAU_USD"
WEIGHT_FILE = "xauusd_unified_weights.pth"
WEIGHT_FILES = {}
CONFIG = {}

if os.path.exists(config_file):
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
            TARGET_SYMBOL = CONFIG.get("TARGET_SYMBOL", "XAUUSD")
            TARGET_PREFIX = CONFIG.get("TARGET_PREFIX", "XAU_USD")
            CONFIG_ID = CONFIG.get("CONFIG_ID", TARGET_PREFIX)
            WEIGHT_FILE = CONFIG.get("WEIGHT_FILE", "xauusd_unified_weights.pth")
            WEIGHT_FILES = CONFIG.get("WEIGHT_FILES", {})
    except: pass

# --- LÕI GIAO DIỆN KIỂM SOÁT TỔNG ---
gui_status = "Đang Sưởi Ấm Radar..."
gui_prediction = "Chờ Tín Hiệu..."
gui_time = "00:00:00"
gui_session = "Phiên: Đang đo Đạc..."
gui_market_data = []

# Khởi tạo Lõi Trade Manager của V2
trade_manager = V2TradeManager(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)

def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_session, gui_market_data, CONFIG
    print("[BOT] Đang kích hoạt OOP Modules...")
    
    # Init Classes
    cloud = V2CloudManager(TARGET_SYMBOL, TARGET_PREFIX, "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")
    engine = V2InferenceEngine()
    mt5_manager = MT5DataManager(log_callback=print, target_sym=TARGET_SYMBOL, config_path=config_file)
    trade_manager.init_mt5()
    processor = None
    
    sched_path = os.path.join(safe_script_dir, "data", "bot_v2_brain_schedule.json")
    config_loader = V2ConfigLoader(main_config_path=config_file, schedule_path=sched_path)
    
    # Lấy kiến trúc cố định (Base config)
    arch = CONFIG.get("TRAINING", {}).get("ARCH", {})
    window_size     = arch.get("win", 60)
    d_model         = arch.get("d_model", 256)
    nhead           = arch.get("heads", 8)
    num_attn_layers = arch.get("layers", 3)
    dropout_rate    = arch.get("dropout", 0.2)
    
    gui_status = "Đang kết nối MT5..."
    if not trade_manager.mt5.initialize(path=CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")):
        gui_status = "❌ Mất Kết Nối MT5 Terminal!"
        return
        
    last_tick_err_time = 0
    brain_loaded = False
    processor = None
    active_run_id = None
    
    while True:
        gui_time = datetime.now().strftime('%H:%M:%S')
        
        # --- HOT RELOAD CONFIGURATION ---
        CONFIG = config_loader.load_base_config()
        target_sess_name, target_sinfo, global_mt5_path = config_loader.get_current_schedule()
        CONFIG = config_loader.apply_schedule_overrides(CONFIG, target_sinfo, global_mt5_path)
        
        trade_manager.config = CONFIG
        trade_manager.update_gui_threshold()
        mt5_manager.config = CONFIG # Cấp config chuẩn cho trình quét Data
            
        if not target_sess_name:
            target_sess_name = "UNIFIED"
            
        target_run_id = target_sinfo.get("run_id") if target_sinfo else None
        
        # NẾU Session chỉ định bộ não MỚI, Yêu cầu tải lại NÃo ngay lập tức!
        if target_run_id and target_run_id != active_run_id:
            print(f"[SES-SCHED] Phát hiện Chuyển Sinh Phiên {target_sess_name.upper()}! Yêu Cầu Thay Não: {target_run_id}")
            brain_loaded = False
            
        if not brain_loaded:
            try:
                loc_config_id = CONFIG.get("CONFIG_ID", TARGET_PREFIX)
                
                if target_sinfo:
                    gui_session = f"{target_sess_name.upper()} [Đang kéo Cloud...]"
                    run_id = target_sinfo.get("run_id")
                    w_file = target_sinfo.get("weight_file")
                    cfg_id = target_sinfo.get("config_id")
                    
                    m_path, a_name, num_xau, n_feat, i_feats = cloud.sync_explicit_model(run_id, w_file, cfg_id)
                    active_run_id = run_id
                    gui_session = f"{target_sess_name.upper()} [{a_name[:15]}...]"
                    loc_config_id = cfg_id
                else:
                    gui_session = "UNIFIED [Đang kéo Cloud...]"
                    m_path, a_name, num_xau, n_feat, i_feats = cloud.sync_session_model(WEIGHT_FILE, "unified")
                    gui_session = f"UNIFIED [{a_name[:20]}]"
                    active_run_id = "unified"
                
                engine.load_weights(m_path, n_feat, d_model, nhead, num_attn_layers, dropout_rate, num_xau)
                
                scaler_path = os.path.join(safe_script_dir, "data", f"scaler_{loc_config_id}.pkl")
                processor = V2DataProcessor(scaler_path, i_feats, window_size)
                
                # BẮT BUỘC MT5 Data Manager PHẢI ĐỔI LƯỚI QUÉT DỮ LIỆU THEO BIẾN CỦA NÃO MỚI!
                mt5_manager.force_reload_dynamic_features(i_feats)
                
                brain_loaded = True
                gui_status = f"✅ Lắp Ráp NÃO [{target_sess_name.upper()}] Thành Công!"
            except Exception as ce:
                gui_status = f"❌ Lỗi Thay Não: {str(ce)[:30]}"
                print(f"Lỗi Thay Não: {ce}")
                time.sleep(5)
                continue
                
        # 2. Rà Soát Máy Chủ (Session Guards)
        mt5_manager.scan_terminals_and_map()
        
        # Luôn đảm bảo kết nối toàn cục MT5 đang hướng về Sàn Giao Dịch thực thi (Vì mt5_manager có thể đã nhảy sàn)
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
                print(f"⚠️ LỖI TICK: {actual_sym} không tồn tại (None!).")
                last_tick_err_time = time.time()
            time.sleep(1)
            continue
            
        staleness_secs = time.time() - tick.time
        if staleness_secs > 300:
            gui_status = f"Giá Freeze ({int(staleness_secs/60)}p)..."
            time.sleep(10)
            continue

        # 3. Kéo Số Liệu Nguyên Sinh (In-memory)
        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
        merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=120)
        
        # FIX CỰC KỲ QUAN TRỌNG: MT5Adapter nội bộ đã vấy bẩn (nhảy mạng) Global State của MT5.
        # Ta BẮT BUỘC phải reset cờ nhớ ảo này để ép các khối sau (như Đặt Lệnh và Loop Lịch) RE-INIT lại MT5 chính Giao dịch!
        mt5_manager.current_connected_path = None
        
        if err_msg:
            gui_status = err_msg
            time.sleep(2)
            continue
            
        gui_market_data = sorted(sym_data, key=lambda x: x[0])
        
        # 4. Pipeline Tiền Xử Lý Lượng Tử
        gui_status = "Chạy Pipeline Giải thuật V2..."
        t_seq, p_err = processor.ingest_and_scale(merged_df)
        if p_err:
            gui_status = f"Pipeline Từ Chối: {p_err[:30]}"
            print(f"⚠️ Pipeline Lỗi: {p_err}")
            time.sleep(2)
            continue
            
        # 5. Suy Diễn & Trích Tỷ Lệ Thắng
        gui_status = "Đang Trích Xuất Lực Cầu (Pytorch)..."
        pred, logits = engine.predict(t_seq)
        if pred is None:
            gui_status = "Động Cơ Torch Sập (No Preds)"
            time.sleep(2)
            continue
            
        gui_prediction = f"{pred*100:.2f}%"
        print(f"[{gui_time}] 🧠 LOGITS: {logits}. Lực Bò: {gui_prediction}")
        
        # 6. Mở Van Bắn Lệnh (Trade Sniper)
        trading_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if mt5_manager.current_connected_path != trading_path:
            trade_manager.mt5.shutdown()
            trade_manager.mt5.initialize(path=trading_path)
            mt5_manager.current_connected_path = trading_path
            
        trade_manager.manage_mt5_positions(pred, actual_target_sym=actual_sym)
        gui_status = "Khóa Mốc. Hoàn tất chu kỳ."
        
        time.sleep(3)

def update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target=None):
    if lbl_target: lbl_target.config(text=gui_target_text)
    lbl_time.config(text=f"🕒 {gui_time}")
    lbl_session.config(text=f"🌐 {gui_session}")
    lbl_action.config(text=f"🎯 Hành động: {trade_manager.gui_action}")
    lbl_status.config(text=f"⚙️ {gui_status}")
    lbl_thr.config(text=trade_manager.gui_thr_text)
    
    for item in tree.get_children():
        tree.delete(item)
    for sym, price, change, t_str, source_name, is_delayed in gui_market_data:
        change_text = f"🟢 {change:+.2f}" if change >= 0 else f"🔴 {change:+.2f}"
        color = "delayed" if is_delayed else "normal"
        source_display = f"Lỗi MT5" if is_delayed else "Mạng MT5"
        tree.insert("", "end", values=(sym, f"{price:,.2f}", change_text, source_display, t_str), tags=(color,))
        
    tree.tag_configure("normal", foreground="white")
    tree.tag_configure("delayed", foreground="#ffaa00")
    
    try:
        val = float(gui_prediction.replace('%', ''))
        if val >= 55: lbl_pred.config(text=f"🧠 BÒ TỚI (TĂNG): {gui_prediction}", fg="#00ffcc") 
        elif val <= 45: lbl_pred.config(text=f"🧠 GẤU TỚI (GIẢM): {gui_prediction}", fg="#ff3366") 
        else: lbl_pred.config(text=f"🧠 LƯỠNG LỰ: {gui_prediction}", fg="#cccccc") 
    except:
        pass
        
    root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target)

def start_overlay_dashboard():
    root = tk.Tk()
    root.title(f"MOE TERMINATOR V2 - {TARGET_SYMBOL}")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.90) 
    
    screen_h = root.winfo_screenheight()
    x_pos = 10 
    y_pos = screen_h - 550
        
    root.geometry(f"360x500+{x_pos}+{y_pos}")
    root.configure(bg='#121212') 
    
    root.x, root.y = 0, 0
    def start_move(e): root.x, root.y = e.x, e.y
    def stop_move(e): root.x, root.y = None, None
    def do_move(event):
        if root.x is None or root.y is None: return
        x = root.winfo_x() + event.x - root.x
        y = root.winfo_y() + event.y - root.y
        root.geometry(f"+{x}+{y}")
        
    root.bind("<ButtonPress-1>", start_move)
    root.bind("<ButtonRelease-1>", stop_move)
    root.bind("<B1-Motion>", do_move)
    
    tk.Label(root, text=f"🔥 {TARGET_SYMBOL} OOP TERMINATOR [v2.0] 🔥", fg="#ffcc00", bg="#121212", font=("Helvetica", 11, "bold")).pack(pady=2)
    lbl_session = tk.Label(root, text="🌐 Phiên: Đang khởi chạy", fg="#cc88ff", bg="#121212", font=("Helvetica", 9, "bold"))
    lbl_session.pack()
    lbl_pred = tk.Label(root, text="🧠 THỜI CƠ (Lực): N/A", fg="#cccccc", bg="#121212", font=("Helvetica", 10, "bold"))
    lbl_pred.pack()
    lbl_action = tk.Label(root, text="🎯 Hành động: Đang ngủ", fg="#ff9900", bg="#121212", font=("Helvetica", 9))
    lbl_action.pack()
    lbl_thr = tk.Label(root, text="⚖️ Ngưỡng L4: Chờ Load", fg="#ff33cc", bg="#121212", font=("Helvetica", 9, "bold"))
    lbl_thr.pack()
    
    frame_data = tk.Frame(root, bg="#121212")
    frame_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    from tkinter import ttk
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#1e1e1e", foreground="white", fieldbackground="#1e1e1e", borderwidth=0)
    style.configure("Treeview.Heading", background="#333", foreground="white", font=("Helvetica", 8, "bold"))
    
    columns = ("Symbol", "Price", "Change", "DataStatus", "Time")
    tree = ttk.Treeview(frame_data, columns=columns, show="headings", height=8)
    tree.heading("Symbol", text="Mã")
    tree.heading("Price", text="Giá")
    tree.heading("Change", text="Biến Động")
    tree.heading("DataStatus", text="Nguồn")
    tree.heading("Time", text="Giờ")
    
    tree.column("Symbol", width=70, anchor="w")
    tree.column("Price", width=65, anchor="e")
    tree.column("Change", width=65, anchor="e")
    tree.column("DataStatus", width=70, anchor="w")
    tree.column("Time", width=60, anchor="center")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    lbl_status = tk.Label(root, text="⚙️ Đang Khởi Đoạt Mạng", fg="#aaaaaa", bg="#121212", font=("Helvetica", 8))
    lbl_status.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
    lbl_time = tk.Label(root, text="🕒 00:00:00", fg="#888888", bg="#121212", font=("Helvetica", 8))
    lbl_time.pack(side=tk.BOTTOM)
    
    update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr)
    root.mainloop()

if __name__ == "__main__":
    t = threading.Thread(target=bot_background_loop)
    t.daemon = True
    t.start()
    start_overlay_dashboard()
