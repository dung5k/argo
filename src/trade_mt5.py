import os
import sys
import time
import subprocess
import threading
import tkinter as tk
import pandas as pd
import numpy as np
import torch
import MetaTrader5 as mt5
from datetime import datetime, timezone

# Import Mạng thần kinh từ file Train
try:
    from src.train_final import CNN_LSTM_Model
except ModuleNotFoundError:
    from train_final import CNN_LSTM_Model

# --- BIẾN TOÀN CỤC CHO GIAO DIỆN (GUI) ---
gui_status = "Đang rà soát Múi Giờ..."
gui_prediction = "Chờ Tín Hiệu..."
gui_time = "00:00:00"
gui_action = "-"
gui_session = "Phiên: Chưa rõ"
# Thêm biến lưu Data Time
gui_forex_time = "FRX: --:--"
gui_crypto_time = "CRY: --:--"
last_mac_run = 0



def log_message(msg):
    try:
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "trade_bot.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass
    print(msg, flush=True)

def get_current_session():
    """Nhận diện Phiên Giao dịch Quốc tế hiện tại theo Giờ UTC"""
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    if 8 <= hour < 13:
        return "european", "ÂU (LONDON)"
    elif 13 <= hour < 22:
        return "us", "MỸ (WALLSTREET)"
    else: 
        return "asian", "Á (TOKYO/SYDNEY)"

def initialize_mt5():
    MT5_MAIN_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=MT5_MAIN_PATH):
        print("❌ LỖI: Không thể khởi tạo Giao diện MetaTrader 5.")
        return False
    return True

def close_mt5_position(position):
    """Đóng khẩn cấp một vị thế MT5 đang sống (Cắt trạng thái hoàn toàn)."""
    symbol = position.symbol
    tick = mt5.symbol_info_tick(symbol)
    
    if position.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": order_type,
        "position": position.ticket, 
        "price": price,
        "deviation": 20,
        "magic": 101010,
        "comment": "AI Close Vị Thế",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False
    return True

def modify_mt5_position(position, sl_pips=50, tp_pips=100):
    """Kéo Trailing Stop Một Chiều (Chỉ kéo SL theo hướng Có Lãi)"""
    symbol = position.symbol
    point = mt5.symbol_info(symbol).point
    tick = mt5.symbol_info_tick(symbol)
    
    current_sl = position.sl
    final_tp = position.tp
    
    if position.type == mt5.ORDER_TYPE_BUY:
        new_sl = tick.ask - sl_pips * 10 * point
        if current_sl == 0.0 or new_sl > current_sl:
            final_sl = new_sl
        else:
            final_sl = current_sl
    else:
        new_sl = tick.bid + sl_pips * 10 * point
        if current_sl == 0.0 or new_sl < current_sl:
            final_sl = new_sl
        else:
            final_sl = current_sl

    if final_sl == current_sl:
        return True

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": position.ticket,
        "sl": float(final_sl),
        "tp": float(final_tp),
        "magic": 101010,
    }
    
    mt5.order_send(request)
    return True

def open_new_mt5_trade(symbol, order_type, lot_size, sl_pips, tp_pips):
    """Mở một vị thế mới hoàn toàn."""
    point = mt5.symbol_info(symbol).point
    tick = mt5.symbol_info_tick(symbol)
    
    if order_type == mt5.ORDER_TYPE_BUY:
        price = tick.ask
        sl = price - sl_pips * 10 * point
        tp = price + tp_pips * 10 * point
    else:
        price = tick.bid
        sl = price + sl_pips * 10 * point
        tp = price - tp_pips * 10 * point
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot_size),
        "type": order_type,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 20,
        "magic": 101010,
        "comment": "AI Entry Order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    mt5.order_send(request)

