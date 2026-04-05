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
    from src.train_ga import TransformerModel
except ModuleNotFoundError:
    from train_ga import TransformerModel

import json

config_file = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\bot_config.json"
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.endswith('.json'):
            config_file = arg

TARGET_SYMBOL = "XAUUSD"
TARGET_PREFIX = "XAU_USD"
WEIGHT_FILE = "xauusd_unified_weights.pth"
CRAWL_SCRIPT = "crawl_mt5.py"
CONFIG = {}

if os.path.exists(config_file):
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
            TARGET_SYMBOL = CONFIG.get("TARGET_SYMBOL", "XAUUSD")
            TARGET_PREFIX = CONFIG.get("TARGET_PREFIX", "XAU_USD")
            WEIGHT_FILE = CONFIG.get("WEIGHT_FILE", "xauusd_unified_weights.pth")
            CRAWL_SCRIPT = CONFIG.get("CRAWL_SCRIPT", "crawl_mt5.py")
    except: pass

# --- BIẾN TOÀN CỤC CHO GIAO DIỆN (GUI) ---
gui_status = "Đang rà soát Múi Giờ..."
gui_prediction = "Chờ Tín Hiệu..."
gui_time = "00:00:00"
gui_action = "-"
gui_session = "Phiên: Chưa rõ"
gui_thr_text = "⚖️ Ngưỡng L4: Đang Tải..."
gui_market_data = []  # Lưu list của tuple (Symbol, Price, Change)
last_mac_run = 0

# --- THEO DÕI LOG TỪNG LỆNH ---
active_trade_loggers = {}

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
    # Sử dụng Đường dẫn MT5 từ config truyền vào, mặc định là MT5 Chính
    MT5_MAIN_PATH = CONFIG.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
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
    
    global active_trade_loggers
    if position.ticket in active_trade_loggers:
        try:
            with open(active_trade_loggers[position.ticket]["log_file"], "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] 🛠️ ĐÃ DỜI SL THÀNH CÔNG: SL Mới = {final_sl}\n")
        except:
            pass

    return True

def update_active_trade_loggers():
    global active_trade_loggers
    if not active_trade_loggers:
        return
        
    tick = mt5.symbol_info_tick(TARGET_SYMBOL)
    if tick is None: return
        
    now = datetime.now()
    now_str = now.strftime('%H:%M:%S')
    tickets_to_remove = []
    
    for ticket, state in active_trade_loggers.items():
        log_file = state["log_file"]
        pos = mt5.positions_get(ticket=ticket)
        is_open = True if (pos and len(pos) > 0) else False
        
        try:
            if is_open:
                diff_str = "N/A"
                if "entry_price" in state:
                    if state.get("order_type") == "BUY":
                        diff = tick.bid - state["entry_price"]
                    else:
                        diff = state["entry_price"] - tick.ask
                    diff_str = f"{diff:+.2f}$"
                    state["last_diff"] = diff_str
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{now_str}] TRACING: Bid={tick.bid} | Ask={tick.ask} | Giá trị Hợp đồng: {diff_str}\n")
            else:
                if state["status"] == "OPEN":
                    state["status"] = "CLOSED_MONITORING"
                    state["close_time"] = time.time()
                    reason = state.get("close_reason", "Chạm lệnh SL/TP (Thị trường) hoặc Cắt Tay trực tiếp")
                    final_pnl = state.get("last_diff", "N/A")
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"[{now_str}] 🔒 LỆNH ĐÃ ĐÓNG (Nguyên nhân: {reason}) | TỔNG KẾT PnL: Lãi/Lỗ {final_pnl}\n")
                        f.write(f"[{now_str}] VÀO GIAI ĐOẠN 5 PHÚT GIÁM SÁT HẬU KỲ...\n")
                elif state["status"] == "CLOSED_MONITORING":
                    elapsed = time.time() - state["close_time"]
                    if elapsed >= 300:
                        with open(log_file, "a", encoding="utf-8") as f:
                            f.write(f"[{now_str}] 🛑 KẾT THÚC 5 PHÚT GIÁM SÁT HẬU KỲ. ĐÓNG LOG.\n")
                        tickets_to_remove.append(ticket)
                    else:
                        with open(log_file, "a", encoding="utf-8") as f:
                            f.write(f"[{now_str}] POST-CLOSE (+{int(elapsed)}s): Bid={tick.bid} | Ask={tick.ask}\n")
        except:
            pass
            
    for t in tickets_to_remove:
        del active_trade_loggers[t]

