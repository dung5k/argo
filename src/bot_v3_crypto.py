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

safe_script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.bot_v3.cloud_manager_v3 import V3CloudManager
from src.bot_v3.data_processor_v3 import V3DataProcessor
from src.bot_v3.inference_engine_v3 import V3InferenceEngine
from src.bot_v3.binance_trade_manager_v3 import BinanceTradeManagerV3
from src.core.mt5_data_manager import MT5DataManager
from src.bot_v3.config_loader_v3 import V3ConfigLoader
import logging

log_dir = os.path.join(safe_script_dir, "data", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"trade_bot_v3_crypto_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log")
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

config_file = os.path.join(safe_script_dir, "data", "bot_config_ltc_crypto_v3_5.json")
schedule_file = os.path.join(safe_script_dir, "data", "bot_v3_brain_schedule.json")
if len(sys.argv) > 1:
    args_json = [arg for arg in sys.argv if arg.endswith('.json')]
    if len(args_json) >= 1:
        config_file = args_json[0]
    if len(args_json) >= 2:
        schedule_file = args_json[1]

# Khởi tạo Config Loader
config_loader = V3ConfigLoader(config_file, schedule_file, log_callback=print)
CONFIG = config_loader.load_base_config()

TARGET_SYMBOL = CONFIG.get("TARGET_SYMBOL", "LTCUSDT")
TARGET_PREFIX = CONFIG.get("TARGET_PREFIX", "LTC")

trade_manager = BinanceTradeManagerV3(TARGET_SYMBOL, CONFIG, tg_notify_callback=tg_notify, log_callback=print)

gui_status = "Đang Sưởi Ấm Radar Binance..."
gui_prediction = "Chờ Tín Hiệu..."
gui_time = "00:00:00"
gui_session = "Phiên: Crypto 24/7"
gui_market_data = []

def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_session, gui_market_data, CONFIG
    print("[BOT V3 CRYPTO] ===== Khởi động Binance V3.5 =====")
    
    engine = V3InferenceEngine(log_callback=print)
    mt5_manager = MT5DataManager(log_callback=print, target_sym=TARGET_SYMBOL, config_path=config_file)
    
    processor = None
    cloud = None
    
    arch = CONFIG.get("TRAINING", {})
    window_size     = CONFIG.get("FEATURE_ENGINEERING", {}).get("WINDOW_SIZE", 20)
    d_model         = arch.get("D_MODEL", 128)
    nhead           = arch.get("N_HEAD", 8)
    num_attn_layers = arch.get("NUM_LAYERS", 4)
    
    gui_status = "Đang kết nối Binance FAPI..."
    if not trade_manager.init_client():
        gui_status = "❌ Khởi tạo Binance CCXT thất bại!"
        print("[BOT V3 CRYPTO] ❌ FATAL: Không thể khởi tạo Binance FAPI. Kiểm tra Key.")
        return
        
    brain_loaded = False
    active_run_id = None
    cycle_count = 0
    last_candle_time = None
    
    trade_manager.sync_existing_positions()
    startup_msg = f"🤖 [BINANCE V3 KHỞI ĐỘNG]\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n💹 Mã: {TARGET_SYMBOL} | Config: {os.path.basename(config_file)}"
    tg_notify(startup_msg)

    while True:
        cycle_count += 1
        gui_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n[BINANCE V3] ────── Chu kỳ #{cycle_count} | {gui_time} ──────")
        
        # 1. Hot-reload Config (Khong dung Schedule cho Crypto 24/7)
        base_cfg = config_loader.load_base_config()
        if base_cfg:
            CONFIG = base_cfg
            
        trade_manager.config = CONFIG
        mt5_manager.config = CONFIG
        trade_manager.update_gui_threshold()
        
        bot_cfg = CONFIG.get("LIVE_BOT", {})
        engine.mse_threshold = bot_cfg.get("MSE_THRESHOLD_PERCENTILE", 70.0)
        engine.prob_threshold = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.70)
            
        target_run_id = CONFIG.get("HF_RUN_ID", "")
        cfg_id = CONFIG.get("CONFIG_ID", "")

        if target_run_id and target_run_id != active_run_id:
            msg = f"🔄 Chuyển đổi Não!\nĐang tiến hành tải Não [{target_run_id}]..."
            print(f"[BINANCE V3] {msg}")
            tg_notify(msg)
            brain_loaded = False
            cloud = V3CloudManager(TARGET_SYMBOL, TARGET_PREFIX, "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", CONFIG, log_callback=print)
            
        if not brain_loaded and cloud is not None:
            print(f"[BINANCE V3] Bắt đầu tải não AAMT...")
            gui_status = "Đang Tải NÃO từ Cloud..."
            try:
                m_path, s_path, i_feats, n_feat = cloud.sync_session_model(cfg_id)
                active_run_id = target_run_id
                
                engine.load_weights(m_path, n_feat, d_model, nhead, num_attn_layers, window_size)
                processor = V3DataProcessor(s_path, i_feats, window_size, config=CONFIG, log_callback=print)
                mt5_manager.force_reload_dynamic_features(i_feats)
                
                brain_loaded = True
                gui_status = "✅ Lắp Ráp NÃO V3 Thành Công!"
                gui_session = f"CRYPTO 24/7 (Não: {os.path.basename(m_path)[:10]})"
                msg_done = f"✅ Lắp ráp NÃO Crypto Xong!\nKhởi tạo thành công Mạng Nơ-ron (Loss %: {bot_cfg.get('MSE_THRESHOLD_PERCENTILE', 70)})\nBot đang nghe ngóng Binance..."
                print(f"[BINANCE V3] {msg_done}")
                tg_notify(msg_done)
            except Exception as ce:
                gui_status = f"❌ Lỗi Thay Não: {str(ce)[:30]}"
                print(f"[BINANCE V3] ❌ Lỗi tải não: {ce}")
                time.sleep(5)
                continue
                
        if not brain_loaded:
            print("[BINANCE V3] Chưa có Bộ Não nào được cấu hình hợ lệ. Đợi 5s...")
            time.sleep(5)
            continue
            
        print("[BINANCE V3] Quét dữ liệu từ Binance và MT5 (Vĩ mô)...")
        mt5_manager.scan_terminals_and_map()
        
        current_candle_time = int(time.time() // 60) * 60
        if current_candle_time == last_candle_time:
            time.sleep(1)
            continue
            
        last_candle_time = current_candle_time
        print(f"[BINANCE V3] 🕒 Nến M1 Mới | {datetime.fromtimestamp(current_candle_time, timezone.utc).strftime('%H:%M')} UTC")

        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
        merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=max(window_size + 50, 120))
        
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
        msg_pred = f"🎯 ĐÃ KẾT THÚC PIPELINE DỰ ĐOÁN BINANCE:\nThời gian: Nến {gui_time}\nGiá trị Loss hiện tại: {mse:.4f} (Threshold: {engine.mse_threshold:.4f})\nTỷ lệ Cược: BUY={probs['buy']:.2%} | SELL={probs['sell']:.2%}\nHành động: {action}"
        print(f"[BINANCE V3] {msg_pred}")
        if action != "SLEEP":
            tg_notify(msg_pred)
            
        trade_manager.manage_positions(action, probs, mse)
        gui_status = f"Khóa Mốc. Hành động: {action}"
        time.sleep(1)

