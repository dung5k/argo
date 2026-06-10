import os
import sys
import time
import json
import logging
import threading
import warnings
import pandas as pd
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5

warnings.filterwarnings("ignore", category=FutureWarning)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.mt5_data_manager import MT5DataManager
from src.bot_v8.data_processor_v8 import V8DataProcessor
from src.bot_v8.inference_engine_v8 import V8InferenceEngine

# Configuration
SYMBOL = "XAUUSDm"
MAGIC_NUMBER = 88801
FIXED_LOT = 0.01
MAX_HOLD_MINUTES = 180
MAX_OPEN_POSITIONS = 4
TP_MULT = 3.0
SL_MULT = 1.5
POLL_INTERVAL = 60
MODEL_NAME = "best_model_ARGO3_OPT-217.pt"

# --- GUI Globals ---
gui_time = "00:00:00"
gui_status = "Khởi động..."
gui_action = "Đang chờ dữ liệu"
gui_probs = {'buy': 0.0, 'sell': 0.0}
gui_price = 0.0
gui_atr = 0.0
gui_sym = SYMBOL
gui_threshold = 0.35

log_dir = os.path.join(_ROOT, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"v8_live_bot_{datetime.now().strftime('%Y%m%d')}.log")

sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def log(msg):
    logging.info(msg)

