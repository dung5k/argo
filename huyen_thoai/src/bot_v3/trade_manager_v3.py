import time
import traceback
from datetime import datetime, time as dtime

class V3TradeManager:
    """Quản lý thực thi lệnh Giao dịch lên máy chủ MT5 dựa trên tín hiệu AI V3."""

    MAGIC_NUMBER = 101010

    def __init__(self, target_symbol: str, config: dict, log_callback=None, tg_notify_callback=None):
        self.target_symbol = target_symbol
        self.config = config
        self.log_callback = log_callback or print
        self.tg_notify = tg_notify_callback or (lambda x: None)

        self.active_trade_loggers: dict = {}
        self.gui_action: str = "-"
        self.gui_thr_text: str = "-"

        self.mt5 = None
        self._positions_synced = False
        self.last_close_time = 0

    def init_mt5(self) -> bool:
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.log_callback("[TradeManagerV3] ✅ Module MT5 đã sẵn sàng.")
            return True
        except ImportError:
            self.log_callback("[TradeManagerV3] ❌ Module MetaTrader5 không tồn tại.")
            return False

    def sync_existing_positions(self, symbol: str = None):
        if not self.mt5:
            return
        sym = symbol or self.target_symbol
        try:
            positions = self.mt5.positions_get(symbol=sym) or []
            for pos in positions:
                if pos.ticket not in self.active_trade_loggers:
                    o_type = "MUA" if pos.type == self.mt5.ORDER_TYPE_BUY else "BÁN"
                    open_time_ts = getattr(pos, 'time', time.time())
                    self.active_trade_loggers[pos.ticket] = {
                        "status": "OPEN",
                        "entry_price": float(getattr(pos, 'price_open', 0.0)),
                        "order_type": o_type,
                        "entry_time": float(open_time_ts),
                        "last_pnl_notify_time": 0.0,
                    }
        except Exception as e:
            self.log_callback(f"[TradeManagerV3] ⚠️ sync_existing_positions lỗi: {e}")

    def _get_daily_pnl(self) -> float:
        if not self.mt5: return 0.0
        try:
            now = datetime.now()
            dt_from = datetime.combine(now.date(), dtime(0, 0, 0))
            deals = self.mt5.history_deals_get(dt_from, now)
            return sum(d.profit for d in deals) if deals else 0.0
        except Exception:
            return 0.0

    def get_active_positions_report(self) -> str:
        """Returns a string summarizing current active positions and their P/L."""
        if not self.mt5: return ""
        try:
            positions = self.mt5.positions_get(symbol=self.target_symbol) or []
            if not positions: return ""
            
            reports = []
            for pos in positions:
                pnl = pos.profit
                pnl_icon = "🟢" if pnl >= 0 else "🔴"
                o_type = "BUY" if pos.type == self.mt5.ORDER_TYPE_BUY else "SELL"
                elapsed_mins = int((time.time() - pos.time) / 60)
                reports.append(f"{pnl_icon} {o_type} #{pos.ticket} ({elapsed_mins}p): {pnl:+.2f}$")
            
            return "Vị thế hiện tại:\n" + "\n".join(reports)
        except Exception as e:
            self.log_callback(f"[TradeManagerV3] ⚠️ get_active_positions_report lỗi: {e}")
            return ""

    def _build_close_request(self, position) -> dict:
        tick = self.mt5.symbol_info_tick(position.symbol)
        if tick is None: raise ValueError(f"Không lấy được tick cho {position.symbol}")
        order_type = self.mt5.ORDER_TYPE_SELL if position.type == self.mt5.ORDER_TYPE_BUY else self.mt5.ORDER_TYPE_BUY
        price = tick.bid if position.type == self.mt5.ORDER_TYPE_BUY else tick.ask
        return {
            "action": self.mt5.TRADE_ACTION_DEAL, "symbol": position.symbol,
            "volume": position.volume, "type": order_type, "position": position.ticket,
            "price": price, "deviation": 20, "magic": self.MAGIC_NUMBER,
            "comment": "AAMT V3 Close", "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

    def _build_open_request(self, symbol: str, order_type, lot_size: float, sl_pips: float, tp_pips: float) -> dict:
        point_info = self.mt5.symbol_info(symbol)
        if not point_info: raise ValueError(f"Không lấy được symbol_info cho {symbol}")
        point = point_info.point
        tick = self.mt5.symbol_info_tick(symbol)
        if not tick: raise ValueError(f"Không lấy được tick cho {symbol}")

        if order_type == self.mt5.ORDER_TYPE_BUY:
            price = tick.ask
            sl = price - sl_pips * 10 * point
            tp = price + tp_pips * 10 * point
        else:
            price = tick.bid
            sl = price + sl_pips * 10 * point
            tp = price - tp_pips * 10 * point

        return {
            "action": self.mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": float(lot_size),
            "type": order_type, "price": price, "sl": float(sl), "tp": float(tp),
            "deviation": 20, "magic": self.MAGIC_NUMBER, "comment": "AAMT V3 Entry",
            "type_time": self.mt5.ORDER_TIME_GTC, "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

    def _send_order(self, request: dict) -> tuple:
        result = self.mt5.order_send(request)
        if result is None: return False, None
        return result.retcode == self.mt5.TRADE_RETCODE_DONE, result

    def close_mt5_position(self, position, close_reason: str = "AAMT V3 Signal") -> bool:
        if not self.mt5: return False
        try:
            req = self._build_close_request(position)
            success, result = self._send_order(req)
            if success:
                self.active_trade_loggers.pop(position.ticket, None)
                self.last_close_time = time.time()
                self.log_callback(f"[TradeManagerV3] ✅ Đóng lệnh #{position.ticket} thành công.")
                self.tg_notify(f"🔴 AI V3 Close | {position.symbol} | #{position.ticket}\nLý do: {close_reason}")
                return True
        except Exception as e:
            self.log_callback(f"[TradeManagerV3] ❌ Lỗi đóng lệnh: {e}")
        return False

    def open_new_mt5_trade(self, symbol: str, order_type, lot_size: float, sl_pips: float, tp_pips: float, preds_info: str):
        if not self.mt5: return None
        try:
            req = self._build_open_request(symbol, order_type, lot_size, sl_pips, tp_pips)
            success, result = self._send_order(req)
            if success:
                ticket = result.order
                self.active_trade_loggers[ticket] = {
                    "status": "OPEN", "entry_price": float(req['price']),
                    "order_type": "MUA" if order_type == self.mt5.ORDER_TYPE_BUY else "BÁN",
                    "entry_time": time.time(), "last_pnl_notify_time": time.time()
                }
                
                # Ghi log cục bộ để không bị mất dấu vết
                self.log_callback(f"[TradeManagerV3] ✅ ĐÃ BẮN LỆNH {'MUA' if order_type==self.mt5.ORDER_TYPE_BUY else 'BÁN'} thành công! Ticket: #{ticket} | Giá: {req['price']}")
                
                self.tg_notify(f"🟢 AI V3 Open {'MUA' if order_type==self.mt5.ORDER_TYPE_BUY else 'BÁN'}\nSymbol: {symbol} | #{ticket} | {preds_info}")
                return ticket
            else:
                err_msg = f"[TradeManagerV3] ❌ Lỗi MT5: {result.comment if result else 'Unknown'}"
                self.log_callback(err_msg)
                self.tg_notify(err_msg)
        except Exception as e:
            self.log_callback(f"[TradeManagerV3] ❌ Lỗi mở lệnh: {e}")
        return None

    def _dynamic_trailing_stop(self, pos, live_cfg: dict):
        sl_pips = live_cfg.get("sl_pips", 50)
        min_sl_pips = live_cfg.get("min_sl_pips", 15)
        
        point_info = self.mt5.symbol_info(pos.symbol)
        if not point_info: return
        pip_value = 10 * point_info.point
        
        ST_nguong_raw = sl_pips * pip_value
        ST_min_raw = min_sl_pips * pip_value
        elapsed_time = time.time() - pos.time
        ST_dong = ST_nguong_raw - (ST_nguong_raw / 600.0) * elapsed_time
        if ST_dong < ST_min_raw: ST_dong = ST_min_raw
            
        current_sl = pos.sl
        step_min = 3 * pip_value 
        updated, new_sl = False, current_sl
        
        if pos.type == self.mt5.ORDER_TYPE_BUY:
            if (pos.price_current - pos.price_open) > ST_dong:
                calc_sl = pos.price_current - ST_dong
                if current_sl == 0.0 or (calc_sl - current_sl) > step_min:
                    new_sl, updated = calc_sl, True
        else:
            if (pos.price_open - pos.price_current) > ST_dong:
                calc_sl = pos.price_current + ST_dong
                if current_sl == 0.0 or (current_sl - calc_sl) > step_min:
                    new_sl, updated = calc_sl, True
                    
        if updated:
            req = {"action": self.mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "symbol": pos.symbol, "sl": float(new_sl), "tp": float(pos.tp), "magic": self.MAGIC_NUMBER}
            self._send_order(req)

    def execute_trade(self, action: str, probs_dict: dict, mse_loss: float, actual_target_sym: str = None):
        if not self.mt5: return
        symbol = actual_target_sym or self.target_symbol
        
        live_cfg = self.config.get("FEATURE_ENGINEERING", {}) # In V3, SL TP is under FE!
        cfg_lot  = live_cfg.get("lot_size", 0.01) # V3 might not have it in FE, so default 0.01
        cfg_sl   = live_cfg.get("SL_PIPS", 15)
        cfg_tp   = live_cfg.get("TP_PIPS", 15)
        
        preds_info = f"MSE:{mse_loss:.3f} | B:{probs_dict.get('buy',0):.2f} S:{probs_dict.get('sell',0):.2f}"

        positions = self.mt5.positions_get(symbol=symbol) or []
        has_open = len(positions) > 0
        just_closed = False

        for pos in positions:
            self._dynamic_trailing_stop(pos, live_cfg)
            
            # Đảo chiều tín hiệu -> cắt lệnh cũ
            if pos.type == self.mt5.ORDER_TYPE_BUY and action == "SELL":
                self.gui_action = f"ĐẢO CHIỀU: CHỐT BUY (#{pos.ticket})"
                if self.close_mt5_position(pos, "Đảo chiều sang SELL"):
                    has_open = False
                    just_closed = True
            elif pos.type == self.mt5.ORDER_TYPE_SELL and action == "BUY":
                self.gui_action = f"ĐẢO CHIỀU: CHỐT SELL (#{pos.ticket})"
                if self.close_mt5_position(pos, "Đảo chiều sang BUY"):
                    has_open = False
                    just_closed = True
            elif action == "TÍN_HIỆU_RÁC" or action == "HOLD":
                self.gui_action = f"GIỮ LỆNH (#{pos.ticket}) [{action}]"

        if not has_open and not just_closed:
            now = time.time()
            if (now - self.last_close_time) < 60:
                self.gui_action = "Chờ Cooldown 60s..."
            else:
                if action == "BUY":
                    self.gui_action = "🔥 ĐÃ BẮN LỆNH MUA (BUY)!"
                    self.open_new_mt5_trade(symbol, self.mt5.ORDER_TYPE_BUY, cfg_lot, cfg_sl, cfg_tp, preds_info)
                elif action == "SELL":
                    self.gui_action = "🔥 ĐÃ BẮN LỆNH BÁN (SELL)!"
                    self.open_new_mt5_trade(symbol, self.mt5.ORDER_TYPE_SELL, cfg_lot, cfg_sl, cfg_tp, preds_info)
                else:
                    self.gui_action = f"Bỏ qua ({action})"

    def update_gui_threshold(self):
        bot_cfg = self.config.get("LIVE_BOT", {})
        mse_thr = bot_cfg.get("MSE_THRESHOLD_PERCENTILE", 70)
        prob_thr = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.7)
        self.gui_thr_text = f"🔥 V3 Phi Tiêu: Prob>{prob_thr} | Cảnh Báo Lạ: MSE>{mse_thr}"