def manage_mt5_positions(prediction, lot_size=0.01, sl_pips=50, tp_pips=100):
    """Hệ thống Quản lý Vị thế Đa Ngưỡng (Threshold State Machine)"""
    global gui_action
    symbol = "XAUUSD"
    if mt5.symbol_info(symbol) is None:
        return
        
    # BỘ NGƯỠNG ĐIỀU HƯỚNG TẦN SỐ XÁC SUẤT (SOFTMAX CONFIDENCE > 75%)
    BUY_ENTRY_THR = 0.75   
    SELL_ENTRY_THR = 0.25  
    CLOSE_BUY_THR = 0.50   
    CLOSE_SELL_THR = 0.50  
    
    positions = mt5.positions_get(symbol=symbol)
    has_open_position = False
    
    if positions:
        for pos in positions:
            has_open_position = True
            if pos.type == mt5.ORDER_TYPE_BUY:
                if prediction <= CLOSE_BUY_THR:
                    gui_action = f"ĐÃ CHỐT BIÊN BUY ({pos.ticket})"
                    print(f"🚨 ACTION: {gui_action} -> Lực Tăng ({prediction*100:.2f}%) < Ngưỡng Đóng {CLOSE_BUY_THR*100}%")
                    if close_mt5_position(pos):
                        has_open_position = False
                else:
                    gui_action = f"ĐANG KHÓA LÃI BUY ({pos.ticket})"
                    print(f"🛡️ ACTION: {gui_action} -> Lực Tăng Tốt ({prediction*100:.2f}%) >= {CLOSE_BUY_THR*100}%. Dời SL/TP!")
                    modify_mt5_position(pos, sl_pips, tp_pips)
                    
            elif pos.type == mt5.ORDER_TYPE_SELL:
                if prediction >= CLOSE_SELL_THR:
                    gui_action = f"ĐÃ CHỐT BIÊN SELL ({pos.ticket})"
                    print(f"🚨 ACTION: {gui_action} -> Lực Giảm Phục Hồi ({prediction*100:.2f}%) > Ngưỡng Đóng {CLOSE_SELL_THR*100}%")
                    if close_mt5_position(pos):
                        has_open_position = False
                else:
                    gui_action = f"ĐANG KHÓA LÃI SELL ({pos.ticket})"
                    print(f"🛡️ ACTION: {gui_action} -> Lực Giảm Tốt ({prediction*100:.2f}%) <= {CLOSE_SELL_THR*100}%. Dời SL/TP!")
                    modify_mt5_position(pos, sl_pips, tp_pips)

    if not has_open_position:
        if prediction >= BUY_ENTRY_THR:
            gui_action = "🔥 ĐÃ BẮN LỆNH MUA (BUY)!"
            print(f"🚀 ACTION: LỆNH MỞ BUY ĐẨY LÊN MT5 -> Vượt Kháng cự ({prediction*100:.2f}% >= {BUY_ENTRY_THR*100}%)")
            open_new_mt5_trade(symbol, mt5.ORDER_TYPE_BUY, lot_size, sl_pips, tp_pips)
        elif prediction <= SELL_ENTRY_THR:
            gui_action = "🔥 ĐÃ BẮN LỆNH BÁN (SELL)!"
            print(f"🩸 ACTION: LỆNH MỞ SELL ĐẨY LÊN MT5 -> Lủng Hỗ trợ ({prediction*100:.2f}% <= {SELL_ENTRY_THR*100}%)")
            open_new_mt5_trade(symbol, mt5.ORDER_TYPE_SELL, lot_size, sl_pips, tp_pips)
        else:
            gui_action = "Thị trường Lưỡng Lự (Quan Sát)"
            print(f"⚖️ ACTION: KHÔNG VÀO LỆNH -> Tín hiệu kẹt trong Vùng Nhiễu ({SELL_ENTRY_THR*100}% < {prediction*100:.2f}% < {BUY_ENTRY_THR*100}%)")