class V8TradeManager:
    def __init__(self, symbol: str):
        self.symbol = symbol
        
    def execute_trade(self, action_name: str, price: float, atr: float):
        # 1. Reversal logic: Đóng các vị thế ngược chiều trước khi vào lệnh mới
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is not None:
            opposing_type = mt5.ORDER_TYPE_SELL if action_name == "STRONG_BUY" else mt5.ORDER_TYPE_BUY
            for pos in positions:
                if pos.magic == MAGIC_NUMBER and pos.type == opposing_type:
                    log(f"🔄 [Reversal] Tín hiệu {action_name} ngược chiều với vị thế {pos.ticket}. Đóng vị thế cũ...")
                    self.close_position(pos)
                    
        # 2. Kiểm tra giới hạn số lệnh nhồi tối đa (MAX_OPEN_POSITIONS)
        positions = mt5.positions_get(symbol=self.symbol)
        active_count = 0
        if positions is not None:
            active_count = sum(1 for pos in positions if pos.magic == MAGIC_NUMBER)
            
        if active_count >= MAX_OPEN_POSITIONS:
            log(f"⚠️ [TradeManager] Bỏ qua tín hiệu {action_name}. Số lệnh đang mở ({active_count}) đã đạt giới hạn tối đa ({MAX_OPEN_POSITIONS}).")
            return False
            
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            log(f"❌ [TradeManager] Không lấy được giá tick cho {self.symbol}")
            return False
            
        tp_dist = atr * TP_MULT
        sl_dist = atr * SL_MULT
        
        if action_name == "STRONG_BUY":
            order_type = mt5.ORDER_TYPE_BUY
            exe_price = tick.ask
            sl = exe_price - sl_dist
            tp = exe_price + tp_dist
        else:
            order_type = mt5.ORDER_TYPE_SELL
            exe_price = tick.bid
            sl = exe_price + sl_dist
            tp = exe_price - tp_dist
            
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(FIXED_LOT),
            "type": order_type,
            "price": exe_price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": MAGIC_NUMBER,
            "comment": "V8 Live Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        log(f"Đang gửi lệnh: {request}")
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            log(f"❌ [TradeManager] Lỗi gửi lệnh: {result.retcode} - {result.comment}")
            return False
            
        log(f"✅ [TradeManager] Khớp lệnh thành công! Ticket: {result.order}")
        return True

    def modify_sl_tp(self, ticket: int, sl: float, tp: float):
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": self.symbol,
            "position": ticket,
            "sl": sl,
            "tp": tp,
            "magic": MAGIC_NUMBER
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            log(f"❌ [TradeManager] Lỗi sửa SL/TP cho lệnh {ticket}: {result.retcode} - {result.comment}")
            return False
        log(f"✅ [TradeManager] Đã sửa SL/TP thành công cho lệnh {ticket}!")
        return True

    def manage_open_positions(self, current_atr: float):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return
            
        for pos in positions:
            if pos.magic == MAGIC_NUMBER:
                tick = mt5.symbol_info_tick(self.symbol)
                if not tick: continue
                
                # Buy position breakeven logic
                if pos.type == mt5.ORDER_TYPE_BUY:
                    current_price = tick.bid
                    profit = current_price - pos.price_open
                    if profit >= current_atr and (pos.sl < pos.price_open or pos.sl == 0.0):
                        new_sl = pos.price_open
                        log(f"🛡️ [Breakeven] Lệnh BUY {pos.ticket} đạt lợi nhuận +{profit:.2f} (>= ATR {current_atr:.2f}). Dịch SL về Entry {new_sl:.2f}...")
                        self.modify_sl_tp(pos.ticket, new_sl, pos.tp)
                        
                # Sell position breakeven logic
                elif pos.type == mt5.ORDER_TYPE_SELL:
                    current_price = tick.ask
                    profit = pos.price_open - current_price
                    if profit >= current_atr and (pos.sl > pos.price_open or pos.sl == 0.0):
                        new_sl = pos.price_open
                        log(f"🛡️ [Breakeven] Lệnh SELL {pos.ticket} đạt lợi nhuận +{profit:.2f} (>= ATR {current_atr:.2f}). Dịch SL về Entry {new_sl:.2f}...")
                        self.modify_sl_tp(pos.ticket, new_sl, pos.tp)

    def check_time_stops(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return
            
        for pos in positions:
            if pos.magic == MAGIC_NUMBER:
                tick = mt5.symbol_info_tick(self.symbol)
                if not tick: continue
                broker_time = tick.time
                duration_minutes = (broker_time - pos.time) / 60.0
                
                if duration_minutes >= MAX_HOLD_MINUTES:
                    log(f"⚠️ [Time Stop] Lệnh {pos.ticket} đã ôm {duration_minutes:.1f} phút. Đang đóng lệnh...")
                    self.close_position(pos)

    def close_position(self, pos):
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick: return False
        action = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": pos.volume,
            "type": action,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": MAGIC_NUMBER,
            "comment": "V8 Time Stop",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        mt5.order_send(request)
        return True

def bot_background_loop():
    global gui_status, gui_action, gui_probs, gui_price, gui_atr, gui_sym
    
    log("="*50)
    log(f"Khởi động V8 LIVE BOT - {SYMBOL}")
    log(f"Model: {MODEL_NAME} | Lot: {FIXED_LOT} | Max Hold: {MAX_HOLD_MINUTES}p")
    log("="*50)
    
    config_path = os.path.join(_ROOT, "v8_configs", "v8_training_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    mt5_manager = MT5DataManager(log_callback=log, target_sym=SYMBOL, config_path=os.path.join(_ROOT, "v8_configs", "unified_config.json"))
    mt5_manager.scan_terminals_and_map()
    
    if not mt5.initialize():
        gui_status = "LỖI KHỞI TẠO MT5"
        log("❌ KHÔNG THỂ KHỞI TẠO MT5. Kiểm tra lại MT5!")
        return

    if mt5.terminal_info() is None:
        gui_status = "LỖI KẾT NỐI MT5"
        log("❌ KHÔNG THỂ KẾT NỐI MT5. Vui lòng kiểm tra lại đường dẫn và đăng nhập.")
        return
        
    actual_sym = mt5_manager.IN_MEMORY_SYMBOL_HINT.get(SYMBOL, SYMBOL)
    gui_sym = actual_sym
    log(f"Đã kết nối MT5. Mã giao dịch thực tế: {actual_sym}")
    gui_status = f"Đã kết nối {actual_sym}"
    
    global gui_threshold
    data_processor = V8DataProcessor(config, log_callback=log)
    inference_engine = V8InferenceEngine(MODEL_NAME, config_path, log_callback=log)
    gui_threshold = inference_engine.threshold
    trade_manager = V8TradeManager(actual_sym)
    
    last_candle_time = None
    base_tf_cfg = config.get("system", {}).get("base_timeframe", "M15")
    resample_freq = '5T' if base_tf_cfg == "M5" else '15T'
    
    gui_status = f"Sẵn sàng, chờ nến {base_tf_cfg}..."
    log("✅ Bot đã sẵn sàng. Đang vào vòng lặp giám sát...")
    
    while True:
        try:
            trade_manager.check_time_stops()
            if gui_atr > 0.0:
                trade_manager.manage_open_positions(gui_atr)
            
            rates = mt5.copy_rates_from_pos(actual_sym, mt5.TIMEFRAME_M1, 0, 50000)
            if rates is None or len(rates) < 48000:
                gui_status = "Lỗi kéo Data từ MT5"
                time.sleep(POLL_INTERVAL)
                continue
                
            df_m1 = pd.DataFrame(rates)
            df_m1['time'] = pd.to_datetime(df_m1['time'], unit='s')
            df_m1.set_index('time', inplace=True)
            df_m1.rename(columns={'tick_volume': 'volume'}, inplace=True)
            
            df_base = data_processor.resample_m1_to_tf(df_m1, resample_freq)
            current_last_candle_time = df_base.index[-1]
            
            # Update gui info if tick is available
            tick = mt5.symbol_info_tick(actual_sym)
            if tick: gui_price = tick.bid
            
            if last_candle_time is None:
                last_candle_time = current_last_candle_time
                gui_status = f"Đồng bộ nến {last_candle_time.strftime('%H:%M')}"
                log(f"[Sync] Đã đồng bộ nến {base_tf_cfg} gần nhất: {last_candle_time}")
            elif current_last_candle_time > last_candle_time:
                gui_status = f"Nến {current_last_candle_time.strftime('%H:%M')} vừa đóng. Analyzing..."
                log(f"🔔 [TÍN HIỆU] Nến {base_tf_cfg} mới đóng: {current_last_candle_time}. Đang phân tích...")
                
                success, tensors = data_processor.process_live_data(df_m1)
                if success and tensors is not None:
                    res = inference_engine.predict(tensors)
                    if "error" not in res:
                        signal = res['signal']
                        action = res['action']
                        conf = res['confidence']
                        price = res['price']
                        atr = res['atr']
                        
                        gui_price = price
                        gui_atr = atr
                        gui_probs['buy'] = res['probs']['B2']
                        gui_probs['sell'] = res['probs']['S2']
                        gui_action = action
                        gui_status = f"Phân tích hoàn tất: {action}"
                        
                        log(f"📊 [Phân tích] Giá: {price} | ATR: {atr:.2f} | Tín hiệu: {action} (Độ tin cậy: {conf*100:.1f}%)")
                        
                        if signal == 4 or signal == 0:
                            trade_manager.execute_trade(action, price, atr)
                            
                last_candle_time = current_last_candle_time
                
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            gui_status = "Lỗi Exception (Xem log)"
            import traceback
            log(f"❌ [Main Loop] Lỗi: {e}\n{traceback.format_exc()}")
            time.sleep(POLL_INTERVAL)

def update_ui(root, lbl_time, lbl_status, canvas_pred, lbl_action, lbl_info):
    global gui_time
    gui_time = datetime.now().strftime('%H:%M:%S')
    lbl_time.config(text=f"🕒 {gui_time}")
    lbl_status.config(text=f"📡 {gui_status}")
    lbl_action.config(text=f"🎯 Chiến thuật: {gui_action}")
    lbl_info.config(text=f"💰 Giá: {gui_price:,.2f} | 📏 ATR: {gui_atr:.2f}")
    
    canvas_pred.delete("all")
    w = canvas_pred.winfo_width()
    if w < 10: w = 330
    
    buy_p = gui_probs.get('buy', 0.0)
    sell_p = gui_probs.get('sell', 0.0)
    
    bw = int(w * buy_p)
    sw = int(w * sell_p)
    
    # Tô sáng màu rực rỡ chỉ khi một bên chiến thắng vượt ngưỡng và thỏa mãn biên lệch min_delta (0.05)
    buy_color = "#00ff77" if (buy_p >= gui_threshold and buy_p > sell_p and (buy_p - sell_p) >= 0.05) else "#007733"
    sell_color = "#ff3333" if (sell_p >= gui_threshold and sell_p > buy_p and (sell_p - buy_p) >= 0.05) else "#882222"
    
    canvas_pred.create_rectangle(0, 0, bw, 24, fill=buy_color, outline="")
    canvas_pred.create_rectangle(w - sw, 0, w, 24, fill=sell_color, outline="")
    
    thr_x_buy = int(w * gui_threshold)
    thr_x_sell = int(w - w * gui_threshold)
    canvas_pred.create_line(thr_x_buy, 0, thr_x_buy, 24, fill="#ffcc00", dash=(2, 2))
    canvas_pred.create_line(thr_x_sell, 0, thr_x_sell, 24, fill="#ffcc00", dash=(2, 2))
    
    txt = f"BUY {buy_p:.1%} | SELL {sell_p:.1%}"
    if buy_p == 0.0 and sell_p == 0.0:
        txt = "Chờ Tín Hiệu..."
    canvas_pred.create_text(w/2, 12, text=txt, fill="white", font=("Consolas", 10, "bold"))
    
    root.after(500, update_ui, root, lbl_time, lbl_status, canvas_pred, lbl_action, lbl_info)

def start_overlay_dashboard():
    root = tk.Tk()
    root.title(f"V8 LIVE TERMINATOR")
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.92) 
    
    screen_h = root.winfo_screenheight()
    root.geometry(f"360x220+10+{screen_h - 300}")
    root.configure(bg='#080b12') 
    
    root.x, root.y = 0, 0
    def do_move(event):
        if root.x is None or root.y is None: return
        root.geometry(f"+{root.winfo_x() + event.x - root.x}+{root.winfo_y() + event.y - root.y}")
        
    root.bind("<ButtonPress-1>", lambda e: setattr(root, 'x', e.x) or setattr(root, 'y', e.y))
    root.bind("<ButtonRelease-1>", lambda e: setattr(root, 'x', None) or setattr(root, 'y', None))
    root.bind("<B1-Motion>", do_move)
    
    tk.Label(root, text=f"🔥 {SYMBOL} V8 LIVE 🔥", fg="#00ffff", bg="#080b12", font=("Consolas", 11, "bold")).pack(pady=5)
    tk.Label(root, text=f"🧠 Model: {MODEL_NAME}", fg="#aa66ff", bg="#080b12", font=("Consolas", 9)).pack()
    
    canvas_pred = tk.Canvas(root, height=24, bg="#1a2235", highlightthickness=0)
    canvas_pred.pack(pady=10, fill=tk.X, padx=15)
    
    lbl_action = tk.Label(root, text="🎯 Chiến thuật: Đang khởi động", fg="#ffcc00", bg="#080b12", font=("Consolas", 9))
    lbl_action.pack()
    
    lbl_info = tk.Label(root, text="💰 Giá: 0.00 | 📏 ATR: 0.00", fg="#ff55bb", bg="#080b12", font=("Consolas", 9))
    lbl_info.pack()
    
    lbl_status = tk.Label(root, text="📡 Khởi tạo...", fg="#aaaaaa", bg="#080b12", font=("Consolas", 8))
    lbl_status.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
    lbl_time = tk.Label(root, text="🕒 00:00:00", fg="#888888", bg="#080b12", font=("Consolas", 8))
    lbl_time.pack(side=tk.BOTTOM)
    
    update_ui(root, lbl_time, lbl_status, canvas_pred, lbl_action, lbl_info)
    root.mainloop()

if __name__ == "__main__":
    t = threading.Thread(target=bot_background_loop)
    t.daemon = True
    t.start()
    start_overlay_dashboard()
