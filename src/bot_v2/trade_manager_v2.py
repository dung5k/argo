import os
import time
from datetime import datetime

class V2TradeManager:
    """Quản lý thực thi lệnh Giao dịch lên máy chủ MT5 (MetaTrader 5)"""
    
    def __init__(self, target_symbol: str, config: dict, log_callback=None, tg_notify_callback=None):
        self.target_symbol = target_symbol
        self.config = config
        self.log_callback = log_callback or print
        self.tg_notify = tg_notify_callback or (lambda x: None)
        
        self.active_trade_loggers = {}
        self.gui_action = "-"
        self.gui_thr_text = "-"
        
        # We will late-import mt5 to allow tests to run on Linux/Mac if needed
        self.mt5 = None

    def init_mt5(self):
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            return True
        except ImportError:
            self.log_callback("❌ Module MetaTrader5 không tồn tại (Có thể đang chạy test enviroment)")
            return False

    def close_mt5_position(self, position):
        """Đóng khẩn cấp một vị thế MT5 đang sống (Cắt trạng thái hoàn toàn)."""
        if not self.mt5: return False
        
        symbol = position.symbol
        tick = self.mt5.symbol_info_tick(symbol)
        
        if position.type == self.mt5.ORDER_TYPE_BUY:
            order_type = self.mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = self.mt5.ORDER_TYPE_BUY
            price = tick.ask
            
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket, 
            "price": price,
            "deviation": 20,
            "magic": 101010,
            "comment": "AI Close Vị Thế",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            return False
            
        try:
            o_type = "MUA" if position.type == self.mt5.ORDER_TYPE_BUY else "BÁN"
            pnl = getattr(position, 'profit', 0)
            icon = "💰" if pnl > 0 else "🩸"
            self.tg_notify(f"🔴 [ĐÓNG LỆNH] AI vừa chốt lệnh {o_type}\n* Mã: {symbol}\n* Ticket: {position.ticket}\n* Lợi nhuận: {icon} {pnl:.2f} USD")
        except: pass
        
        return True

    def open_new_mt5_trade(self, symbol, order_type, lot_size, sl_pips, tp_pips, prediction):
        """Mở một vị thế mới hoàn toàn."""
        if not self.mt5: return None
        
        point_info = self.mt5.symbol_info(symbol)
        if point_info is None: return None
        point = point_info.point
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None: return None
        
        if order_type == self.mt5.ORDER_TYPE_BUY:
            price = tick.ask
            sl = price - sl_pips * 10 * point
            tp = price + tp_pips * 10 * point
        else:
            price = tick.bid
            sl = price + sl_pips * 10 * point
            tp = price - tp_pips * 10 * point
            
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot_size),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 101010,
            "comment": "AI Entry Order",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        
        result = self.mt5.order_send(request)
        if result is not None and getattr(result, 'retcode', -1) == self.mt5.TRADE_RETCODE_DONE:
            ticket = result.order
            try:
                o_type = "MUA (BUY)" if order_type == self.mt5.ORDER_TYPE_BUY else "BÁN (SELL)"
                self.tg_notify(f"🟢 [VÀO LỆNH] AI Đã thực hiện lệnh {o_type}\n* Mã: {symbol}\n* Ticket: {ticket}\n* Tỉ lệ Vượt Cản: {prediction*100:.2f}%")
            except: pass
            
            # Khởi tạo log (giản lược)
            self.active_trade_loggers[ticket] = {
                "status": "OPEN",
                "entry_price": float(request['price']),
                "order_type": "BUY" if order_type == self.mt5.ORDER_TYPE_BUY else "SELL",
            }
            return ticket
        else:
            self.log_callback(f"Lỗi MT5 Bắn Lệnh: {getattr(result, 'comment', 'N/A')}")
            return None

    def manage_mt5_positions(self, prediction, actual_target_sym=None, lot_size=0.01, sl_pips=50, tp_pips=100):
        """Hệ thống Quản lý Vị thế Đa Ngưỡng (Threshold State Machine)"""
        if not self.mt5: return
        
        symbol = actual_target_sym if actual_target_sym else self.target_symbol
        
        if self.mt5.symbol_info(symbol) is None:
            self.log_callback(f"⚠️ [Sniper Abort] Không tìm thấy mã {symbol}!")
            return
            
        live_cfg = self.config.get("LIVE_TRADING", {})
        BUY_ENTRY_THR  = live_cfg.get("BUY_ENTRY_THR", 0.60)
        SELL_ENTRY_THR = live_cfg.get("SELL_ENTRY_THR", 0.40)
        CLOSE_BUY_THR  = live_cfg.get("CLOSE_BUY_THR", 0.50)
        CLOSE_SELL_THR = live_cfg.get("CLOSE_SELL_THR", 0.50)
        
        cfg_lot_size = live_cfg.get("lot_size", lot_size)
        cfg_sl_pips = live_cfg.get("sl_pips", sl_pips)
        cfg_tp_pips = live_cfg.get("tp_pips", tp_pips)
            
        self.gui_thr_text = f"🔥 V2 Ngưỡng: BUY>{int(BUY_ENTRY_THR*100)}% | SELL<{int(SELL_ENTRY_THR*100)}%"
        
        positions = self.mt5.positions_get(symbol=symbol)
        has_open_position = False
        
        just_closed = False
        if positions:
            for pos in positions:
                has_open_position = True
                if pos.type == self.mt5.ORDER_TYPE_BUY:
                    if prediction <= CLOSE_BUY_THR:
                        self.gui_action = f"ĐÃ CHỐT BIÊN BUY ({pos.ticket})"
                        if self.close_mt5_position(pos):
                            has_open_position = False
                            just_closed = True
                    else:
                        self.gui_action = f"ĐANG KHÓA LÃI BUY ({pos.ticket})"
                        
                elif pos.type == self.mt5.ORDER_TYPE_SELL:
                    if prediction >= CLOSE_SELL_THR:
                        self.gui_action = f"ĐÃ CHỐT BIÊN SELL ({pos.ticket})"
                        if self.close_mt5_position(pos):
                            has_open_position = False
                            just_closed = True
                    else:
                        self.gui_action = f"ĐANG KHÓA LÃI SELL ({pos.ticket})"

        if not has_open_position and not just_closed:
            if prediction >= BUY_ENTRY_THR:
                self.gui_action = "🔥 ĐÃ BẮN LỆNH MUA (BUY)!"
                self.open_new_mt5_trade(symbol, self.mt5.ORDER_TYPE_BUY, cfg_lot_size, cfg_sl_pips, cfg_tp_pips, prediction)
            elif prediction <= SELL_ENTRY_THR:
                self.gui_action = "🔥 ĐÃ BẮN LỆNH BÁN (SELL)!"
                self.open_new_mt5_trade(symbol, self.mt5.ORDER_TYPE_SELL, cfg_lot_size, cfg_sl_pips, cfg_tp_pips, prediction)
            else:
                self.gui_action = "Thị trường Lưỡng Lự (Quan Sát)"