# --- LUỒNG BOT CHẠY NGẦM ---
def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_action, gui_session, gui_forex_time, gui_crypto_time, last_mac_run
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    features_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\final_features_2d.parquet"
    
    try:
        sample_df = pd.read_parquet(features_path)
        num_features = sample_df.shape[1]
    except Exception as e:
        gui_status = "Lỗi đọc Parquet! Chạy file Lọc Data trước."
        return
        
    # NẠP GEN CHUẨN THẾ HỆ MỚI
    window_size, cnn_filters, lstm_units, lstm_layers, dropout_rate = 60, 16, 128, 2, 0.2
    import json
    genes_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\best_genes.json"
    if os.path.exists(genes_path):
        with open(genes_path, "r", encoding='utf-8') as f:
            genes = json.load(f)
            window_size = genes.get("window_size", 60)
            cnn_filters = genes.get("cnn_filters", 16)
            lstm_units = genes.get("lstm_units", 128)
            lstm_layers = genes.get("lstm_layers", 2)
            dropout_rate = genes.get("dropout_rate", 0.2)
            gui_status = f"✅ Đã Khớp Gen Chống Đạn O(N) Tối Ưu."
            
    model = CNN_LSTM_Model(num_features, cnn_filters=cnn_filters, 
                           lstm_layers=lstm_layers, lstm_units=lstm_units, dropout_rate=dropout_rate).to(device)
    
    if not initialize_mt5():
        gui_status = "Lỗi: Không tìm thấy máy chủ MT5!"
        return
        
    current_loaded_session = ""
    gui_status = "Xong. Chờ nến mới..."
    
    while True:
        now = datetime.now()
        gui_time = now.strftime('%H:%M:%S')
        
        # --- HOT-SWAP MODULE: TỰ ĐỘNG THAY ĐỔI NÃO BỘ THEO MÚI GIỜ ---
        session_id, session_display = get_current_session()
        gui_session = session_display
        
        if session_id != current_loaded_session:
            model_path = rf"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\models\xauusd_{session_id}_weights.pth"
            if os.path.exists(model_path):
                model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
                model.eval()
                current_loaded_session = session_id
                gui_status = f"Đã Nạp Lõi Pytorch Phiên {session_id.upper()}"
            else:
                gui_status = f"⚠️ Lỗi: Không tìm thấy Trọng số Phiên {session_id}. Yêu cầu Training!"
        
        if now.second == 2 or now.second == 3:
            if not current_loaded_session:
                # time.sleep(1)
                continue
                
            gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
            log_message(f"\n[{gui_time}] 🔄 BẮT ĐẦU VÒNG ĐỜI VẮT SỮA DỮ LIỆU TỪ 3 LỤC ĐỊA...")
            script_dir = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"
            python_exe = sys.executable
            
            try:
                my_env = os.environ.copy()
                my_env["PYTHONIOENCODING"] = "utf-8"
                my_env["PYTHONUTF8"] = "1"
                
                # Tăng Timeout lên 60s để Binance mạng lag vẫn tải đủ 10 đồng không bị văng
                # Trạm (1) - Lõi Giao dịch & XAUUSD Data
                res_mt5 = subprocess.run([python_exe, "-X", "utf8", r"src\crawl_mt5.py", "live"], cwd=script_dir, capture_output=True, text=True, encoding='utf-8', env=my_env, timeout=25)
                log_message(f" ├─ Trạm MT5 (1) - XAUUSD/FOREX: {'✅ HOÀN HẢO' if res_mt5.returncode == 0 else f'❌ LỖI VĂNG: {res_mt5.stderr.strip()}'}")
                
                # Trạm (2) - Vệ tinh Data Crypto & Vĩ Mô 
                res_alt = subprocess.run([python_exe, "-X", "utf8", r"src\crawl_mt5_alt.py", "live"], cwd=script_dir, capture_output=True, text=True, encoding='utf-8', env=my_env, timeout=25)
                log_message(f" ├─ Trạm MT5 (2) - Crypto & Vĩ mô: {'✅ TỐC ĐỘ RAM IPC (0.5s)' if res_alt.returncode == 0 else f'❌ LỖI ĐƯỜNG DẪN PATH: Hãy điền đúng Path trong src/crawl_mt5_alt.py'}")
                
                
                # Cập nhật Thời gian Nến Đồng Bộ (Bù trừ về Cột Giờ Địa Phương - Việt Nam UTC+7)
                try:
                    df_mt5 = pd.read_parquet(os.path.join(script_dir, r"data\XAUUSD_1m_2025_2026.parquet"))
                    # Dữ liệu Gốc đã ép về chuẩn UTC+0 => VN là UTC+7
                    local_time = df_mt5.index[-1] + pd.Timedelta(hours=7)
                    gui_forex_time = f"FRX: {local_time.strftime('%H:%M')}"
                except:
                    gui_forex_time = "FRX: LỖI"
                    
                try:
                    df_bin = pd.read_parquet(os.path.join(script_dir, r"data\btc_usdt_1m_2025_2026.parquet"))
                    local_time = df_bin.index[-1] + pd.Timedelta(hours=7)
                    gui_crypto_time = f"CRY: {local_time.strftime('%H:%M')}"
                except:
                    gui_crypto_time = "CRY: LỖI"
                
                
                gui_status = "Ép Ma trận 3D Tensor Pytorch..."
                res_feat = subprocess.run([python_exe, "-X", "utf8", r"src\feature_engineering.py", "live"], cwd=script_dir, capture_output=True, text=True, encoding='utf-8', env=my_env, timeout=60)
                log_message(f" ├─ Lõi Lượng Tử Data (Feature Eng): {'✅ TỔNG HỢP XONG' if res_feat.returncode == 0 else f'❌ LỖI VĂNG SÓNG {res_feat.stderr[:50]}'}")

                df = pd.read_parquet(features_path)
                log_message(f" 📊 KIỂM KÊ KHO: Hầm chứa Parquet đang ngậm đủ {len(df):,} nến.")
                
                last_60_candles = df.iloc[-window_size:].values
                
                if len(last_60_candles) < window_size:
                    gui_status = "Mạng lag, đợi nến 1 phút sau..."
                    print(f" ⚠️ CẢNH BÁO LỰC: Lượng Nến Cắt quá mỏng ({len(last_60_candles)}/{window_size}). AI từ chối uống dòng Máu này!", flush=True)
                    time.sleep(2)
                    continue
                    
                X_tensor = torch.tensor(last_60_candles, dtype=torch.float32).unsqueeze(0).to(device)
                
                gui_status = "Đang trích xuất Lực Cầu (Softmax Confidence)..."
                with torch.no_grad():
                    output = model(X_tensor)
                    probs = torch.softmax(output.data, dim=1).squeeze()
                    
                    # Xác suất Phe Bò (Index 1) và Phe Gấu (Index 0)
                    prob_down, prob_up = probs[0].item(), probs[1].item()
                    prediction = prob_up 
                    
                    gui_prediction = f"{prediction*100:.2f}%"
                    
                    t_min, t_max, t_mean = X_tensor.min().item(), X_tensor.max().item(), X_tensor.mean().item()
                    raw_logits = output.cpu().numpy()[0]
                    
                    # LOGGING THEO YÊU CẦU TRỰC TIẾP
                    print(f"\n[{gui_time}] 🌐 MÔ HÌNH NÃO BỘ TỰ ĐỘNG CHỌN: {session_display} 🌐", flush=True)
                    print(f"👉 INPUT: Tensor Shape {X_tensor.shape}. Min={t_min:.4f}|Max={t_max:.4f}|Mean={t_mean:.4f}. Core Z-Score: {last_60_candles[-1][:5]}...", flush=True)
                    print(f"🧠 DỮ LIỆU LOGITS THÔ (RAW): {raw_logits}. XÁC SUẤT SOFTMAX: {prediction*100:.4f}%", flush=True)
                    
                    # Cổng Điều Hướng Sniper 55/45
                    manage_mt5_positions(prediction, lot_size=0.01, sl_pips=50, tp_pips=100)
                    gui_status = "Đã Khóa Mốc & Trượt Dừng lỗ! Đang ngáy..."
                        
            except Exception as e:
                import traceback
                log_message(f"FATAL EXCEPTION in Bot Loop: {e}\n{traceback.format_exc()}")
                gui_status = "Lỗi Mạng/Khựng Phễu!"
                
            time.sleep(5) 
            
        time.sleep(0.5)

