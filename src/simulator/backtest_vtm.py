import time
from src.bot_v3.virtual_trade_manager_v3 import V3VirtualTradeManager

class BacktestVirtualTradeManager(V3VirtualTradeManager):
    """
    Kế thừa V3VirtualTradeManager để xử lý đặc thù Backtest:
    - Khớp lệnh T+1 (vào nến sau)
    - Trượt giá (Slippage Penalty)
    - Quét SL/TP bằng OHLC (quét râu)
    - Tính Trailing & PnL thả nổi bằng giá Close (chống nhiễu PnL múa râu)
    """

    def __init__(self, target_symbol: str, config: dict, log_callback=None, tg_notify_callback=None):
        super().__init__(target_symbol, config, log_callback, tg_notify_callback)
        self.pending_orders = []

    def _save_state(self):
        """OVERRIDE: Không lưu state ra file trong quá trình Backtest để tránh xung đột chéo giữa các threshold"""
        pass

    def _load_state(self):
        """OVERRIDE: Không load state từ file trong quá trình Backtest để tránh xung đột chéo giữa các threshold"""
        pass

    def open_new_mt5_trade(self, symbol: str, order_type_str: str, lot_size: float, sl_pips: float, tp_pips: float, preds_info: str, current_bid: float, current_ask: float, point: float):
        """OVERRIDE: Không mở lệnh ngay, nhốt vào pending queue chờ nến T+1"""
        self.log_callback(f"[Backtest VTM] 🛑 Đánh chặn lệnh {order_type_str} - Đưa vào hàng đợi T+1.")
        self.pending_orders.append({
            "symbol": symbol,
            "order_type_str": order_type_str,
            "lot_size": lot_size,
            "sl_pips": sl_pips,
            "tp_pips": tp_pips,
            "preds_info": preds_info,
            "point": point
        })
        # Trả về ticket ảo để logic execute_trade không bị lỗi
        return self.virtual_ticket_counter + 1

    def update_virtual_positions_ohlc(self, open_p: float, high_p: float, low_p: float, close_p: float, point: float, spread_pips: float = 1.0, slippage_pips: float = 1.5):
        """Hàm MỚI: Cập nhật vị thế dùng cả 4 giá OHLC của nến M1 hiện tại"""
        
        # 1. THỰC THI LỆNH T+1 TẠI GIÁ OPEN
        if self.pending_orders:
            for order in self.pending_orders:
                o_bid = open_p
                o_ask = open_p + (spread_pips * point * 10)
                
                # Trượt giá (Penalty): Mua giá cao hơn, Bán giá thấp hơn
                if order["order_type_str"] == "BUY":
                    exec_ask = o_ask + (slippage_pips * point * 10)
                    exec_bid = o_bid + (slippage_pips * point * 10)
                else:
                    exec_bid = o_bid - (slippage_pips * point * 10)
                    exec_ask = o_ask - (slippage_pips * point * 10)

                # Gọi super() để xuyên qua Override, dùng logic tạo state GỐC của Bot Live
                self.log_callback(f"[Backtest VTM] ⚡ Khớp lệnh T+1 {order['order_type_str']} tại giá Open+Slippage.")
                super().open_new_mt5_trade(
                    symbol=order["symbol"],
                    order_type_str=order["order_type_str"],
                    lot_size=order["lot_size"],
                    sl_pips=order["sl_pips"],
                    tp_pips=order["tp_pips"],
                    preds_info=order["preds_info"],
                    current_bid=exec_bid,
                    current_ask=exec_ask,
                    point=order["point"]
                )
            self.pending_orders.clear()

        # 2. QUÉT SL/TP BẰNG HIGH/LOW & TÍNH TRAILING/PNL BẰNG CLOSE
        closed_tickets = []
        # Giả định cơ bản: 1 lot standard -> 10$/pip (Có thể tùy chỉnh theo công thức thật)
        pip_value_multiplier = 10.0 

        for ticket, pos in self.active_trade_loggers.items():
            hit_sl = False
            hit_tp = False
            close_price = 0.0

            # --- Quét SL/TP ---
            if pos["order_type"] == "MUA":
                if low_p <= pos["sl"]: 
                    hit_sl = True; close_price = pos["sl"]
                elif high_p >= pos["tp"]: 
                    hit_tp = True; close_price = pos["tp"]
            else: # BÁN (Cộng spread vào đỉnh/đáy để ra ask)
                ask_high = high_p + (spread_pips * point * 10)
                ask_low  = low_p + (spread_pips * point * 10)
                
                if ask_high >= pos["sl"]: 
                    hit_sl = True; close_price = pos["sl"]
                elif ask_low <= pos["tp"]: 
                    hit_tp = True; close_price = pos["tp"]

            if hit_sl or hit_tp:
                reason = "SL Hit" if hit_sl else "TP Hit"
                # Tính PnL chốt sổ chính xác theo giá quét
                if pos["order_type"] == "MUA":
                    final_pips = (close_price - pos["entry_price"]) / (point * 10)
                else:
                    final_pips = (pos["entry_price"] - close_price) / (point * 10)
                
                pos["current_profit"] = final_pips * pos["volume"] * pip_value_multiplier
                self._close_position_internal(ticket, close_price, reason)
                closed_tickets.append(ticket)
                continue

            # --- Cập nhật PnL thả nổi và Trailing Stop (Bằng giá Close) ---
            close_ask = close_p + (spread_pips * point * 10)
            if pos["order_type"] == "MUA":
                float_pips = (close_p - pos["entry_price"]) / (point * 10)
            else:
                float_pips = (pos["entry_price"] - close_ask) / (point * 10)
            
            pos["current_profit"] = float_pips * pos["volume"] * pip_value_multiplier
            self._dynamic_trailing_stop(ticket, pos, close_p, close_ask, point)

        for t in closed_tickets:
            self.active_trade_loggers.pop(t, None)
        if closed_tickets:
            self._save_state()

    def _close_position_internal(self, ticket, close_price, reason):
        super()._close_position_internal(ticket, close_price, reason)
        if self.history_deals and self.sim_clock:
            from datetime import datetime, timezone
            self.history_deals[-1]["close_time"] = datetime.fromtimestamp(self.sim_clock, tz=timezone.utc)
