import time
import os
import ccxt
from datetime import datetime
from dotenv import load_dotenv

class BinanceTradeManagerV3:
    """Quản lý thực thi lệnh Giao dịch lên máy chủ Binance Futures dựa trên tín hiệu AI V3."""

    def __init__(self, target_symbol: str, config: dict, log_callback=None, tg_notify_callback=None):
        self.target_symbol = target_symbol # e.g. "LTCUSDT"
        self.config = config
        self.log_callback = log_callback or print
        self.tg_notify = tg_notify_callback or (lambda x: None)

        self.active_trade_loggers: dict = {}
        self.gui_action: str = "-"
        self.gui_thr_text: str = "-"

        self.exchange = None
        self.last_close_time = 0
        
        load_dotenv()
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.secret_key = os.getenv("BINANCE_SECRET_KEY")

    def init_client(self) -> bool:
        if not self.api_key or not self.secret_key:
            self.log_callback("[BinanceTradeManagerV3] ❌ Thiếu BINANCE_API_KEY hoặc SECRET_KEY trong .env")
            return False
            
        try:
            self.exchange = ccxt.binanceusdm({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True
                }
            })
            
            self.exchange.load_markets()
            try:
                self.exchange.load_time_difference()
            except Exception as e:
                self.log_callback(f"[BinanceTradeManagerV3] ⚠️ Không thể đồng bộ time offset: {e}")
            self.log_callback("[BinanceTradeManagerV3] ✅ Module CCXT đã kết nối Binance Futures.")
            
            # Setup đòn bẩy
            exec_cfg = self.config.get("LIVE_BOT", {}).get("BINANCE_EXECUTION", {})
            leverage = exec_cfg.get("LEVERAGE", 10)
            target_binance_sym = self._format_symbol(self.target_symbol)
            try:
                self.exchange.set_leverage(leverage, target_binance_sym)
                self.log_callback(f"[BinanceTradeManagerV3] ✅ Đã set Leverage = {leverage} cho {target_binance_sym}")
            except Exception as set_lvg_err:
                self.log_callback(f"[BinanceTradeManagerV3] ⚠️ Không thể set margin: {set_lvg_err}")

            return True
        except Exception as e:
            self.log_callback(f"[BinanceTradeManagerV3] ❌ Cảnh báo kết nối CCXT: {e}")
            return False

    def _format_symbol(self, sym: str) -> str:
        # Chuyển "LTCUSDT" -> "LTC/USDT"
        sym = sym.replace("m", "").replace(".a", "")
        if "USDT" in sym:
            return sym.replace("USDT", "/USDT")
        return sym

    def _safe_api_call(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "-1021" in str(e) or "Timestamp for this request" in str(e):
                self.log_callback(f"[BinanceTradeManagerV3] ⚠️ Lỗi timestamp (-1021). Đang tự động đồng bộ lại thời gian với máy chủ Binance...")
                try:
                    self.exchange.load_time_difference()
                except Exception as sync_err:
                    pass
                return func(*args, **kwargs)
            raise e

    def sync_existing_positions(self, symbol: str = None):
        if not self.exchange: return
        try:
            target_binance_sym = self._format_symbol(symbol or self.target_symbol)
            positions = self._safe_api_call(self.exchange.fetch_positions, symbols=[target_binance_sym])
            for pos in positions:
                contracts = float(pos.get("contracts", 0))
                if contracts > 0:
                    side = pos.get('side', 'long').upper() # "long" / "short"
                    o_type = "MUA" if side == "LONG" else "BÁN"
                    ticket = f"pos_{target_binance_sym}_{side}"
                    
                    if ticket not in self.active_trade_loggers:
                        raw_ts = pos.get('timestamp')
                        if not raw_ts and 'info' in pos:
                            raw_ts = pos['info'].get('updateTime')
                        
                        entry_time_sec = float(raw_ts) / 1000.0 if raw_ts else time.time()
                        
                        self.active_trade_loggers[ticket] = {
                            "status": "OPEN",
                            "entry_price": float(pos.get("entryPrice", 0)),
                            "order_type": o_type,
                            "entry_time": entry_time_sec,
                            "contracts": contracts,
                            "side": side
                        }
        except Exception as e:
            self.log_callback(f"[BinanceTradeManagerV3] ⚠️ Lỗi sync_existing_positions: {e}")

    def get_active_positions_report(self) -> str:
        """Returns a string summarizing current active positions and their P/L."""
        if not self.exchange: return ""
        try:
            target_binance_sym = self._format_symbol(self.target_symbol)
            positions = self._safe_api_call(self.exchange.fetch_positions, symbols=[target_binance_sym])
            active = [p for p in positions if float(p.get("contracts", 0)) > 0]
            if not active: return ""
            
            reports = []
            for pos in active:
                pnl = float(pos.get("unrealizedProfit", 0))
                pnl_icon = "🟢" if pnl >= 0 else "🔴"
                side = pos.get('side', '').upper()
                ticket = f"pos_{target_binance_sym}_{side}"
                logger_pos = self.active_trade_loggers.get(ticket, {})
                entry_time = logger_pos.get("entry_time", time.time())
                elapsed_mins = int((time.time() - entry_time) / 60)
                reports.append(f"{pnl_icon} {side} {target_binance_sym} ({elapsed_mins}p): {pnl:+.2f}$")
            
            return "Vị thế Binance hiện tại:\n" + "\n".join(reports)
        except Exception as e:
            self.log_callback(f"[BinanceTradeManagerV3] ⚠️ get_active_positions_report lỗi: {e}")
            return ""

    def close_binance_position(self, pos_info: dict, close_reason: str = "AAMT V3 Signal") -> bool:
        if not self.exchange: return False
        try:
            target_binance_sym = self._format_symbol(self.target_symbol)
            contracts = pos_info["contracts"]
            side = pos_info["side"]
            
            # Đóng lệnh = mở ngược lại
            close_side = 'sell' if side == 'LONG' else 'buy'
            
            # Hủy hết lệnh open orders (như SL/TP)
            self._safe_api_call(self.exchange.cancel_all_orders, target_binance_sym)
            
            # Bắn market order để đóng
            order = self._safe_api_call(
                self.exchange.create_order,
                symbol=target_binance_sym,
                type='market',
                side=close_side,
                amount=contracts,
                params={"reduceOnly": True}
            )
            
            ticket = f"pos_{target_binance_sym}_{side}"
            self.active_trade_loggers.pop(ticket, None)
            self.last_close_time = time.time()
            
            self.log_callback(f"[BinanceTradeManagerV3] ✅ Đóng lệnh {side} thành công.")
            self.tg_notify(f"🔴 AI V3 Binance Close | {target_binance_sym}\nLý do: {close_reason}")
            return True
        except Exception as e:
            self.log_callback(f"[BinanceTradeManagerV3] ❌ Lỗi đóng lệnh: {e}")
            return False

    def open_new_binance_trade(self, order_type: str, lot_size: float, sl_pct: float, tp_pct: float, preds_info: str):
        if not self.exchange: return None
        target_binance_sym = self._format_symbol(self.target_symbol)
        
        try:
            ticker = self._safe_api_call(self.exchange.fetch_ticker, target_binance_sym)
            current_price = ticker['last']
            
            # Tính SL TP Absolute
            if order_type == "BUY":
                side = "buy"
                sl_price = current_price * (1 - sl_pct)
                tp_price = current_price * (1 + tp_pct)
                pos_side = "LONG"
            else:
                side = "sell"
                sl_price = current_price * (1 + sl_pct)
                tp_price = current_price * (1 - tp_pct)
                pos_side = "SHORT"
                
            # 1. Mở Market Order
            order = self._safe_api_call(
                self.exchange.create_order,
                symbol=target_binance_sym,
                type='market',
                side=side,
                amount=lot_size
            )
            
            time.sleep(1)
            
            # 2. Đặt SL (STOP_MARKET) & TP (TAKE_PROFIT_MARKET)
            sl_side = "sell" if side == "buy" else "buy"
            
            try:
                sl_order = self._safe_api_call(
                    self.exchange.create_order,
                    symbol=target_binance_sym,
                    type='STOP_MARKET',
                    side=sl_side,
                    amount=lot_size,
                    params={
                        'stopPrice': self.exchange.price_to_precision(target_binance_sym, sl_price),
                        'reduceOnly': True
                    }
                )
                self.log_callback(f"[BinanceTradeManagerV3] ✅ Đã đặt Stop Loss tại {sl_price:.2f}")
            except Exception as estop:
                self.log_callback(f"[BinanceTradeManagerV3] ⚠️ Lỗi đặt StopLoss: {estop}")
            
            try:
                tp_order = self._safe_api_call(
                    self.exchange.create_order,
                    symbol=target_binance_sym,
                    type='TAKE_PROFIT_MARKET',
                    side=sl_side,
                    amount=lot_size,
                    params={
                        'stopPrice': self.exchange.price_to_precision(target_binance_sym, tp_price),
                        'reduceOnly': True
                    }
                )
                self.log_callback(f"[BinanceTradeManagerV3] ✅ Đã đặt Take Profit tại {tp_price:.2f}")
            except Exception as etp:
                self.log_callback(f"[BinanceTradeManagerV3] ⚠️ Lỗi đặt TakeProfit: {etp}")

            ticket = f"pos_{target_binance_sym}_{pos_side}"
            self.active_trade_loggers[ticket] = {
                "status": "OPEN", "entry_price": float(current_price),
                "order_type": "MUA" if side == "buy" else "BÁN",
                "entry_time": time.time(), "contracts": lot_size, "side": pos_side
            }
            
            # Ghi log cục bộ
            self.log_callback(f"[BinanceTradeManagerV3] ✅ ĐÃ BẮN LỆNH {'MUA' if side=='buy' else 'BÁN'} thành công! Symbol: {target_binance_sym} | L: {lot_size} | Giá: {current_price}")
            
            self.tg_notify(f"🟢 AI V3 Binance Open {'MUA' if side=='buy' else 'BÁN'} (Market)\nSymbol: {target_binance_sym} | L: {lot_size}\nSL: {sl_price:.2f} | TP: {tp_price:.2f}\n{preds_info}")
            return ticket
            
        except Exception as e:
            self.log_callback(f"[BinanceTradeManagerV3] ❌ Lỗi mở lệnh: {e}")
            return None

    def execute_trade(self, action: str, probs_dict: dict, mse_loss: float, actual_target_sym: str = None):
        if not self.exchange: return
        target_binance_sym = self._format_symbol(self.target_symbol)
        
        exec_cfg = self.config.get("LIVE_BOT", {}).get("BINANCE_EXECUTION", {})
        lot_size = exec_cfg.get("LOT_SIZE", 0.5)
        
        # Crypto config uses PCT directly instead of PIPS
        fe_cfg = self.config.get("FEATURE_ENGINEERING", {})
        sl_pct = fe_cfg.get("SL_PCT", 0.003)
        tp_pct = fe_cfg.get("TP_PCT", 0.003)
        
        preds_info = f"MSE:{mse_loss:.3f} | B:{probs_dict.get('buy',0):.2f} S:{probs_dict.get('sell',0):.2f}"

        # Fetch Active Positions
        try:
            positions = self._safe_api_call(self.exchange.fetch_positions, symbols=[target_binance_sym])
            active_positions = [p for p in positions if float(p.get("contracts", 0)) > 0]
        except Exception as e:
            self.log_callback(f"Lỗi fetch positions Binance: {e}")
            active_positions = []

        has_open = len(active_positions) > 0
        just_closed = False

        max_hold_bars = fe_cfg.get("MAX_HOLD_BARS", 20)
        max_hold_seconds = max_hold_bars * 60

        for pos in active_positions:
            side = pos.get('side', '').upper()
            contracts = float(pos.get("contracts", 0))
            pos_dict = {"side": side, "contracts": contracts}
            
            # Kiểm tra thời gian giữ lệnh quá hạn
            target_binance_sym = self._format_symbol(self.target_symbol)
            ticket = f"pos_{target_binance_sym}_{side}"
            logger_pos = self.active_trade_loggers.get(ticket)
            
            if logger_pos and (time.time() - logger_pos.get("entry_time", time.time())) > max_hold_seconds:
                self.gui_action = f"CHỐT: QUÁ GIỜ (>{max_hold_bars} nến)"
                if self.close_binance_position(pos_dict, f"Giữ lệnh quá {max_hold_bars} phút"):
                    has_open = False
                    just_closed = True
            elif side == "LONG" and action == "SELL":
                self.gui_action = f"ĐẢO CHIỀU: CHỐT BUY"
                if self.close_binance_position(pos_dict, "Đảo chiều sang SELL"):
                    has_open = False
                    just_closed = True
            elif side == "SHORT" and action == "BUY":
                self.gui_action = f"ĐẢO CHIỀU: CHỐT SELL"
                if self.close_binance_position(pos_dict, "Đảo chiều sang BUY"):
                    has_open = False
                    just_closed = True
            elif action == "TÍN_HIỆU_RÁC" or action == "HOLD":
                self.gui_action = f"GIỮ LỆNH ({side})"

        if not has_open and not just_closed:
            now = time.time()
            if (now - self.last_close_time) < 60:
                self.gui_action = "Chờ Cooldown 60s..."
            else:
                if action == "BUY":
                    self.gui_action = "🔥 ĐÃ BẮN LỆNH MUA (BUY) LÊN BINANCE!"
                    self.open_new_binance_trade("BUY", lot_size, sl_pct, tp_pct, preds_info)
                elif action == "SELL":
                    self.gui_action = "🔥 ĐÃ BẮN LỆNH BÁN (SELL) LÊN BINANCE!"
                    self.open_new_binance_trade("SELL", lot_size, sl_pct, tp_pct, preds_info)
                else:
                    self.gui_action = f"Bỏ qua ({action})"

    def update_gui_threshold(self):
        bot_cfg = self.config.get("LIVE_BOT", {})
        mse_thr = bot_cfg.get("MSE_THRESHOLD_PERCENTILE", 70)
        prob_thr = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.7)
        self.gui_thr_text = f"🔥 Binance Phi Tiêu: Prob>{prob_thr} | Cảnh Báo: MSE>{mse_thr}"