# --- LUỒNG CHÍNH: VẼ BẢNG ĐIỀU KHIỂN NỔI ĐA PHIÊN (MOE DASHBOARD) ---
def update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, lbl_forex, lbl_crypto):
    lbl_time.config(text=f"🕒 {gui_time}")
    lbl_session.config(text=f"🌐 {gui_session}")
    lbl_action.config(text=f"🎯 Hành động: {gui_action}")
    lbl_status.config(text=f"⚙️ {gui_status}")
    
    lbl_forex.config(text=gui_forex_time)
    lbl_crypto.config(text=gui_crypto_time)
    
    try:
        val = float(gui_prediction.replace('%', ''))
        if val >= 55:
            lbl_pred.config(text=f"🧠 BÒ TỚI (TĂNG): {gui_prediction}", fg="#00ffcc") 
        elif val <= 45:
            lbl_pred.config(text=f"🧠 GẤU TỚI (GIẢM): {gui_prediction}", fg="#ff3366") 
        else:
            lbl_pred.config(text=f"🧠 THỜI CƠ LƯỠNG LỰ: {gui_prediction}", fg="#cccccc") 
    except:
        lbl_pred.config(text=f"🧠 THỜI CƠ (Lực): {gui_prediction}", fg="#cccccc")
        
    root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, lbl_forex, lbl_crypto)