def open_new_mt5_trade(symbol, order_type, lot_size, sl_pips, tp_pips, prediction):
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
    
    result = mt5.order_send(request)
    
    global active_trade_loggers
    if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
        ticket = result.order
        
        # Tạo file log theo dõi lệnh này
        log_dir = os.path.join(os.getcwd(), "logs", "trades")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"trade_{ticket}_{datetime.now().strftime('%H%M%S')}.log")
        
        active_trade_loggers[ticket] = {
            "status": "OPEN",
            "log_file": log_file,
            "close_time": None,
            "entry_price": float(request['price']),
            "order_type": "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL",
            "close_reason": "UNKNOWN"
        }
        
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"--- BÁO CÁO VÀO LỆNH (TICKET: {ticket}) ---\n")
                f.write(f"Thời gian mở: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Loại lệnh: {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'}\n")
                f.write(f"AI Lực Khuyến Nghị (Prediction): {prediction*100:.2f}%\n")
                f.write(f"Khối lượng: {lot_size}\n")
                f.write(f"Entry Price: {request['price']}\n")
                f.write(f"SL Đặt: {request['sl']}\n")
                f.write(f"TP Đặt: {request['tp']}\n")
                f.write(f"--- BẮT ĐẦU THEO DÕI TRACING TICK ---\n")
        except:
            pass
        return ticket
    else:
        err = getattr(result, 'comment', 'Unknown Error') if result else 'Request Null'
        print(f"Lỗi MT5 Bắn Lệnh: {err}")
        return None