def update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target=None):
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
    
    lbl_pred.config(text=f"🧠 Tín Hiệu: {gui_prediction}", fg="#00ffcc" if "B" in gui_prediction else "#cccccc")
    root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target)

def start_overlay_dashboard():
    root = tk.Tk()
    root.title(f"AAMT CRYPTO TERMINATOR V3 - {TARGET_SYMBOL}")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.95) 
    
    screen_h = root.winfo_screenheight()
    screen_w = root.winfo_screenwidth()
    root.geometry(f"360x450+{screen_w - 380}+{screen_h - 500}") # Đặt góc phải cho Bot Crypto
    root.configure(bg='#1c100b') # Màu nền thiên cam (Binance theme)
    
    root.x, root.y = 0, 0
    def do_move(event):
        if root.x is None or root.y is None: return
        root.geometry(f"+{root.winfo_x() + event.x - root.x}+{root.winfo_y() + event.y - root.y}")
        
    root.bind("<ButtonPress-1>", lambda e: setattr(root, 'x', e.x) or setattr(root, 'y', e.y))
    root.bind("<ButtonRelease-1>", lambda e: setattr(root, 'x', None) or setattr(root, 'y', None))
    root.bind("<B1-Motion>", do_move)
    
    tk.Label(root, text=f"🔶 {TARGET_SYMBOL} BINANCE V3.5 🔶", fg="#f3ba2f", bg="#1c100b", font=("Consolas", 11, "bold")).pack(pady=5)
    lbl_session = tk.Label(root, text="🌐 Phiên: Đang khởi chạy", fg="#aa66ff", bg="#1c100b", font=("Consolas", 9))
    lbl_session.pack()
    lbl_pred = tk.Label(root, text="🧠 THỜI CƠ: N/A", fg="#cccccc", bg="#1c100b", font=("Consolas", 10, "bold"))
    lbl_pred.pack(pady=3)
    lbl_action = tk.Label(root, text="🎯 Chiến thuật: Đang ngủ", fg="#ffcc00", bg="#1c100b", font=("Consolas", 9))
    lbl_action.pack()
    lbl_thr = tk.Label(root, text="⚖️ Ngưỡng L4: Chờ Load", fg="#ff55bb", bg="#1c100b", font=("Consolas", 9))
    lbl_thr.pack()
    
    from tkinter import ttk
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#2b1a13", foreground="white", fieldbackground="#2b1a13", borderwidth=0)
    style.configure("Treeview.Heading", background="#3e251a", foreground="#f3ba2f", font=("Consolas", 8, "bold"))
    
    frame_data = tk.Frame(root, bg="#1c100b")
    frame_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    tree = ttk.Treeview(frame_data, columns=("Symbol", "Price", "Change", "Time"), show="headings", height=8)
    tree.heading("Symbol", text="Mã")
    tree.heading("Price", text="Giá")
    tree.heading("Change", text="Biến Động")
    tree.heading("Time", text="Giờ")
    for c, w in zip(("Symbol", "Price", "Change", "Time"), (80, 65, 65, 60)): tree.column(c, width=w, anchor="e" if c != "Symbol" else "w")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    lbl_status = tk.Label(root, text="⚙️ Đang Khởi Đoạt Mạng", fg="#aaaaaa", bg="#1c100b", font=("Consolas", 8))
    lbl_status.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
    lbl_time = tk.Label(root, text="🕒 00:00:00", fg="#f3ba2f", bg="#1c100b", font=("Consolas", 8, "bold"))
    lbl_time.pack(side=tk.BOTTOM)
    
    update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr)
    root.mainloop()

if __name__ == "__main__":
    t = threading.Thread(target=bot_background_loop)
    t.daemon = True
    t.start()
    start_overlay_dashboard()
