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
import logging

# Move logs to data/logs instead of root to keep source code clean
log_dir = os.path.join(safe_script_dir, "data", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"trade_bot_v2_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
def custom_print(*args, **kwargs):
    msg = " ".join(map(str, args))
    # Hack to avoid double printing if logging already prints to stdout, but we used basicConfig with StreamHandler
    # Actually basicConfig with StreamHandler will print to console!
    logging.info(msg)

print = custom_print

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
    print("[BOT] ===== Khởi động OOP Modules V2.0 =====")
    
    # Init Classes - truyền log_callback vào từng sub-component
    cloud = V2CloudManager(TARGET_SYMBOL, TARGET_PREFIX, "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", log_callback=print)
    engine = V2InferenceEngine(log_callback=print)
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
    
    mt5_init_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    print(f"[BOT] Kết nối MT5 tại: {mt5_init_path}")
    gui_status = "Đang kết nối MT5..."
    if not trade_manager.mt5.initialize(path=mt5_init_path):
        gui_status = "❌ Mất Kết Nối MT5 Terminal!"
        print("[BOT] ❌ FATAL: Không thể khởi tạo kết nối MT5.")
        return
        
    last_tick_err_time = 0
    brain_loaded = False
    processor = None
    active_run_id = None
    cycle_count = 0
    last_candle_time = None  # Track timestamp nến M1 cuối cùng đã xử lý
    print("[BOT] ✅ MT5 đã kết nối. Bắt đầu vòng lặp chính...")

    # Quét ngay lập tức các lệnh đang sẵn có trên sàn để track PnL từ đầu
    print("[BOT] 🔄 Sync lệnh đang có trên sàn (nếu có)...")
    trade_manager.sync_existing_positions()

    # Gửi thông báo khởi động lên Telegram
    live_cfg_startup = CONFIG.get("LIVE_TRADING", {})
    startup_msg = (
        f"🤖 [BOT KHỚI ĐỘNG]"
        f"\n⏰ Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        f"\n💹 Mã: {TARGET_SYMBOL} | Config: {config_file}"
        f"\n📌 Cấu hình giao dịch:"
        f"\n  - Ngưỡng MUA: {live_cfg_startup.get('BUY_ENTRY_THR', '?')}"
        f"\n  - Ngưỡng BÁN: {live_cfg_startup.get('SELL_ENTRY_THR', '?')}"
        f"\n  - Đóng BUY khi pred < {live_cfg_startup.get('CLOSE_BUY_THR', '?')}"
        f"\n  - Đóng SELL khi pred > {live_cfg_startup.get('CLOSE_SELL_THR', '?')}"
        f"\n  - Lot size: {live_cfg_startup.get('lot_size', '?')}"
        f"\n  - SL: {live_cfg_startup.get('sl_pips', '?')} pips | TP: {live_cfg_startup.get('tp_pips', '?')} pips"
        f"\n📊 Lệnh sẵn có: {len(trade_manager.active_trade_loggers)} lệnh"
    )
    print(f"[BOT] {startup_msg}")
    tg_notify(startup_msg)

    # Snapshot config để detect thay đổi
    _last_live_cfg_snapshot = dict(live_cfg_startup)

    while True:
        cycle_count += 1
        gui_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n[BOT] ────── Chu kỳ #{cycle_count} | {gui_time} ──────")
        
        # ── STEP 1: Hot Reload Config ──
        CONFIG = config_loader.load_base_config()
        target_sess_name, target_sinfo, global_mt5_path = config_loader.get_current_schedule()
        CONFIG = config_loader.apply_schedule_overrides(CONFIG, target_sinfo, global_mt5_path)
        trade_manager.config = CONFIG
        trade_manager.update_gui_threshold()
        mt5_manager.config = CONFIG
        print(f"[BOT] STEP 1 Config ↻ | phiên='{target_sess_name}'")

        # ── Kiểm tra thay đổi config LIVE_TRADING ──
        current_live_cfg = CONFIG.get("LIVE_TRADING", {})
        changed_keys = [
            k for k in current_live_cfg
            if current_live_cfg.get(k) != _last_live_cfg_snapshot.get(k)
        ]
        if changed_keys:
            lines = [f"  - {k}: {_last_live_cfg_snapshot.get(k, 'N/A')} → {current_live_cfg[k]}" for k in changed_keys]
            change_msg = (
                f"❗ [CẤU HÌNH THAY ĐỔI]"
                f"\n⏰ {datetime.now().strftime('%H:%M:%S')} | Phiên: {target_sess_name}"
                f"\n" + "\n".join(lines)
            )
            print(f"[BOT] CONFIG DIFF: {changed_keys}")
            tg_notify(change_msg)
            _last_live_cfg_snapshot = dict(current_live_cfg)

        if not target_sess_name:
            target_sess_name = "UNIFIED"
            
        target_run_id = target_sinfo.get("run_id") if target_sinfo else None
        
        # ── STEP 2: Kiểm tra thay não ──
        if target_run_id and target_run_id != active_run_id:
            print(f"[BOT] STEP 2 Phát hiện Não mới! {active_run_id} → {target_run_id}")
            brain_loaded = False
            
        if not brain_loaded:
            print(f"[BOT] STEP 2 Bắt đầu tải não cho phiên '{target_sess_name.upper()}'...")
            try:
                loc_config_id = CONFIG.get("CONFIG_ID", TARGET_PREFIX)
                
                if target_sinfo:
                    gui_session = f"{target_sess_name.upper()} [Đang kéo Cloud...]"
                    run_id = target_sinfo.get("run_id")
                    w_file = target_sinfo.get("weight_file")
                    cfg_id = target_sinfo.get("config_id")
                    print(f"[BOT] STEP 2 Sync explicit | run={run_id} weight={w_file} cfg={cfg_id}")
                    
                    m_path, a_name, num_xau, n_feat, i_feats = cloud.sync_explicit_model(run_id, w_file, cfg_id)
                    active_run_id = run_id
                    gui_session = f"{target_sess_name.upper()} [{a_name[:15]}...]"
                    loc_config_id = cfg_id
                else:
                    gui_session = "UNIFIED [Đang kéo Cloud...]"
                    print("[BOT] STEP 2 Sync session UNIFIED")
                    m_path, a_name, num_xau, n_feat, i_feats = cloud.sync_session_model(WEIGHT_FILE, "unified")
                    gui_session = f"UNIFIED [{a_name[:20]}]"
                    active_run_id = "unified"
                
                print(f"[BOT] STEP 2 Load weights | n_feat={n_feat} n_xau={num_xau}")
                engine.load_weights(m_path, n_feat, d_model, nhead, num_attn_layers, dropout_rate, num_xau)
                
                scaler_path = os.path.join(safe_script_dir, "data", f"scaler_{loc_config_id}.pkl")
                print(f"[BOT] STEP 2 Init DataProcessor | scaler={os.path.basename(scaler_path)}")
                processor = V2DataProcessor(scaler_path, i_feats, window_size, log_callback=print)
                
                print(f"[BOT] STEP 2 Đồng bộ MT5DataManager với {len(i_feats)} features")
                mt5_manager.force_reload_dynamic_features(i_feats)
                
                brain_loaded = True
                gui_status = f"✅ Lắp Ráp NÃO [{target_sess_name.upper()}] Thành Công!"
                print(f"[BOT] STEP 2 ✅ Não sẵn sàng | session='{target_sess_name.upper()}'")
            except Exception as ce:
                gui_status = f"❌ Lỗi Thay Não: {str(ce)[:30]}"
                print(f"[BOT] STEP 2 ❌ Lỗi tải não: {ce}")
                import traceback; print(traceback.format_exc())
                time.sleep(5)
                continue
                
        # ── STEP 3: Scan & Guard MT5 Connection ──
        print("[BOT] STEP 3 Scan terminals...")
        mt5_manager.scan_terminals_and_map()
        
        # Bảo đảm kết nối MT5 đang trỏ về Trading Terminal (không phải broker data)
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
                print(f"[BOT] ⚠️ LỖI TICK: {actual_sym} = None! Kiểm tra kết nối MT5. Force reconnect...")
                last_tick_err_time = time.time()
            mt5_manager.current_connected_path = None # Force re-init in next loop
            time.sleep(1)
            continue
            
        staleness_secs = time.time() - tick.time
        if staleness_secs > 300:
            gui_status = f"Giá Freeze ({int(staleness_secs/60)}p)..."
            print(f"[BOT] ⚠️ Giá {actual_sym} bị stale {int(staleness_secs)}s! Đang chờ...")
            time.sleep(10)
            continue
        
        print(f"[BOT] STEP 3 Tick OK | sym={actual_sym} bid={tick.bid} ask={tick.ask} delay={staleness_secs:.1f}s")

        # ── STEP 3.5: Chờ Nến M1 Mới (New Bar Filter) ──
        # Tính timestamp nến M1 hiện tại: mỗi nến M1 = 60 giây, làm tròn xuống
        current_candle_time = int(time.time() // 60) * 60  # Unix timestamp đầu nến hiện tại

        if current_candle_time == last_candle_time:
            # Chưa có nến mới — bỏ qua chu kỳ này, chờ đến khi nến đóng
            time.sleep(1)
            continue

        last_candle_time = current_candle_time
        candle_utc_str = datetime.utcfromtimestamp(current_candle_time).strftime('%H:%M')
        print(f"[BOT] STEP 3.5 🕒 Nến M1 Mới | candle_time={candle_utc_str} UTC")

        # ── STEP 4: Kéo Dữ Liệu MT5 ──
        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
        print(f"[BOT] STEP 4 Pull MT5 data | window=120")
        merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=120)
        
        # QUAN TRỌNG: reset flag sau khi cào data đa-sàn
        mt5_manager.current_connected_path = None
        
        if err_msg:
            gui_status = err_msg
            print(f"[BOT] STEP 4 ❌ Dữ liệu lỗi: {err_msg}")
            time.sleep(2)
            continue
        
        if merged_df is None or len(merged_df) == 0:
            gui_status = "Dữ liệu rỗng (Empty DataFrame)"
            print("[BOT] STEP 4 ⚠️ merged_df rỗng!")
            time.sleep(2)
            continue
            
        print(f"[BOT] STEP 4 Dữ liệu OK | rows={len(merged_df)} syms={len(sym_data)}")
        gui_market_data = sorted(sym_data, key=lambda x: x[0])
        
        # ── STEP 5: Feature Pipeline ──
        gui_status = "Chạy Pipeline Giải thuật V2..."
        print("[BOT] STEP 5 DataProcessor.ingest_and_scale...")
        t_seq, p_err = processor.ingest_and_scale(merged_df)
        if p_err:
            gui_status = f"Pipeline Từ Chối: {p_err[:40]}"
            print(f"[BOT] STEP 5 ❌ Pipeline lỗi: {p_err}")
            time.sleep(2)
            continue
        
        print(f"[BOT] STEP 5 ✅ Pipeline xong | tensor_shape={getattr(t_seq, 'shape', 'N/A')}")
            
        # ── STEP 6: Inference ──
        gui_status = "Đang Trích Xuất Lực Cầu (Pytorch)..."
        print("[BOT] STEP 6 Inference Engine predict...")
        pred, logits = engine.predict(t_seq)
        if pred is None:
            gui_status = "Động Cơ Torch Sập (No Preds)"
            print("[BOT] STEP 6 ❌ Inference trả về None!")
            time.sleep(2)
            continue
            
        gui_prediction = f"{pred*100:.2f}%"
        print(f"[BOT] STEP 6 ✅ | LOGITS={logits} | Lực Bò={gui_prediction}")
        
        # ── STEP 7: Re-guard MT5 rồi thực thi lệnh ──
        print("[BOT] STEP 7 Guard MT5 connection trước khi thực thi lệnh...")
        trading_path = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if mt5_manager.current_connected_path != trading_path:
            print(f"[BOT] STEP 7 Re-init MT5 Trading Terminal → {trading_path}")
            trade_manager.mt5.shutdown()
            trade_manager.mt5.initialize(path=trading_path)
            mt5_manager.current_connected_path = trading_path
            
        print(f"[BOT] STEP 7 manage_mt5_positions | sym={actual_sym} pred={pred:.4f}")
        trade_manager.manage_mt5_positions(pred, actual_target_sym=actual_sym)
        gui_status = "Khóa Mốc. Hoàn tất chu kỳ."
        print(f"[BOT] STEP 7 ✅ Hoàn tất chu kỳ #{cycle_count} | action='{trade_manager.gui_action}'")
        
        time.sleep(1)  # Nghỉ ngắn, vòng lặp sẽ tự chờ nến mới ở STEP 3.5

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