def manage_mt5_positions(prediction, lot_size=0.01, sl_pips=50, tp_pips=100):
    """Hệ thống Quản lý Vị thế Đa Ngưỡng (Threshold State Machine)"""
    global gui_action, gui_thr_text
    symbol = TARGET_SYMBOL
    if mt5.symbol_info(symbol) is None:
        return
        
    import json
    import os
    config_file = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\bot_config.json"
    
    BUY_ENTRY_THR  = 0.60
    SELL_ENTRY_THR = 0.40
    CLOSE_BUY_THR  = 0.50
    CLOSE_SELL_THR = 0.50
    # Cấu hình tĩnh ban đầu từ tham số hàm
    cfg_lot_size = lot_size
    cfg_sl_pips = sl_pips
    cfg_tp_pips = tp_pips
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                BUY_ENTRY_THR  = cfg.get("BUY_ENTRY_THR", BUY_ENTRY_THR)
                SELL_ENTRY_THR = cfg.get("SELL_ENTRY_THR", SELL_ENTRY_THR)
                CLOSE_BUY_THR  = cfg.get("CLOSE_BUY_THR", CLOSE_BUY_THR)
                CLOSE_SELL_THR = cfg.get("CLOSE_SELL_THR", CLOSE_SELL_THR)
                cfg_lot_size = cfg.get("lot_size", cfg_lot_size)
                cfg_sl_pips = cfg.get("sl_pips", cfg_sl_pips)
                cfg_tp_pips = cfg.get("tp_pips", cfg_tp_pips)
    except Exception as e:
        pass
        
    gui_thr_text = f"⚖️ Ngưỡng: BUY>{int(BUY_ENTRY_THR*100)}% | SELL<{int(SELL_ENTRY_THR*100)}%"
    
    positions = mt5.positions_get(symbol=symbol)
    has_open_position = False
    
    if positions:
        for pos in positions:
            has_open_position = True
            if pos.type == mt5.ORDER_TYPE_BUY:
                if prediction <= CLOSE_BUY_THR:
                    gui_action = f"ĐÃ CHỐT BIÊN BUY ({pos.ticket})"
                    print(f"🚨 ACTION: {gui_action} -> Lực Tăng ({prediction*100:.2f}%) < Ngưỡng Đóng {CLOSE_BUY_THR*100}%")
                    if pos.ticket in active_trade_loggers:
                        active_trade_loggers[pos.ticket]["close_reason"] = "Đóng Kỹ Thuật Bằng Lệnh Thoát Trái Tuyến Tính (Do AI nhận thấy tín hiệu Đảo chiều Xấu)"
                    if close_mt5_position(pos):
                        has_open_position = False
                else:
                    gui_action = f"ĐANG KHÓA LÃI BUY ({pos.ticket})"
                    print(f"🛡️ ACTION: {gui_action} -> Lực Tăng Tốt ({prediction*100:.2f}%) >= {CLOSE_BUY_THR*100}%. Dời SL/TP!")
                    modify_mt5_position(pos, cfg_sl_pips, cfg_tp_pips)
                    
            elif pos.type == mt5.ORDER_TYPE_SELL:
                if prediction >= CLOSE_SELL_THR:
                    gui_action = f"ĐÃ CHỐT BIÊN SELL ({pos.ticket})"
                    print(f"🚨 ACTION: {gui_action} -> Lực Giảm Phục Hồi ({prediction*100:.2f}%) > Ngưỡng Đóng {CLOSE_SELL_THR*100}%")
                    if pos.ticket in active_trade_loggers:
                        active_trade_loggers[pos.ticket]["close_reason"] = "Đóng Kỹ Thuật Bằng Lệnh Thoát Trái Tuyến Tính (Do AI nhận thấy tín hiệu Đảo chiều Xấu)"
                    if close_mt5_position(pos):
                        has_open_position = False
                else:
                    gui_action = f"ĐANG KHÓA LÃI SELL ({pos.ticket})"
                    print(f"🛡️ ACTION: {gui_action} -> Lực Giảm Tốt ({prediction*100:.2f}%) <= {CLOSE_SELL_THR*100}%. Dời SL/TP!")
                    modify_mt5_position(pos, cfg_sl_pips, cfg_tp_pips)

    if not has_open_position:
        if prediction >= BUY_ENTRY_THR:
            gui_action = "🔥 ĐÃ BẮN LỆNH MUA (BUY)!"
            print(f"🚀 ACTION: LỆNH MỞ BUY ĐẨY LÊN MT5 -> Vượt Kháng cự ({prediction*100:.2f}% >= {BUY_ENTRY_THR*100}%)")
            open_new_mt5_trade(symbol, mt5.ORDER_TYPE_BUY, cfg_lot_size, cfg_sl_pips, cfg_tp_pips, prediction)
        elif prediction <= SELL_ENTRY_THR:
            gui_action = "🔥 ĐÃ BẮN LỆNH BÁN (SELL)!"
            print(f"🩸 ACTION: LỆNH MỞ SELL ĐẨY LÊN MT5 -> Lủng Hỗ trợ ({prediction*100:.2f}% <= {SELL_ENTRY_THR*100}%)")
            open_new_mt5_trade(symbol, mt5.ORDER_TYPE_SELL, cfg_lot_size, cfg_sl_pips, cfg_tp_pips, prediction)
        else:
            gui_action = "Thị trường Lưỡng Lự (Quan Sát)"
            print(f"⚖️ ACTION: KHÔNG VÀO LỆNH -> Tín hiệu kẹt trong Vùng Nhiễu ({SELL_ENTRY_THR*100}% < {prediction*100:.2f}% < {BUY_ENTRY_THR*100}%)")

