import os
import sys
import io
import time
import json
import threading

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
        try: tg_bot.send_message(tg_chat_id, msg)
        except: pass

def tg_notify(msg):
    global tg_brain_count
    
    # 1. Đoạn đầu khởi động và Cảnh báo
    force_tg_kws = ["KHỞI ĐỘNG", "Khởi động", "ĐÃ BẮN LỆNH", "CHỐT", "ĐẢO CHIỀU", "❌", "⚠️", "✅"]
    if any(k in msg for k in force_tg_kws):
        _send_raw_tg(msg)
        return

    tm = globals().get('trade_manager')
    g_probs = globals().get('gui_probs')
    cfg = globals().get('CONFIG', {})

    # 4. Trong khi có lệnh
    has_position = False
    if tm and hasattr(tm, 'active_trade_loggers') and len(tm.active_trade_loggers) > 0:
        has_position = True

    if has_position:
        _send_raw_tg(msg)
        return

    # 3. Khi giá gần đến ngưỡng vào lệnh (>= 80% ngưỡng)
    is_close_to_thr = False
    if g_probs and cfg:
        prob_thr = cfg.get("LIVE_BOT", {}).get("MIN_PROBABILITY_THRESH", 0.50)
        near_thr = prob_thr * 0.8
        if g_probs.get('buy', 0.0) >= near_thr or g_probs.get('sell', 0.0) >= near_thr:
            is_close_to_thr = True

    if is_close_to_thr:
        _send_raw_tg(msg)
        return

    # 2. 3 kết quả đầu tiên của bộ não
    if "PIPELINE DỰ ĐOÁN" in msg or "Tỷ lệ Cược" in msg:
        if tg_brain_count < 3:
            _send_raw_tg(msg)
            tg_brain_count += 1
        return
        
    # Chặn đứng các nội dung khác (ví dụ: liên tục báo HOLD vô nghĩa)
    pass

config_file = os.path.join(safe_script_dir, "workspaces", "CFG_XAU_NY_V3_5", "base_config.json")
schedule_file = os.path.join(safe_script_dir, "workspaces", "shared_meta", "bot_v3_brain_schedule.json")
if len(sys.argv) > 1:
    args_json = [arg for arg in sys.argv if arg.endswith('.json')]
    if len(args_json) >= 1:
        config_file = args_json[0]
    if len(args_json) >= 2:
        schedule_file = args_json[1]

# Khởi tạo Config Loader
config_loader = V3ConfigLoader(config_file, schedule_file, log_callback=print)
CONFIG = config_loader.load_base_config()

TARGET_SYMBOL = CONFIG.get("TARGET_SYMBOL", "XAUUSD")
TARGET_PREFIX = CONFIG.get("TARGET_PREFIX", "XAUUSD")

TRADE_PLATFORM = CONFIG.get("LIVE_BOT", {}).get("TRADE_PLATFORM", "MT5")

if TRADE_PLATFORM == "BINANCE":
    trade_manager = BinanceTradeManagerV3(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)
else:
    trade_manager = V3TradeManager(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)

gui_status = "Đang Sưởi Ấm Radar V3..."
gui_prediction = "Chờ Tín Hiệu..."
gui_probs = {'buy': 0.0, 'sell': 0.0, 'loss': 0.0}
gui_time = "00:00:00"
gui_session = "Phiên: Đang khởi chạy..."
gui_market_data = []

def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_session, gui_market_data, CONFIG, gui_probs
    print("[BOT V3] ===== Khởi động OOP Modules V3.0 (MASTER SCHEDULER) =====")
    
    engine = V3InferenceEngine(log_callback=print)
    mt5_manager = MT5DataManager(log_callback=print, target_sym=TARGET_SYMBOL, config_path=config_file)
    
    if TRADE_PLATFORM == "BINANCE":
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
    startup_msg = f"🤖 [BOT V3 MASTER KHỞI ĐỘNG]\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n💹 Mã: {TARGET_SYMBOL} | Config: {os.path.basename(config_file)}"
    tg_notify(startup_msg)

    while True:
        cycle_count += 1
        gui_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n[BOT V3] ────── Chu kỳ #{cycle_count} | {gui_time} ──────")
        
        # 1. Hot-reload Config & Schedule
        base_cfg = config_loader.load_base_config()
        if base_cfg:
            CONFIG = base_cfg
            
        sess_name, sinfo, global_mt5 = config_loader.get_current_schedule()
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
                processor = V3DataProcessor(s_path, i_feats, window_size, config=CONFIG, log_callback=print)
                mt5_manager.force_reload_dynamic_features(i_feats)
                
                brain_loaded = True
                gui_status = "✅ Lắp Ráp NÃO V3 Thành Công!"
                gui_session = f"PHIÊN {sess_name.upper() if sess_name else 'UNKNOWN'} (Não: {os.path.basename(m_path)[:10]})"
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
        mt5.symbol_select(actual_sym, True)
        
        tick = mt5.symbol_info_tick(actual_sym)
        if tick is None:
            if time.time() - last_tick_err_time > 10:
                print(f"[BOT V3] ⚠️ LỖI TICK: {actual_sym} = None! Reconnect...")
                last_tick_err_time = time.time()
            mt5_manager.current_connected_path = None
            time.sleep(1)
            continue
            
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
        msg_pred = f"🎯 ĐÃ KẾT THÚC PIPELINE DỰ ĐOÁN:\nThời gian: Nến {gui_time}\nGiá trị Loss hiện tại: {mse:.4f} (Threshold: {engine.mse_threshold:.4f})\nTỷ lệ Cược: BUY={probs['buy']:.2%} | SELL={probs['sell']:.2%}\nHành động: {action}"
        print(f"[BOT V3] {msg_pred}")
        # Gửi output hiện tại của mô hình qua Telegram (theo yêu cầu của user)
        # Để tránh spam, sẽ chỉ gửi nếu tín hiệu vượt kỳ vọng (Loss nhỏ) hoặc Action = BUY/SELL
        if action != "SLEEP":
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
    lbl_session = tk.Label(root, text="🌐 Phiên: Đang khởi chạy", fg="#aa66ff", bg="#080b12", font=("Consolas", 9))
    lbl_session.pack()
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
