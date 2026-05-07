import time
import traceback
import ccxt
import json
import os
from datetime import datetime, time as dtime

class V3VirtualTradeManager:
    """Quản lý Giao dịch Ảo (Paper Trading) cho AI V3. 
    Không gửi lệnh lên MT5, mọi thứ được mô phỏng trên RAM.
    """

    def __init__(self, target_symbol: str, config: dict, log_callback=None, tg_notify_callback=None):
        self.target_symbol = target_symbol
        self.config = config
        self.log_callback = log_callback or print
        self.tg_notify = tg_notify_callback or (lambda x: None)

        self.active_trade_loggers: dict = {}
        self.gui_action: str = "-"
        self.gui_thr_text: str = "-"

        self._positions_synced = True
        self.last_close_time = 0
        
        self.virtual_balance = 10000.0  # Mặc định $10,000
        self.virtual_ticket_counter = 1000
        self.spread_pips = 0.0 # Giả định spread = 0 pips cho pure signal
        
        # Để lưu lại lịch sử
        self.history_deals = []

        # Tên file lưu trạng thái
        safe_name = self.target_symbol.replace("/", "_").replace("\\", "_")
        self.state_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", f"virtual_state_{safe_name}.json")
        
        self._load_state()

    def _save_state(self):
        try:
            state = {
                "virtual_balance": self.virtual_balance,
                "virtual_ticket_counter": self.virtual_ticket_counter,
                "active_trade_loggers": self.active_trade_loggers,
                "history_deals": []
            }
            
            # Serialize history_deals (handle datetimes)
            for deal in self.history_deals:
                d_copy = deal.copy()
                if isinstance(d_copy.get("close_time"), datetime):
                    d_copy["close_time"] = d_copy["close_time"].isoformat()
                state["history_deals"].append(d_copy)
                
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            self.log_callback(f"[VirtualTradeManager] ❌ Lỗi lưu trạng thái: {e}")

    def _load_state(self):
        try:
            if not os.path.exists(self.state_file):
                return
                
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                
            self.virtual_balance = state.get("virtual_balance", 10000.0)
            self.virtual_ticket_counter = state.get("virtual_ticket_counter", 1000)
            self.active_trade_loggers = state.get("active_trade_loggers", {})
            
            # Deserialize history_deals
            self.history_deals = []
            for deal in state.get("history_deals", []):
                if isinstance(deal.get("close_time"), str):
                    try:
                        deal["close_time"] = datetime.fromisoformat(deal["close_time"])
                    except: pass
                self.history_deals.append(deal)
                
            self.log_callback(f"[VirtualTradeManager] 📂 Đã tải trạng thái ảo từ file. Balance: {self.virtual_balance:.2f}$ | Lệnh đang mở: {len(self.active_trade_loggers)}")
        except Exception as e:
            self.log_callback(f"[VirtualTradeManager] ❌ Lỗi tải trạng thái: {e}")

    def init_mt5(self) -> bool:
        self.log_callback("[VirtualTradeManager] ✅ Đã kích hoạt chế độ PAPER TRADING (Giả lập giao dịch MT5).")
        return True

    def init_client(self) -> bool:
        self.log_callback("[VirtualTradeManager] ✅ Đã kích hoạt chế độ PAPER TRADING (Giả lập giao dịch Binance/Crypto).")
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        return True

    def sync_existing_positions(self, symbol: str = None):
        # Trong chế độ ảo, chúng ta duy trì trạng thái trên RAM
        pass

    def _get_daily_pnl(self) -> float:
        try:
            now = datetime.now().date()
            daily_profit = sum(d["profit"] for d in self.history_deals if d["close_time"].date() == now)
            return daily_profit
        except Exception:
            return 0.0

    def get_active_positions_report(self) -> str:
        if not self.active_trade_loggers: return ""
        
        reports = []
        for ticket, pos in self.active_trade_loggers.items():
            pnl = pos.get("current_profit", 0.0)
            pnl_icon = "🟢" if pnl >= 0 else "🔴"
            elapsed_mins = int((time.time() - pos.get("entry_time", time.time())) / 60)
            reports.append(f"{pnl_icon} {pos['order_type']} #{ticket} ({elapsed_mins}p): {pnl:+.2f}$")
        
        return "Vị thế ẢO hiện tại:\n" + "\n".join(reports) + f"\nSố dư ẢO: {self.virtual_balance:.2f}$"

    def update_virtual_positions(self, current_bid: float, current_ask: float, point: float):
        """Hàm này phải được gọi liên tục mỗi khi có Tick giá mới để mô phỏng Trailing Stop/PNL"""
        closed_tickets = []
        for ticket, pos in self.active_trade_loggers.items():
            # Tính PnL ảo (chưa bao gồm phí qua đêm)
            if pos["order_type"] == "MUA":
                pips_diff = (current_bid - pos["entry_price"]) / (point * 10)
            else:
                pips_diff = (pos["entry_price"] - current_ask) / (point * 10)
                
            # Đơn giản hóa: 1 pip = 1$ cho 0.01 lot standard? 
            # Phụ thuộc vào công thức thật, nhưng ta sẽ lấy đại khái 1 lot standard = 1 pip = $10 
            # Hoặc chỉ lưu Pips thay vì $ cho dễ nhìn.
            pip_value_usd = pos["volume"] * 10.0 # Tương đối
            current_profit = pips_diff * pip_value_usd
            pos["current_profit"] = current_profit
            
            # SL / TP Check
            hit_sl = False
            hit_tp = False
            close_price = 0.0
            
            if pos["order_type"] == "MUA":
                if current_bid <= pos["sl"]: hit_sl = True
                if current_bid >= pos["tp"]: hit_tp = True
                close_price = current_bid
            else:
                if current_ask >= pos["sl"]: hit_sl = True
                if current_ask <= pos["tp"]: hit_tp = True
                close_price = current_ask
                
            if hit_sl or hit_tp:
                reason = "SL Hit" if hit_sl else "TP Hit"
                self._close_position_internal(ticket, close_price, reason)
                closed_tickets.append(ticket)
                continue
                
            # Trailing Stop
            self._dynamic_trailing_stop(ticket, pos, current_bid, current_ask, point)
            
        for t in closed_tickets:
            self.active_trade_loggers.pop(t, None)
            
        if closed_tickets:
            self._save_state()

    def _close_position_internal(self, ticket: int, close_price: float, reason: str):
        pos = self.active_trade_loggers.get(ticket)
        if not pos: return False
        
        profit = pos.get("current_profit", 0.0)
        self.virtual_balance += profit
        
        deal = {
            "ticket": ticket,
            "order_type": pos["order_type"],
            "entry_price": pos["entry_price"],
            "close_price": close_price,
            "profit": profit,
            "close_time": datetime.now(),
            "reason": reason
        }
        self.history_deals.append(deal)
        self.last_close_time = time.time()
        
        msg = f"[VirtualTradeManager] ✅ Đóng ẢO lệnh #{ticket} ({reason}). PnL: {profit:+.2f}$ | Balance: {self.virtual_balance:.2f}$"
        self.log_callback(msg)
        self.tg_notify(f"🔴 AI V3 Close VIRTUAL | {self.target_symbol} | #{ticket}\nLý do: {reason}\nPnL: {profit:+.2f}$")
        return True

    def close_mt5_position(self, pos_or_ticket, close_reason: str = "AAMT V3 Signal") -> bool:
        # Nếu truyền vào ticket (do ta mô phỏng)
        ticket = pos_or_ticket if isinstance(pos_or_ticket, int) else pos_or_ticket.get("ticket")
        if not ticket: return False
        
        pos = self.active_trade_loggers.get(ticket)
        if not pos: return False
        
        # Vì đây là lệnh do AI đóng (Đảo chiều), ta coi giá đóng = Entry Price để đơn giản, 
        # Hoặc lấy tạm giá hiện tại nếu có. Trong execute_trade chưa có giá tick. 
        # Tạm tính profit đang lưu.
        return self._close_position_internal(ticket, 0.0, close_reason) # 0.0 vì không quan trọng nếu đã có current_profit

    def open_new_mt5_trade(self, symbol: str, order_type_str: str, lot_size: float, sl_pips: float, tp_pips: float, preds_info: str, current_bid: float, current_ask: float, point: float):
        try:
            self.virtual_ticket_counter += 1
            ticket = self.virtual_ticket_counter
            
            if order_type_str == "BUY":
                price = current_ask + (self.spread_pips * point * 10)
                sl = price - sl_pips * 10 * point
                tp = price + tp_pips * 10 * point
                o_type_vn = "MUA"
            else:
                price = current_bid - (self.spread_pips * point * 10)
                sl = price + sl_pips * 10 * point
                tp = price - tp_pips * 10 * point
                o_type_vn = "BÁN"
                
            self.active_trade_loggers[ticket] = {
                "ticket": ticket,
                "status": "OPEN", 
                "entry_price": float(price),
                "order_type": o_type_vn,
                "volume": float(lot_size),
                "sl": float(sl),
                "tp": float(tp),
                "entry_time": time.time(),
                "current_profit": 0.0
            }
            
            self.log_callback(f"[VirtualTradeManager] ✅ ĐÃ BẮN LỆNH ẢO {o_type_vn}! Ticket: #{ticket} | Giá: {price:.3f} | SL: {sl:.3f} | TP: {tp:.3f}")
            self.tg_notify(f"🟢 AI V3 Open ẢO {o_type_vn}\nSymbol: {symbol} | #{ticket} | {preds_info}")
            
            self._save_state()
            return ticket
        except Exception as e:
            self.log_callback(f"[VirtualTradeManager] ❌ Lỗi mở lệnh ảo: {e}")
            return None

    def _dynamic_trailing_stop(self, ticket: int, pos: dict, current_bid: float, current_ask: float, point: float):
        live_cfg = self.config.get("FEATURE_ENGINEERING", {})
        sl_pips = live_cfg.get("sl_pips", 50)
        min_sl_pips = live_cfg.get("min_sl_pips", 15)
        
        pip_value = 10 * point
        ST_nguong_raw = sl_pips * pip_value
        ST_min_raw = min_sl_pips * pip_value
        
        elapsed_time = time.time() - pos["entry_time"]
        ST_dong = ST_nguong_raw - (ST_nguong_raw / 600.0) * elapsed_time
        if ST_dong < ST_min_raw: ST_dong = ST_min_raw
            
        current_sl = pos["sl"]
        step_min = 3 * pip_value 
        updated = False
        
        if pos["order_type"] == "MUA":
            if (current_bid - pos["entry_price"]) > ST_dong:
                calc_sl = current_bid - ST_dong
                if current_sl == 0.0 or (calc_sl - current_sl) > step_min:
                    pos["sl"] = calc_sl
                    updated = True
        else:
            if (pos["entry_price"] - current_ask) > ST_dong:
                calc_sl = current_ask + ST_dong
                if current_sl == 0.0 or (current_sl - calc_sl) > step_min:
                    pos["sl"] = calc_sl
                    updated = True
                    
        if updated:
            self.log_callback(f"[VirtualTradeManager] 🔵 Đã dời SL ảo cho lệnh #{ticket} -> {pos['sl']:.3f}")
            self._save_state()

    def _format_symbol(self, sym: str) -> str:
        if "USDT" in sym and "/" not in sym:
            return sym.replace("USDT", "/USDT")
        return sym

    def execute_trade(self, action: str, probs_dict: dict, mse_loss: float, current_bid: float, current_ask: float, point: float, actual_target_sym: str = None):
        symbol = actual_target_sym or self.target_symbol
        
        live_cfg = self.config.get("FEATURE_ENGINEERING", {})
        cfg_lot  = live_cfg.get("lot_size", 0.01)
        cfg_sl   = live_cfg.get("SL_PIPS", 15)
        cfg_tp   = live_cfg.get("TP_PIPS", 15)
        
        preds_info = f"MSE:{mse_loss:.3f} | B:{probs_dict.get('buy',0):.2f} S:{probs_dict.get('sell',0):.2f}"

        has_open = len(self.active_trade_loggers) > 0
        just_closed = False
        closed_tickets = []

        max_hold_bars = live_cfg.get("MAX_HOLD_BARS", 20)
        max_hold_seconds = max_hold_bars * 60

        # Convert dict to list to safely mutate during iteration? We actually pop later.
        for ticket, pos in self.active_trade_loggers.items():
            if (time.time() - pos["entry_time"]) > max_hold_seconds:
                self.gui_action = f"CHỐT ẢO: QUÁ GIỜ (>{max_hold_bars} nến)"
                if self.close_mt5_position(ticket, f"Giữ lệnh quá {max_hold_bars} phút"):
                    has_open = False
                    just_closed = True
                    closed_tickets.append(ticket)
            elif pos["order_type"] == "MUA" and action == "SELL":
                self.gui_action = f"ĐẢO CHIỀU: CHỐT BUY ẢO (#{ticket})"
                if self.close_mt5_position(ticket, "Đảo chiều sang SELL"):
                    has_open = False
                    just_closed = True
                    closed_tickets.append(ticket)
            elif pos["order_type"] == "BÁN" and action == "BUY":
                self.gui_action = f"ĐẢO CHIỀU: CHỐT SELL ẢO (#{ticket})"
                if self.close_mt5_position(ticket, "Đảo chiều sang BUY"):
                    has_open = False
                    just_closed = True
                    closed_tickets.append(ticket)
            elif action == "TÍN_HIỆU_RÁC" or action == "HOLD":
                self.gui_action = f"GIỮ LỆNH ẢO (#{ticket}) [{action}]"

        for t in closed_tickets:
            self.active_trade_loggers.pop(t, None)

        if not has_open and not just_closed:
            now = time.time()
            if (now - self.last_close_time) < 60:
                self.gui_action = "Chờ Cooldown 60s..."
            else:
                if action == "BUY":
                    self.gui_action = "🔥 ĐÃ BẮN LỆNH MUA ẢO!"
                    self.open_new_mt5_trade(symbol, "BUY", cfg_lot, cfg_sl, cfg_tp, preds_info, current_bid, current_ask, point)
                elif action == "SELL":
                    self.gui_action = "🔥 ĐÃ BẮN LỆNH BÁN ẢO!"
                    self.open_new_mt5_trade(symbol, "SELL", cfg_lot, cfg_sl, cfg_tp, preds_info, current_bid, current_ask, point)
                else:
                    self.gui_action = f"Bỏ qua ({action})"

    def update_gui_threshold(self):
        bot_cfg = self.config.get("LIVE_BOT", {})
        mse_thr = bot_cfg.get("MSE_THRESHOLD_PERCENTILE", 70)
        prob_thr = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.7)
        self.gui_thr_text = f"🔥 VIRTUAL Phi Tiêu: Prob>{prob_thr} | Cảnh Báo Lạ: MSE>{mse_thr}"