# --- LUỒNG BOT CHẠY NGẦM ---
def bot_background_loop():
    global gui_status, gui_prediction, gui_time, gui_action, gui_session, gui_forex_time, gui_crypto_time, last_mac_run
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    features_path = rf"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\final_features_{TARGET_PREFIX}.parquet"
    
    try:
        sample_df = pd.read_parquet(features_path)
        num_features = sample_df.shape[1]
    except Exception as e:
        gui_status = "Lỗi đọc Parquet! Chạy file Lọc Data trước."
        return
        
    # Load genes (hyperparams) from best_genes.json
    import json
    genes_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\best_genes.json"
    genes = {"window_size": 30, "lstm_units": 128, "lstm_layers": 2, "dropout_rate": 0.25}
    if os.path.exists(genes_path):
        with open(genes_path, "r", encoding='utf-8') as f:
            genes = json.load(f)
    window_size     = genes.get("window_size", 30)
    d_model         = genes.get("lstm_units", 128)
    nhead           = 4
    num_attn_layers = genes.get("lstm_layers", 2)
    dropout_rate    = genes.get("dropout_rate", 0.25)
    gui_status = f"Genes loaded: win={window_size}, d={d_model}"
    log_message(f"[BOT] Genes: {genes}")

    # Load num_xau_features if available
    meta_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\feature_meta.json"
    num_xau_features = None
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding='utf-8') as mf:
            meta = json.load(mf)
            num_xau_features = meta.get("num_xau_features", None)

    model = TransformerModel(
        num_features=num_features, d_model=d_model, nhead=nhead,
        num_layers=num_attn_layers, dropout_rate=dropout_rate,
        num_xau_features=num_xau_features
    ).to(device)
    log_message(f"[BOT] TransformerModel d={d_model}, heads={nhead}, layers={num_attn_layers}, win={window_size}")
    
    log_message("[BOT] Bắt đầu kết nối MT5 initialization...")
    if not initialize_mt5():
        gui_status = "Lỗi: Không tìm thấy máy chủ MT5!"
        log_message("[BOT] ❌ FATAL ERROR: mt5.initialize trả về False!")
        return
    log_message("[BOT] ✅ Kết nối MT5 thành công!")
        
    current_loaded_session = ""
    gui_status = "Xong. Chờ nến mới..."
    
    while True:
        now = datetime.now()
        gui_time = now.strftime('%H:%M:%S')
        
        # --- HOT-SWAP MODULE: TỰ ĐỘNG THAY ĐỔI NÃO BỘ THEO MÚI GIỜ ---
        session_id, session_display = get_current_session()
        gui_session = session_display
        
        if session_id != current_loaded_session:
            log_message(f"[BOT] Thay đổi Phiên: {session_id}. Đang load model...")
            # Ưu tiên load WEIGHT_FILE từ folder runs, nếu không có thì tìm trong models, hoặc báo lỗi
            from pathlib import Path
            runs_dir = Path(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs")
            found_models = list(runs_dir.rglob(WEIGHT_FILE))
            runs_model_path = str(max(found_models, key=os.path.getctime)) if found_models else ""
            old_model_path = os.path.join(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\models", f"{TARGET_SYMBOL.lower()}_{session_id}_weights.pth")
            
            if os.path.exists(runs_model_path):
                log_message(f"[BOT] Đang load model từ file {runs_model_path}")
                model.load_state_dict(torch.load(runs_model_path, map_location=device, weights_only=True))
                model.eval()
                current_loaded_session = session_id
                gui_status = f"Đã Nạp Trọng Số Chung {WEIGHT_FILE}"
                log_message(f"[BOT] Nạp thành công {WEIGHT_FILE}")
            elif os.path.exists(old_model_path):
                log_message(f"[BOT] Đang load model từ file {old_model_path}")
                model.load_state_dict(torch.load(old_model_path, map_location=device, weights_only=True))
                model.eval()
                current_loaded_session = session_id
                gui_status = f"Đã Nạp Lõi Pytorch Phiên {session_id.upper()}"
                log_message(f"[BOT] Nạp thành công {old_model_path}")
            else:
                gui_status = f"⚠️ Lỗi: Không tìm thấy file trọng số {WEIGHT_FILE}!"
                log_message(f"[BOT] LỖI THIẾU MODEL: {WEIGHT_FILE}")
        
        if not current_loaded_session:
            time.sleep(1)
            continue
            
        # --- 1. SESSION GUARD: STALE PRICE CHECK ---
        tick = mt5.symbol_info_tick(TARGET_SYMBOL)
        if tick is None:
            time.sleep(1)
            continue
            
        staleness_seconds = time.time() - tick.time
        if staleness_seconds > 300: # 5 minutes
            gui_status = f"Giá ngưng đọng ({int(staleness_seconds/60)}p). Chờ..."
            log_message(f"[{gui_time}] 🔴 [SESSION GUARD] Giá bị Frozen/Stale. Từ chối Crawl/Trade.")
            time.sleep(10)
            continue
            
        # --- 2. SESSION GUARD: MARKET HOURS CHECK ---
        session_guard_enabled = CONFIG.get("SESSION_GUARD_ENABLED", False)
        block_trading = False
        force_close = False
        
        if session_guard_enabled:
            tick_dt = datetime.utcfromtimestamp(tick.time)
            market_open = CONFIG.get("MARKET_OPEN", "01:00")
            market_close = CONFIG.get("MARKET_CLOSE", "23:55")
            
            h_open, m_open = map(int, market_open.split(':'))
            h_close, m_close = map(int, market_close.split(':'))
            
            curr_min = tick_dt.hour * 60 + tick_dt.minute
            open_min = h_open * 60 + m_open
            close_min = h_close * 60 + m_close
            
            if open_min <= curr_min < open_min + 30:
                block_trading = True
            elif close_min - 30 <= curr_min < close_min:
                block_trading = True
                
            if close_min - 15 <= curr_min < close_min:
                force_close = True
                
            if curr_min >= close_min or curr_min < open_min:
                block_trading = True
                
        if force_close:
            log_message(f"[{gui_time}] ⚠️ [SESSION GUARD] ÉP BUỘC CẮT LỆNH CUỐI PHIÊN!")
            for ticket in list(active_trade_loggers.keys()):
                pos = mt5.positions_get(ticket=ticket)
                if pos and len(pos) > 0:
                    close_mt5_position(pos[0])
                    active_trade_loggers[ticket]["close_reason"] = "Force Close (End of Session)"
                    
        if block_trading:
            gui_status = "Đang Khóa Phiên Giao Dịch"
            log_message(f"[{gui_time}] 🚧 [SESSION GUARD] Khung giờ cấm giao dịch. Bỏ qua Vòng lặp.")
            time.sleep(30)
            continue
            
        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực..."
        if True:
            log_message(f"\n[{gui_time}] 🔄 BẮT ĐẦU VÒNG ĐỜI VẮT SỮA DỮ LIỆU TỪ 3 LỤC ĐỊA...")
            script_dir = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"
            python_exe = sys.executable
            
            try:
                my_env = os.environ.copy()
                my_env["PYTHONIOENCODING"] = "utf-8"
                my_env["PYTHONUTF8"] = "1"
                
                # Trạm thu thập dữ liệu (Gọi file theo CRAWL_SCRIPT)
                t0_alt = time.time()
                res_alt = subprocess.run([python_exe, "-X", "utf8", rf"src\{CRAWL_SCRIPT}", "live"], cwd=script_dir, capture_output=True, text=True, encoding='utf-8', env=my_env, timeout=90)
                dt_alt = time.time() - t0_alt
                log_message(f" ├─ Trạm MT5 ({CRAWL_SCRIPT}): {'✅ TỐC ĐỘ RAM IPC (' + f'{dt_alt:.2f}s)' if res_alt.returncode == 0 else f'❌ LỖI RUN CRAWLER: {res_alt.stderr[:50]}'}")
                
                # --- Cập nhật Treeview Data ---
                sym_data = []
                from pathlib import Path
                for pqt in Path(os.path.join(script_dir, "data")).glob("*mt5_1m_2026.parquet"):
                    try:
                        df_raw = pd.read_parquet(pqt)
                        if len(df_raw) >= 2:
                            sym = pqt.name.replace("_mt5_1m_2026.parquet", "").upper().replace("_USD", "")
                            sym = sym.replace("M", "") # clean up
                            p_curr = df_raw['close'].iloc[-1]
                            p_prev = df_raw['close'].iloc[-2]
                            change = p_curr - p_prev
                            if isinstance(df_raw.index, pd.DatetimeIndex):
                                dt = df_raw.index[-1]
                                time_str = dt.strftime("%H:%M")
                            else:
                                time_str = "-"
                                
                            sym_data.append((sym, p_curr, change, time_str))
                    except: pass
                global gui_market_data
                gui_market_data = sorted(sym_data, key=lambda x: x[0])
                
                gui_status = "Ép Ma trận 3D Tensor Pytorch..."
                t0_feat = time.time()
                res_feat = subprocess.run([python_exe, "-X", "utf8", r"src\feature_engineering.py", "live", config_file], cwd=script_dir, capture_output=True, text=True, encoding='utf-8', env=my_env, timeout=60)
                dt_feat = time.time() - t0_feat
                log_message(f" ├─ Lõi Lượng Tử Data (Feature Eng): {'✅ TỔNG HỢP XONG (' + f'{dt_feat:.2f}s)' if res_feat.returncode == 0 else f'❌ LỖI VĂNG SÓNG {res_feat.stderr[:50]}'}")

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
                t0_infer = time.time()
                with torch.no_grad():
                    output = model(X_tensor)
                    probs = torch.softmax(output.data, dim=1).squeeze()
                    
                    # Xác suất Phe Bò (Index 1) và Phe Gấu (Index 0)
                    prob_down, prob_up = probs[0].item(), probs[1].item()
                    prediction = prob_up 
                    
                    gui_prediction = f"{prediction*100:.2f}%"
                    
                    t_min, t_max, t_mean = X_tensor.min().item(), X_tensor.max().item(), X_tensor.mean().item()
                    raw_logits = output.cpu().numpy()[0]
                    
                dt_infer = time.time() - t0_infer
                    
                # LOGGING THEO YÊU CẦU TRỰC TIẾP
                print(f"\n[{gui_time}] 🌐 MÔ HÌNH NÃO BỘ TỰ ĐỘNG CHỌN: {session_display} 🌐", flush=True)
                print(f"👉 INPUT: Tensor Shape {X_tensor.shape}. Min={t_min:.4f}|Max={t_max:.4f}|Mean={t_mean:.4f}. Core Z-Score: {last_60_candles[-1][:5]}...", flush=True)
                print(f"🧠 DỮ LIỆU LOGITS MẠNG NƠ RON [{dt_infer:.4f}s]: {raw_logits}. XÁC SUẤT SOFTMAX: {prediction*100:.4f}%", flush=True)
                    
                # Cổng Điều Hướng Sniper 55/45
                manage_mt5_positions(prediction, lot_size=0.01, sl_pips=50, tp_pips=100)
                update_active_trade_loggers()
                gui_status = "Đã Khóa Mốc & Trượt Dừng lỗ! Đang ngáy..."
                        
            except Exception as e:
                import traceback
                log_message(f"FATAL EXCEPTION in Bot Loop: {e}\n{traceback.format_exc()}")
                gui_status = "Lỗi Mạng/Khựng Phễu!"
                
            # Đợi 3 giây trước ranh giới cào dữ liệu mới
            time.sleep(3)
            
        time.sleep(0.5)

# --- LUỒNG CHÍNH: VẼ BẢNG ĐIỀU KHIỂN NỔI ĐA PHIÊN (MOE DASHBOARD) ---
def update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr):
    lbl_time.config(text=f"🕒 {gui_time}")
    lbl_session.config(text=f"🌐 {gui_session}")
    lbl_action.config(text=f"🎯 Hành động: {gui_action}")
    lbl_status.config(text=f"⚙️ {gui_status}")
    lbl_thr.config(text=gui_thr_text)
    
    # Update Market Data Treeview
    for item in tree.get_children():
        tree.delete(item)
    for sym, price, change, t_str in gui_market_data:
        color = "green" if change >= 0 else "red"
        tree.insert("", "end", values=(sym, f"{price:,.2f}", f"{change:+.2f}", t_str), tags=(color,))
    tree.tag_configure("green", foreground="#00ffcc")
    tree.tag_configure("red", foreground="#ff3366")
    
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
        
    root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr)