def start_overlay_dashboard():
    root = tk.Tk()
    root.title("MoE Terminator Dashboard")
    
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.88) 
    
    screen_w = root.winfo_screenwidth()
    x_pos = screen_w - 340 
    root.geometry(f"320x150+{x_pos}+50")
    root.configure(bg='#121212') 
    
    def start_move(event):
        root.x = event.x
        root.y = event.y
    def stop_move(event):
        root.x = None
        root.y = None
    def do_move(event):
        deltax = event.x - root.x
        deltay = event.y - root.y
        x = root.winfo_x() + deltax
        y = root.winfo_y() + deltay
        root.geometry(f"+{x}+{y}")
        
    root.bind("<ButtonPress-1>", start_move)
    root.bind("<ButtonRelease-1>", stop_move)
    root.bind("<B1-Motion>", do_move)
    
    tk.Label(root, text="🔥 XAUUSD MOE TERMINATOR 🔥", fg="#ffcc00", bg="#121212", font=("Helvetica", 11, "bold")).pack(pady=2)
    
    lbl_session = tk.Label(root, text="🌐 Phiên: Đang đo Đạc...", fg="#cc88ff", bg="#121212", font=("Helvetica", 9, "bold"))
    lbl_session.pack()
    
    lbl_pred = tk.Label(root, text="🧠 THỜI CƠ (Lực): N/A", fg="#cccccc", bg="#121212", font=("Helvetica", 10, "bold"))
    lbl_pred.pack()
    
    lbl_action = tk.Label(root, text="🎯 Hành động: Đang ngủ", fg="#ff9900", bg="#121212", font=("Helvetica", 9))
    lbl_action.pack()
    
    # KHU VỰC BÁO CÁO REAL-TIME DỮ LIỆU
    frame_data = tk.Frame(root, bg="#121212")
    frame_data.pack(fill=tk.X, pady=4, padx=5)
    
    lbl_forex = tk.Label(frame_data, text="FRX: --:--", fg="#00ffff", bg="#121212", font=("Courier", 10, "bold"))
    lbl_forex.pack(side=tk.LEFT, expand=True)
    
    lbl_crypto = tk.Label(frame_data, text="CRY: --:--", fg="#f3ba2f", bg="#121212", font=("Courier", 10, "bold"))
    lbl_crypto.pack(side=tk.LEFT, expand=True)
    
    frame_bottom = tk.Frame(root, bg="#121212")
    frame_bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=2, padx=5)
    
    lbl_time = tk.Label(frame_bottom, text="🕒 00:00:00", fg="white", bg="#121212", font=("Helvetica", 8))
    lbl_time.pack(side=tk.LEFT)
    
    lbl_status = tk.Label(frame_bottom, text="⚙️ Booting...", fg="#888888", bg="#121212", font=("Helvetica", 8))
    lbl_status.pack(side=tk.RIGHT)
    
    bot_thread = threading.Thread(target=bot_background_loop, daemon=True)
    bot_thread.start()
    
    update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, lbl_forex, lbl_crypto)
    root.mainloop()

if __name__ == "__main__":
    start_overlay_dashboard()
