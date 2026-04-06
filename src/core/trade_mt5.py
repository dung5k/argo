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

import sys
import os

# Đẩy src lên đầu cờ để import được ở mọi cwd (dù khác ổ đĩa hay thư mục)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Mạng thần kinh từ file Train
try:
    from src.legacy.train_ga import TransformerModel
except ModuleNotFoundError:
    try:
        from legacy.train_ga import TransformerModel
    except ModuleNotFoundError:
        import traceback
        traceback.print_exc()
        print("\n[LỖI] Không thể nạp mạng thần kinh (TransformerModel).")
        input("Bấm Enter để thoát...")
        sys.exit(1)

import json

# Import Feature Engineering logic for in-memory processing
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import src.core.feature_engineering as fe
except ModuleNotFoundError:
    try:
        import core.feature_engineering as fe
    except ModuleNotFoundError:
        import feature_engineering as fe
from mt5_data_manager import MT5DataManager

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
    global gui_status, gui_prediction, gui_time, gui_action, gui_session, gui_forex_time, gui_crypto_time, last_mac_run, gui_thr_text
    
    last_delayed_log_time = 0
    inference_feats = []
    
    mt5_manager = MT5DataManager(log_callback=log_message, target_sym=TARGET_SYMBOL)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Đọc num_features từ Scaler chứ không phải Parquet (Scaler là nguồn sự thật chính xác)
    import joblib
    scaler_path = rf"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\scaler.pkl"
    try:
        _scaler = joblib.load(scaler_path)
        num_features = len(_scaler.feature_names_in_) + 1  # +1 for is_imputed_flag appended after scale
        log_message(f"[BOT] Đọc num_features từ Scaler: {num_features} (bao gồm is_imputed_flag)")
    except Exception as e:
        # Fallback: đọc từ parquet
        features_path = rf"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\final_features_{TARGET_PREFIX}.parquet"
        try:
            sample_df = pd.read_parquet(features_path)
            num_features = sample_df.shape[1]
            log_message(f"[BOT] Fallback: Đọc num_features từ Parquet: {num_features}")
        except Exception as e2:
            gui_status = "Lỗi đọc Scaler hoặc Parquet! Kiểm tra data/"
            log_message(f"[BOT] FATAL: Không thể xác định num_features: {e2}")
            return
        
    # Load genes (hyperparams) from best_genes.json
    import json
    # Cố định kiến trúc v5.0 Deep Phoenix
    window_size     = 60
    d_model         = 256
    nhead           = 8
    num_attn_layers = 3
    dropout_rate    = 0.2
    
    gui_status = f"V5 Mode: win={window_size}, d={d_model}"
    log_message(f"[BOT] Unified Transformer V5: {d_model}")

    # Load num_xau_features if available
    meta_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\feature_meta.json"
    num_xau_features = None
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding='utf-8') as mf:
            meta = json.load(mf)
            num_xau_features = meta.get("num_xau_features", None)

    model = None
    log_message(f"[BOT] Ready to init TransformerModel d={d_model}, heads={nhead}, layers={num_attn_layers}, win={window_size}")
    
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
        
        # --- CẬP NHẬT NGƯỠNG HIỂN THỊ (UI) & CẤU HÌNH BOT LIÊN TỤC TRONG LÚC CHỜ ---
        # Mặc định phòng hờ
        weight_file_cfg = f"{TARGET_SYMBOL.lower()}_unified_weights.pth"
        hf_run_cfg = None

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as ft:
                    cfg_t = json.load(ft)
                    b_th = int(cfg_t.get("BUY_ENTRY_THR", 0.60) * 100)
                    s_th = int(cfg_t.get("SELL_ENTRY_THR", 0.40) * 100)
                    gui_thr_text = f"⚖️ Ngưỡng L4: BUY>{b_th}% | SELL<{s_th}%"
                    
                    weight_file_cfg = cfg_t.get("WEIGHT_FILE", weight_file_cfg)
                    hf_run_cfg = cfg_t.get("HF_RUN_ID", None)
        except: pass
        
        # Load from config instead of hardcoding
        WEIGHT_FILE = weight_file_cfg
        
        # --- HOT-SWAP MODULE: TỰ ĐỘNG THAY ĐỔI NÃO BỘ THEO MÚI GIỜ ---
        session_id, session_display = get_current_session()
        
        # Xác định tên Não bộ từ Model đang chạy
        global active_brain_name
        if 'active_brain_name' not in globals():
            active_brain_name = WEIGHT_FILE
        
        gui_session = f"{session_display}  [Não bộ: {active_brain_name}]"
        
        if session_id != current_loaded_session:
            log_message(f"[BOT] Thay đổi Phiên: {session_id}. Đang nạp {WEIGHT_FILE}...")
            
            runs_model_path = ""
            # 1. Ưu tiên cao nhất: Tải Weights, Scaler, và Metrix xịn nhất từ Đám mây HuggingFace
            hf_token = "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"
            try:
                from huggingface_hub import HfApi, hf_hub_download
                api = HfApi(token=hf_token)
                files = api.list_repo_files("dung5k/argo_data", repo_type="dataset")
                
                # Tìm tất cả thư mục run_ tương thích với TARGET_SYMBOL
                run_dirs = [f.split('/')[1] for f in files if f.startswith('runs/') and f'_{TARGET_SYMBOL.lower()}_' in f and WEIGHT_FILE in f]
                
                if run_dirs:
                    if hf_run_cfg and hf_run_cfg in run_dirs:
                        latest_run = hf_run_cfg
                    else:
                        latest_run = max(run_dirs)
                        
                    active_brain_name = latest_run
                    gui_status = f"Đang kéo mây Không Gian {latest_run}..."
                    log_message(f"[HF CLOUD] XÁC ĐỊNH NÃO BỘ TỐT NHẤT: {latest_run} (File: {WEIGHT_FILE})")
                    
                    runs_model_path = hf_hub_download(
                        repo_id="dung5k/argo_data", repo_type="dataset", token=hf_token,
                        filename=f"runs/{latest_run}/{WEIGHT_FILE}"
                    )
                    
                    # ĐỒNG BỘ SCALER KHỚP VỚI TRỌNG SỐ (CỰC QUAN TRỌNG)
                    try:
                        scaler_cloud_path = hf_hub_download(
                            repo_id="dung5k/argo_data", repo_type="dataset", token=hf_token,
                            filename=f"runs/{latest_run}/scaler.pkl"
                        )
                        import joblib
                        _tmp_scaler = joblib.load(scaler_cloud_path)
                        _tmp_feats = list(_tmp_scaler.feature_names_in_)
                        
                        if not any(TARGET_PREFIX in f for f in _tmp_feats):
                            log_message(f" ├─ ⚠️ [SCALE SHIELD] Scaler Cloud KHÔNG HỢP LỆ (Lỗi chứa data mã khác). Sẽ dùng Scaler Local!")
                        else:
                            import shutil
                            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            scaler_local = os.path.join(script_dir, "data", "scaler.pkl")
                            shutil.copy(scaler_cloud_path, scaler_local)
                            mt5_manager.reload_features() # Xây lại lưới ngay lập tức để hít đúng Data
                            log_message(f" ├─ ✅ [SCALE SHIELD] Đã đồng bộ Scaler Local về đúng định dạng của não {latest_run}!")
                    except Exception as sce:
                        log_message(f" ├─ ⚠️ Không thể tải đồng bộ scaler.pkl từ đám mây: {sce}")
                        
                    # PHÂN TÍCH METRIX (HIỂN THỊ LOG KIỂM KÊ FEATURES THEO YÊU CẦU CỦA USER)
                    try:
                        metrix_path = hf_hub_download(
                            repo_id="dung5k/argo_data", repo_type="dataset", token=hf_token,
                            filename=f"runs/{latest_run}/training_metrix.json"
                        )
                        with open(metrix_path, "r", encoding='utf-8') as fm:
                            metrix = json.load(fm)
                        feats = metrix.get("training_metadata", {}).get("data_features", [])
                        inference_feats = feats
                        
                        # TỰ ĐỘNG KHỚP BỘ NÃO VỚI ĐÁM MÂY (CHỐNG SIZE MISMATCH LÚC LOAD TRỌNG SỐ)
                        # Đọc num_xau_features từ file meta chuẩn (ví dụ 8 feature OHLVC) chứ không đếm mù nhòa
                        safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        meta_path_local = os.path.join(safe_script_dir, "data", f"feature_meta_{TARGET_PREFIX}.json")
                        num_xau_features = 8 # Fallback gốc
                        if os.path.exists(meta_path_local):
                            with open(meta_path_local, "r", encoding='utf-8') as mf:
                                num_xau_features = json.load(mf).get("num_xau_features", 8)
                                
                        num_features = len(feats)  # Khớp tổng số chiều của não bộ (VD: 86)
                        log_message(f" ├─ 📐 Khớp Kích thước Mạng: {TARGET_PREFIX} ({num_xau_features}) | Macro ({num_features - num_xau_features}) | SUM ({num_features})")
                            
                        log_message(f" ├─ 🧠 [METRIX DATA] Não bộ yêu cầu TỔNG CỘNG {len(feats)} Dimensions để nạp đạn!")
                        # Log snippet of features to terminal to inform user
                        sample_feats = [f for f in feats if 'close' in f.lower() or 'PARQUET' in f or 'volume' in f.lower()][:10]
                        log_message(f" ├─ Danh sách Features nhận diện mẫu: {', '.join(sample_feats)}...")
                    except Exception as me:
                        pass
                        
                    log_message(f"[HF CLOUD] Đã tải thành công HỆ TƯ TƯỞNG từ Đám mây!")
                else:
                    raise Exception("Không tìm thấy thư mục run_ tương thích trên Repo!")
            except Exception as e:
                log_message(f"[HF CLOUD] Không thể kết nối Đám mây hoặc Lỗi Tải: {str(e)[:100]}. Chuyển qua lấy bộ nhớ Local.")
                
                # 2. Phương án dự phòng: Tìm trong Local
                from pathlib import Path
                runs_dir = Path(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs")
                found_models = list(runs_dir.rglob(WEIGHT_FILE))
                runs_model_path = str(max(found_models, key=os.path.getctime)) if found_models else ""
            
            old_model_path = os.path.join(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\models", f"{TARGET_SYMBOL.lower()}_{session_id}_weights.pth")
            
            if os.path.exists(runs_model_path):
                log_message(f"[BOT] Đang ốp Ma trận trọng số (Local Cache): {runs_model_path}")
                
                try:
                    local_metrix = os.path.join(os.path.dirname(runs_model_path), "training_metrix.json")
                    with open(local_metrix, "r", encoding='utf-8') as fm:
                        _metrix = json.load(fm)
                    inference_feats = _metrix.get("training_metadata", {}).get("data_features", [])
                    if inference_feats:
                        log_message(f"[BOT] ✅ Đã cache đạn dược {len(inference_feats)} features từ metrix local.")
                except:
                    pass
                
                # TỰ ĐỘNG ĐỌC KÍCH THƯỚC THỰC TẾ TỪ FILE WEIGHTS (NGUỒN SỰ THẬT TUYỆT ĐỐI)
                # Không tin vào metrix.json hay feature_meta.json vì chúng có thể bị stale
                try:
                    _state = torch.load(runs_model_path, map_location='cpu', weights_only=True)
                    # xau_input_proj.weight shape: [d_model, num_xau_features]
                    # macro_fc.0.weight shape: [hidden, num_macro_features]
                    _xau_w = _state.get('xau_input_proj.weight', None)
                    _macro_w = _state.get('macro_fc.0.weight', None)
                    if _xau_w is not None:
                        num_xau_features = _xau_w.shape[1]
                    if _xau_w is not None and _macro_w is not None:
                        num_macro_features = _macro_w.shape[1]
                        num_features = num_xau_features + num_macro_features
                    log_message(f"[BOT] ✅ [AUTO-DETECT] Đọc từ Weights: XAU={num_xau_features} | MACRO={num_features - num_xau_features} | SUM={num_features}")
                except Exception as ade:
                    log_message(f"[BOT] ⚠️ Auto-detect thất bại, dùng giá trị hiện tại ({num_xau_features}/{num_features}): {ade}")
                
                # KHỞI TẠO LẠI NÃO BỘ ĐÚNG KÍCH THƯỚC TRƯỚC KHI LOAD STATE DICT
                model = TransformerModel(
                    num_features=num_features, d_model=d_model, nhead=nhead,
                    num_layers=num_attn_layers, dropout_rate=dropout_rate,
                    num_xau_features=num_xau_features
                ).to(device)
                
                model.load_state_dict(torch.load(runs_model_path, map_location=device, weights_only=True))
                model.eval()
                current_loaded_session = session_id
                gui_status = f"Đã Nạp Trọng Số: {active_brain_name[:20]}..."
                log_message(f"[BOT] Nạp não bộ thành công: {active_brain_name}")
            elif os.path.exists(old_model_path):
                log_message(f"[BOT] Đang load model từ file {old_model_path}")
                
                # Fetch run name from local if needed
                active_brain_name = WEIGHT_FILE
                try:
                    match = re.search(r'(run_\d{8}_\d{6}_[^/\\]+)', old_model_path)
                    if match: active_brain_name = match.group(1)
                except: pass
                
                # KHỞI TẠO LẠI NÃO BỘ ĐÚNG KÍCH THƯỚC DỰ PHÒNG
                model = TransformerModel(
                    num_features=num_features, d_model=d_model, nhead=nhead,
                    num_layers=num_attn_layers, dropout_rate=dropout_rate,
                    num_xau_features=num_xau_features
                ).to(device)
                
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
            
        gui_status = "Đang Cào Dữ Liệu Thời Gian Thực (In-Memory)..."
        if True:
            log_message(f"\n[{gui_time}] 🔄 BẮT ĐẦU VẬN CÔNG HÍT THỞ (TRỰC TIẾP TỪ RAM)...")
            
            t0_feat = time.time()
            
            try:
                merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=120)
                
                if err_msg:
                    gui_status = err_msg
                    
                if merged_df is None or len(merged_df) < window_size:
                    if "KHÔNG TÌM THẤY MÃ" not in gui_status:
                        gui_status = "❌ KHÔNG ĐỦ 120 NẾN HOẶC MẤT MẠNG MT5!"
                        log_message(f" ├─ Trạm Lõi (In-Memory): {gui_status}")
                    time.sleep(5)
                    continue
                
                # Cập nhật GUI Treeview từ RAM siêu tốc
                global gui_market_data
                gui_market_data = sorted(sym_data, key=lambda x: x[0])
                
                delayed_count = sum(1 for item in gui_market_data if item[5])
                current_t = time.time()
                if delayed_count > 0 and (current_t - last_delayed_log_time) > 180: # Báo mỗi 3 phút
                    log_message(f" 🔌⚠️ [WIFI/BROKER ĐỨT MẠNG] Phát hiện {delayed_count}/{len(gui_market_data)} cặp tiền bị đứt luồng dữ liệu (Quá 5 phút không có giá mới). Bảng điện đồ sẽ hiển thị 'Lỗi MT5 (Mất Data)'. Vui lòng kiểm tra đường truyền MT5 Terminal!")
                    last_delayed_log_time = current_t
                
                gui_status = "Ép Ma trận 3D Tensor Pytorch (In-Memory)..."
                
                df, _ = fe.create_stationary_features(merged_df, is_live=True)
                
                dt_feat = time.time() - t0_feat
                log_message(f" ├─ Trạm Lõi lượng tử (RAM Mapped): ✅ HOÀN TẤT ({dt_feat:.2f}s)")
                log_message(f" 📊 KIỂM KÊ KHO: RAM Nạp thành công {len(df):,} nến.")
                
                if inference_feats and len(inference_feats) <= len(df.columns):
                    valid_cols = [c for c in inference_feats if c in df.columns]
                    if len(valid_cols) == len(inference_feats):
                        last_60_candles = df[valid_cols].iloc[-window_size:].values
                    else:
                        gui_status = "Lỗi: Sai lệch Features!"
                        missing_feats = [c for c in inference_feats if c not in df.columns]
                        print(f" ⚠️ CẢNH BÁO LỰC: Thiếu Features! Model cần {len(inference_feats)} nhưng data chỉ có {len(valid_cols)} khớp. (Thiếu: {missing_feats[:5]})", flush=True)
                        time.sleep(2)
                        continue
                else:
                    last_60_candles = df.iloc[-window_size:].values
                
                if len(last_60_candles) < window_size:
                    gui_status = "Mạng lag, đợi nến 1 phút sau..."
                    print(f" ⚠️ CẢNH BÁO LỰC: Lượng Nến Cắt quá mỏng ({len(last_60_candles)}/{window_size}). AI từ chối uống dòng Máu này!", flush=True)
                    time.sleep(2)
                    continue
                
                # Vệ sinh dữ liệu: Chặn Model ăn Rác (NaN/Inf)
                if np.isnan(last_60_candles).any() or np.isinf(last_60_candles).any():
                    gui_status = "Data chứa Rác (NaN/Inf), Xả bỏ!"
                    print(f" 🚨 LỖI TINH KHIẾT: Phát hiện dữ liệu lỗi (NaN hoặc Inf). Model từ chối tiêu thụ!", flush=True)
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
                        
            except Exception as ex_feat:
                import traceback
                log_message(f" ├─ Lõi Lượng Tử (RAM Mapped): ❌ LỖI NGHIÊM TRỌNG: {str(ex_feat)[:100]}")
                log_message(traceback.format_exc())
                gui_status = "Lỗi Xử Lý Dữ Liệu / Inference!"
                
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
    for sym, price, change, t_str, source_name, is_delayed in gui_market_data:
        change_text = f"🟢 {change:+.2f}" if change >= 0 else f"🔴 {change:+.2f}"
        color = "delayed" if is_delayed else "normal"
        # Since 100% is from MT5, we only show standard MT5 network error if delayed
        source_display = f"Lỗi MT5 (Mất Data)" if is_delayed else "Mạng MT5"
        tree.insert("", "end", values=(sym, f"{price:,.2f}", change_text, source_display, t_str), tags=(color,))
        
    tree.tag_configure("normal", foreground="white")
    tree.tag_configure("delayed", foreground="#ffaa00") # Màu cam nếu giá bị chậm (delay)
    
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
    
    cols = ("Symbol", "Price", "Change", "Source", "Time")
    tree = ttk.Treeview(frame_data, columns=cols, show="headings", height=15)
    tree.heading("Symbol", text="Mã")
    tree.heading("Price", text="Giá")
    tree.heading("Change", text="Biến Động")
    tree.heading("Source", text="Nguồn")
    tree.heading("Time", text="Giờ")
    
    tree.column("Symbol", width=70, anchor=tk.W)
    tree.column("Price", width=65, anchor=tk.E)
    tree.column("Change", width=65, anchor=tk.E)
    tree.column("Source", width=80, anchor=tk.W)
    tree.column("Time", width=45, anchor=tk.E)
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