def start_overlay_dashboard():
    root = tk.Tk()
    root.title("MoE Terminator Dashboard")
    
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.90) 
    
    screen_w = root.winfo_screenwidth()
    x_pos = screen_w - 380 
    
    # Đặt lệch Layout để không chèn lên nhau
    if "XAU" in TARGET_SYMBOL.upper():
        y_pos = 50
    else:
        y_pos = 250
        
    root.geometry(f"360x500+{x_pos}+{y_pos}")
    root.configure(bg='#121212') 
    
    # Init root drag pos
    root.x = 0
    root.y = 0
    
    def start_move(event):
        root.x = event.x
        root.y = event.y
    def stop_move(event):
        root.x = None
        root.y = None
    def do_move(event):
        if root.x is None or root.y is None: return
        deltax = event.x - root.x
        deltay = event.y - root.y
        x = root.winfo_x() + deltax
        y = root.winfo_y() + deltay
        root.geometry(f"+{x}+{y}")
        
    root.bind("<ButtonPress-1>", start_move)
    root.bind("<ButtonRelease-1>", stop_move)
    root.bind("<B1-Motion>", do_move)
    
    tk.Label(root, text=f"🔥 {TARGET_SYMBOL} MOE TERMINATOR 🔥", fg="#ffcc00", bg="#121212", font=("Helvetica", 11, "bold")).pack(pady=2)
    
    lbl_session = tk.Label(root, text="🌐 Phiên: Đang đo Đạc...", fg="#cc88ff", bg="#121212", font=("Helvetica", 9, "bold"))
    lbl_session.pack()
    
    lbl_pred = tk.Label(root, text="🧠 THỜI CƠ (Lực): N/A", fg="#cccccc", bg="#121212", font=("Helvetica", 10, "bold"))
    lbl_pred.pack()
    
    lbl_action = tk.Label(root, text="🎯 Hành động: Đang ngủ", fg="#ff9900", bg="#121212", font=("Helvetica", 9))
    lbl_action.pack()
    
    lbl_thr = tk.Label(root, text="⚖️ Ngưỡng L4: BUY>60% | SELL<40%", fg="#ff33cc", bg="#121212", font=("Helvetica", 9, "bold"))
    lbl_thr.pack()
    
    # KHU VỰC BÁO CÁO REAL-TIME DỮ LIỆU
    frame_data = tk.Frame(root, bg="#121212")
    frame_data.pack(fill=tk.BOTH, expand=True, pady=4, padx=5)
    
    import tkinter.ttk as ttk
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#1e1e1e", foreground="white", fieldbackground="#1e1e1e", borderwidth=0, font=("Courier", 9))
    style.configure("Treeview.Heading", background="#333333", foreground="white", font=("Helvetica", 9, "bold"))
    
    cols = ("Symbol", "Price", "Change", "Time")
    tree = ttk.Treeview(frame_data, columns=cols, show="headings", height=15)
    tree.heading("Symbol", text="Mã")
    tree.heading("Price", text="Giá")
    tree.heading("Change", text="Biến Động")
    tree.heading("Time", text="Giờ")
    tree.column("Symbol", width=80, anchor=tk.W)
    tree.column("Price", width=70, anchor=tk.E)
    tree.column("Change", width=70, anchor=tk.E)
    tree.column("Time", width=50, anchor=tk.E)
    tree.pack(fill=tk.BOTH, expand=True)
    
    frame_bottom = tk.Frame(root, bg="#121212")
    frame_bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=2, padx=5)
    
    lbl_time = tk.Label(frame_bottom, text="🕒 00:00:00", fg="white", bg="#121212", font=("Helvetica", 8))
    lbl_time.pack(side=tk.LEFT)
    
    lbl_status = tk.Label(frame_bottom, text="⚙️ Booting...", fg="#888888", bg="#121212", font=("Helvetica", 8))
    lbl_status.pack(side=tk.RIGHT)
    
    bot_thread = threading.Thread(target=bot_background_loop, daemon=True)
    bot_thread.start()
    
    update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr)
    root.mainloop()

if __name__ == "__main__":
    start_overlay_dashboard()
