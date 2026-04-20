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
        self.api_key = os.getenv("BINANCE_DEMO_API_KEY")
        self.secret_key = os.getenv("BINANCE_DEMO_SECRET_KEY")

    def init_client(self) -> bool:
        if not self.api_key or not self.secret_key:
            self.log_callback("[BinanceTradeManagerV3] ❌ Thiếu BINANCE_DEMO_API_KEY hoặc SECRET_KEY trong .env")
            return False
            
        try:
            self.exchange = ccxt.binanceusdm({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future'
                }
            })
            
            # Kích hoạt chế độ Demo bằng cách đè URL API
            if os.getenv("BINANCE_FUTURES_DEMO", "True").lower() == "true":
                self.exchange.set_sandbox_mode(True) # Set first to populate the structure
                
                # Iterate and replace domain
                for k, v in self.exchange.urls['api'].items():
                    if isinstance(v, str) and 'testnet.binancefuture.com' in v:
                        self.exchange.urls['api'][k] = v.replace('testnet.binancefuture.com', 'demo-fapi.binance.com')
                    elif isinstance(v, str) and 'testnet.binance.vision' in v:
                        self.exchange.urls['api'][k] = v.replace('testnet.binance.vision', 'demo-fapi.binance.com')
                        
            self.exchange.load_markets()
            self.log_callback("[BinanceTradeManagerV3] ✅ Module CCXT đ kết nối Binance Futures (Demo).")
            
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

    def sync_existing_positions(self, symbol: str = None):
        if not self.exchange: return
        try:
            target_binance_sym = self._format_symbol(symbol or self.target_symbol)
            positions = self.exchange.fetch_positions(symbols=[target_binance_sym])
            for pos in positions:
                contracts = float(pos.get("contracts", 0))
                if contracts > 0:
                    side = pos.get('side', 'long').upper() # "long" / "short"
                    o_type = "MUA" if side == "LONG" else "BÁN"
                    ticket = f"pos_{target_binance_sym}_{side}"
                    
                    if ticket not in self.active_trade_loggers:
                        self.active_trade_loggers[ticket] = {
                            "status": "OPEN",
                            "entry_price": float(pos.get("entryPrice", 0)),
                            "order_type": o_type,
                            "entry_time": time.time(),
                            "contracts": contracts,
                            "side": side
                        }
        except Exception as e:
            self.log_callback(f"[BinanceTradeManagerV3] ⚠️ Lỗi sync_existing_positions: {e}")

    def close_binance_position(self, pos_info: dict, close_reason: str = "AAMT V3 Signal") -> bool:
        if not self.exchange: return False
        try:
            target_binance_sym = self._format_symbol(self.target_symbol)
            contracts = pos_info["contracts"]
            side = pos_info["side"]
            
            # Đóng lệnh = mở ngược lại
            close_side = 'sell' if side == 'LONG' else 'buy'
            
            # Hủy hết lệnh open orders (như SL/TP)
            self.exchange.cancel_all_orders(target_binance_sym)
            
            # Bắn market order để đóng
            order = self.exchange.create_order(
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
            ticker = self.exchange.fetch_ticker(target_binance_sym)
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
            order = self.exchange.create_order(
                symbol=target_binance_sym,
                type='market',
                side=side,
                amount=lot_size
            )
            
            time.sleep(1)
            
            # 2. Đặt SL (STOP_MARKET) & TP (TAKE_PROFIT_MARKET) - Binance Futures cần ReduceOnly
            sl_side = "sell" if side == "buy" else "buy"
            
            try:
                self.exchange.create_order(
                    symbol=target_binance_sym,
                    type='stopMarket',
                    side=sl_side,
                    amount=lot_size,
                    params={'stopPrice': sl_price, 'reduceOnly': True}
                )
            except Exception as estop:
                self.log_callback(f"⚠️ Lỗi đặ StopMarket: {estop}")
            
            try:
                self.exchange.create_order(
                    symbol=target_binance_sym,
                    type='takeProfitMarket',
                    side=sl_side,
                    amount=lot_size,
                    params={'stopPrice': tp_price, 'reduceOnly': True}
                )
            except Exception as etp:
                self.log_callback(f"⚠️ Lỗi đặt TakeProfitMarket: {etp}")

            ticket = f"pos_{target_binance_sym}_{pos_side}"
            self.active_trade_loggers[ticket] = {
                "status": "OPEN", "entry_price": float(current_price),
                "order_type": "MUA" if side == "buy" else "BÁN",
                "entry_time": time.time(), "contracts": lot_size, "side": pos_side
            }
            
            self.tg_notify(f"🟢 AI V3 Binance Open {'MUA' if side=='buy' else 'BÁN'} (Market)\nSymbol: {target_binance_sym} | L: {lot_size}\nSL: {sl_price:.2f} | TP: {tp_price:.2f}\n{preds_info}")
            return ticket
            
        except Exception as e:
            self.log_callback(f"[BinanceTradeManagerV3] ❌ Lỗi mở lệnh: {e}")
            return None

    def manage_positions(self, action: str, probs_dict: dict, mse_loss: float):
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
            positions = self.exchange.fetch_positions(symbols=[target_binance_sym])
            active_positions = [p for p in positions if float(p.get("contracts", 0)) > 0]
        except Exception as e:
            self.log_callback(f"Lỗi fetch positions Binance: {e}")
            active_positions = []

        has_open = len(active_positions) > 0
        just_closed = False

        for pos in active_positions:
            side = pos.get('side', '').upper()
            contracts = float(pos.get("contracts", 0))
            pos_dict = {"side": side, "contracts": contracts}
            
            if side == "LONG" and action == "SELL":
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
