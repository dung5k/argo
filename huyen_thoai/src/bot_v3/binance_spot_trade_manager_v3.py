import time
import os
import ccxt
from datetime import datetime
from dotenv import load_dotenv

class BinanceSpotTradeManagerV3:
    """Quản lý thực thi lệnh Giao dịch lên máy chủ Binance SPOT dựa trên tín hiệu AI V3.
    
    Khác biệt cốt lõi so với Futures:
    - KHÔNG có Short (Bán khống). Tín hiệu SELL = Bán coin đang giữ.
    - KHÔNG có Leverage (Đòn bẩy).
    - SL/TP sử dụng OCO Order thay vì STOP_MARKET/TAKE_PROFIT_MARKET.
    - Vị thế được theo dõi qua Balance (số dư coin) thay vì fetch_positions.
    """

    def __init__(self, target_symbol: str, config: dict, log_callback=None, tg_notify_callback=None):
        self.target_symbol = target_symbol  # e.g. "LTCUSDT"
        self.config = config
        self.log_callback = log_callback or print
        self.tg_notify = tg_notify_callback or (lambda x: None)

        self.active_trade_loggers: dict = {}
        self.gui_action: str = "-"
        self.gui_thr_text: str = "-"

        self.exchange = None
        self.last_close_time = 0
        # Lưu giá mua vào để tính P/L
        self._entry_price: float = 0.0

        load_dotenv()
        self.api_key = os.getenv("BINANCE_DEMO_API_KEY")
        self.secret_key = os.getenv("BINANCE_DEMO_SECRET_KEY")

    def init_client(self) -> bool:
        if not self.api_key or not self.secret_key:
            self.log_callback("[BinanceSpotV3] ❌ Thiếu BINANCE_DEMO_API_KEY hoặc SECRET_KEY trong .env")
            return False

        try:
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True
                }
            })

            # Kích hoạt chế độ Demo (Testnet) nếu cần
            if os.getenv("BINANCE_SPOT_DEMO", "True").lower() == "true":
                self.exchange.set_sandbox_mode(True)

            self.exchange.load_markets()
            try:
                self.exchange.load_time_difference()
            except Exception as e:
                self.log_callback(f"[BinanceSpotV3] ⚠️ Không thể đồng bộ time offset: {e}")
            self.log_callback("[BinanceSpotV3] ✅ Module CCXT đã kết nối Binance Spot.")

            return True
        except Exception as e:
            self.log_callback(f"[BinanceSpotV3] ❌ Cảnh báo kết nối CCXT: {e}")
            return False

    def _format_symbol(self, sym: str) -> str:
        """Chuyển 'LTCUSDT' -> 'LTC/USDT'."""
        sym = sym.replace("m", "").replace(".a", "")
        if "USDT" in sym:
            return sym.replace("USDT", "/USDT")
        return sym

    def _safe_api_call(self, func, *args, **kwargs):
        """Wrapper tự động retry khi gặp lỗi timestamp (-1021)."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "-1021" in str(e) or "Timestamp for this request" in str(e):
                self.log_callback(f"[BinanceSpotV3] ⚠️ Lỗi timestamp (-1021). Đang đồng bộ lại...")
                try:
                    self.exchange.load_time_difference()
                except Exception:
                    pass
                return func(*args, **kwargs)
            raise e

    def _get_coin_balance(self) -> float:
        """Lấy số dư coin (VD: LTC) từ ví Spot."""
        if not self.exchange:
            return 0.0
        try:
            target_sym = self._format_symbol(self.target_symbol)
            base_coin = target_sym.split("/")[0]  # "LTC"
            balance = self._safe_api_call(self.exchange.fetch_balance)
            free = float(balance.get(base_coin, {}).get('free', 0))
            return free
        except Exception as e:
            self.log_callback(f"[BinanceSpotV3] ⚠️ Lỗi fetch balance: {e}")
            return 0.0

    def _get_total_coin_balance(self) -> float:
        """Lấy TỔNG số dư coin (free + locked trong orders)."""
        if not self.exchange:
            return 0.0
        try:
            target_sym = self._format_symbol(self.target_symbol)
            base_coin = target_sym.split("/")[0]
            balance = self._safe_api_call(self.exchange.fetch_balance)
            total = float(balance.get(base_coin, {}).get('total', 0))
            return total
        except Exception as e:
            self.log_callback(f"[BinanceSpotV3] ⚠️ Lỗi fetch total balance: {e}")
            return 0.0

    def sync_existing_positions(self, symbol: str = None):
        """Đồng bộ vị thế hiện có dựa trên Balance coin."""
        if not self.exchange:
            return
        try:
            total_balance = self._get_total_coin_balance()
            target_binance_sym = self._format_symbol(symbol or self.target_symbol)
            ticket = f"spot_{target_binance_sym}_LONG"

            if total_balance > 0.001:  # Ngưỡng tối thiểu để coi là đang giữ coin
                if ticket not in self.active_trade_loggers:
                    # Thử lấy giá hiện tại làm entry price ước lượng
                    try:
                        ticker = self._safe_api_call(self.exchange.fetch_ticker, target_binance_sym)
                        est_price = ticker.get('last', 0)
                    except Exception:
                        est_price = 0

                    try:
                        trades = self._safe_api_call(self.exchange.fetch_my_trades, target_binance_sym, limit=5)
                        # Find last buy
                        buy_trades = [t for t in trades if t.get('side') == 'buy']
                        if buy_trades:
                            entry_time_sec = buy_trades[-1].get('timestamp', time.time() * 1000) / 1000.0
                        else:
                            entry_time_sec = time.time()
                    except Exception:
                        entry_time_sec = time.time()

                    self.active_trade_loggers[ticket] = {
                        "status": "OPEN",
                        "entry_price": est_price,
                        "order_type": "MUA",
                        "entry_time": entry_time_sec,
                        "contracts": total_balance,
                        "side": "LONG"
                    }
                    self.log_callback(f"[BinanceSpotV3] 📌 Phát hiện {total_balance:.4f} {target_binance_sym.split('/')[0]} trong ví.")
            else:
                # Không có coin -> xóa logger nếu có
                self.active_trade_loggers.pop(ticket, None)
        except Exception as e:
            self.log_callback(f"[BinanceSpotV3] ⚠️ Lỗi sync_existing_positions: {e}")

    def get_active_positions_report(self) -> str:
        """Trả về báo cáo vị thế Spot hiện tại và P/L ước tính."""
        if not self.exchange:
            return ""
        try:
            target_binance_sym = self._format_symbol(self.target_symbol)
            base_coin = target_binance_sym.split("/")[0]
            total_balance = self._get_total_coin_balance()

            if total_balance < 0.001:
                return ""

            ticker = self._safe_api_call(self.exchange.fetch_ticker, target_binance_sym)
            current_price = ticker.get('last', 0)

            # Tính P/L nếu có entry price
            ticket = f"spot_{target_binance_sym}_LONG"
            entry_price = self._entry_price
            if ticket in self.active_trade_loggers:
                entry_price = self.active_trade_loggers[ticket].get("entry_price", 0)

            if entry_price > 0:
                pnl = (current_price - entry_price) * total_balance
                pnl_pct = ((current_price / entry_price) - 1) * 100
                pnl_icon = "🟢" if pnl >= 0 else "🔴"
                ticket = f"spot_{target_binance_sym}_LONG"
                logger_pos = self.active_trade_loggers.get(ticket, {})
                entry_time = logger_pos.get("entry_time", time.time())
                elapsed_mins = int((time.time() - entry_time) / 60)
                return f"Vị thế Spot hiện tại:\n{pnl_icon} LONG {base_coin} ({elapsed_mins}p): {total_balance:.4f} @ {entry_price:.2f} → {current_price:.2f} ({pnl_pct:+.2f}%) = {pnl:+.2f}$"
            else:
                return f"Vị thế Spot hiện tại:\n📌 LONG {base_coin}: {total_balance:.4f} @ Giá: {current_price:.2f}"

        except Exception as e:
            self.log_callback(f"[BinanceSpotV3] ⚠️ get_active_positions_report lỗi: {e}")
            return ""

    def close_spot_position(self, close_reason: str = "AAMT V3 Signal") -> bool:
        """Đóng vị thế Spot = Bán hết coin đang giữ."""
        if not self.exchange:
            return False
        try:
            target_binance_sym = self._format_symbol(self.target_symbol)
            free_balance = self._get_coin_balance()

            if free_balance < 0.001:
                self.log_callback(f"[BinanceSpotV3] ⚠️ Không có coin để bán.")
                return False

            # 1. Hủy hết open orders (OCO SL/TP)
            try:
                self._safe_api_call(self.exchange.cancel_all_orders, target_binance_sym)
                self.log_callback(f"[BinanceSpotV3] 🗑️ Đã hủy tất cả open orders.")
            except Exception as cancel_err:
                self.log_callback(f"[BinanceSpotV3] ⚠️ Lỗi hủy orders: {cancel_err}")

            # Sau khi hủy orders, balance locked có thể được giải phóng
            time.sleep(0.5)
            free_balance = self._get_coin_balance()

            # 2. Bán hết coin bằng Market Order
            # Làm tròn amount theo quy tắc của exchange
            amount = self.exchange.amount_to_precision(target_binance_sym, free_balance)
            amount = float(amount)

            order = self._safe_api_call(
                self.exchange.create_order,
                symbol=target_binance_sym,
                type='market',
                side='sell',
                amount=amount
            )

            ticket = f"spot_{target_binance_sym}_LONG"
            self.active_trade_loggers.pop(ticket, None)
            self.last_close_time = time.time()
            self._entry_price = 0.0

            self.log_callback(f"[BinanceSpotV3] ✅ Đã BÁN {amount} {target_binance_sym.split('/')[0]} thành công.")
            self.tg_notify(f"🔴 AI V3 Spot SELL (Đóng vị thế) | {target_binance_sym}\nSố lượng: {amount}\nLý do: {close_reason}")
            return True
        except Exception as e:
            self.log_callback(f"[BinanceSpotV3] ❌ Lỗi đóng vị thế Spot: {e}")
            return False

    def open_new_spot_trade(self, lot_size: float, sl_pct: float, tp_pct: float, preds_info: str):
        """Mở lệnh MUA Spot mới + đặt OCO Order cho SL/TP."""
        if not self.exchange:
            return None
        target_binance_sym = self._format_symbol(self.target_symbol)

        try:
            ticker = self._safe_api_call(self.exchange.fetch_ticker, target_binance_sym)
            current_price = ticker['last']

            # Tính SL TP
            sl_price = current_price * (1 - sl_pct)
            tp_price = current_price * (1 + tp_pct)

            # 1. Mở Market Order MUA
            order = self._safe_api_call(
                self.exchange.create_order,
                symbol=target_binance_sym,
                type='market',
                side='buy',
                amount=lot_size
            )

            time.sleep(1)

            # Lấy giá thực tế sau khi khớp
            filled_price = current_price
            if order and order.get('average'):
                filled_price = float(order['average'])
            elif order and order.get('price'):
                filled_price = float(order['price'])

            self._entry_price = filled_price

            # Tính lại SL/TP dựa trên giá khớp thực
            sl_price = filled_price * (1 - sl_pct)
            tp_price = filled_price * (1 + tp_pct)

            # 2. Đặt OCO Order (SL + TP)
            exec_cfg = self.config.get("LIVE_BOT", {}).get("BINANCE_SPOT_EXECUTION", {})
            use_oco = exec_cfg.get("USE_OCO_SL_TP", True)

            if use_oco:
                try:
                    # OCO Order trên Binance Spot:
                    # - LIMIT order (Take Profit): bán khi giá LÊN đến tp_price
                    # - STOP_LOSS_LIMIT order (Stop Loss): bán khi giá XUỐNG đến sl_price
                    sl_price_str = self.exchange.price_to_precision(target_binance_sym, sl_price)
                    tp_price_str = self.exchange.price_to_precision(target_binance_sym, tp_price)
                    # Stop limit price hơi thấp hơn sl_price để đảm bảo khớp
                    sl_limit_price = sl_price * 0.998  # 0.2% dưới stop price
                    sl_limit_str = self.exchange.price_to_precision(target_binance_sym, sl_limit_price)
                    amount_str = self.exchange.amount_to_precision(target_binance_sym, lot_size)

                    # Sử dụng CCXT để tạo OCO
                    # Binance OCO = 1 limit (TP) + 1 stop-limit (SL), hủy lẫn nhau
                    oco_params = {
                        'stopPrice': float(sl_price_str),
                        'stopLimitPrice': float(sl_limit_str),
                        'stopLimitTimeInForce': 'GTC',
                    }
                    oco_order = self._safe_api_call(
                        self.exchange.create_order,
                        symbol=target_binance_sym,
                        type='limit',
                        side='sell',
                        amount=float(amount_str),
                        price=float(tp_price_str),
                        params={
                            'orderListType': 'OCO',
                            **oco_params
                        }
                    )
                    self.log_callback(f"[BinanceSpotV3] ✅ OCO đã đặt — SL: {sl_price_str} | TP: {tp_price_str}")
                except Exception as oco_err:
                    self.log_callback(f"[BinanceSpotV3] ⚠️ Lỗi đặt OCO: {oco_err}")
                    # Fallback: Đặt SL riêng lẻ
                    try:
                        sl_price_str = self.exchange.price_to_precision(target_binance_sym, sl_price)
                        sl_limit_str = self.exchange.price_to_precision(target_binance_sym, sl_price * 0.998)
                        amount_str = self.exchange.amount_to_precision(target_binance_sym, lot_size)
                        self._safe_api_call(
                            self.exchange.create_order,
                            symbol=target_binance_sym,
                            type='STOP_LOSS_LIMIT',
                            side='sell',
                            amount=float(amount_str),
                            price=float(sl_limit_str),
                            params={'stopPrice': float(sl_price_str), 'timeInForce': 'GTC'}
                        )
                        self.log_callback(f"[BinanceSpotV3] ✅ Fallback SL đã đặt tại {sl_price_str}")
                    except Exception as sl_err:
                        self.log_callback(f"[BinanceSpotV3] ❌ Fallback SL cũng thất bại: {sl_err}")

            ticket = f"spot_{target_binance_sym}_LONG"
            self.active_trade_loggers[ticket] = {
                "status": "OPEN",
                "entry_price": filled_price,
                "order_type": "MUA",
                "entry_time": time.time(),
                "contracts": lot_size,
                "side": "LONG"
            }

            self.log_callback(f"[BinanceSpotV3] ✅ ĐÃ BẮN LỆNH MUA Spot! Symbol: {target_binance_sym} | L: {lot_size} | Giá: {filled_price:.2f}")
            self.tg_notify(
                f"🟢 AI V3 Spot BUY (Market)\n"
                f"Symbol: {target_binance_sym} | Qty: {lot_size}\n"
                f"Giá khớp: {filled_price:.2f}\n"
                f"SL: {sl_price:.2f} | TP: {tp_price:.2f}\n"
                f"{preds_info}"
            )
            return ticket

        except Exception as e:
            self.log_callback(f"[BinanceSpotV3] ❌ Lỗi mở lệnh Spot: {e}")
            return None

    def execute_trade(self, action: str, probs_dict: dict, mse_loss: float, actual_target_sym: str = None):
        """Xử lý tín hiệu giao dịch cho Spot.
        
        Logic Spot:
        - BUY: Mua coin nếu chưa có vị thế.
        - SELL: Bán coin nếu đang giữ. KHÔNG MỞ SHORT.
        - HOLD/TÍN_HIỆU_RÁC: Giữ nguyên.
        """
        if not self.exchange:
            return
        target_binance_sym = self._format_symbol(self.target_symbol)

        exec_cfg = self.config.get("LIVE_BOT", {}).get("BINANCE_SPOT_EXECUTION", {})
        lot_size = exec_cfg.get("LOT_SIZE", 0.5)

        # Crypto config uses PCT directly
        fe_cfg = self.config.get("FEATURE_ENGINEERING", {})
        sl_pct = fe_cfg.get("SL_PCT", 0.003)
        tp_pct = fe_cfg.get("TP_PCT", 0.003)

        preds_info = f"MSE:{mse_loss:.3f} | B:{probs_dict.get('buy', 0):.2f} S:{probs_dict.get('sell', 0):.2f}"

        # Kiểm tra balance coin hiện tại
        total_balance = self._get_total_coin_balance()
        has_coin = total_balance > 0.001

        max_hold_bars = fe_cfg.get("MAX_HOLD_BARS", 20)
        max_hold_seconds = max_hold_bars * 60
        
        target_binance_sym = self._format_symbol(self.target_symbol)
        ticket = f"spot_{target_binance_sym}_LONG"
        logger_pos = self.active_trade_loggers.get(ticket)

        if has_coin and logger_pos and (time.time() - logger_pos.get("entry_time", time.time())) > max_hold_seconds:
            self.gui_action = f"CHỐT: QUÁ GIỜ (>{max_hold_bars} nến)"
            self.close_spot_position(f"Giữ lệnh quá {max_hold_bars} phút")
        elif action == "SELL":
            if has_coin:
                # Đang giữ coin → Bán hết (Đóng vị thế)
                self.gui_action = "🔴 CHỐT LỜI/CẮT LỖ: BÁN COIN"
                self.close_spot_position(f"AI Signal SELL | {preds_info}")
            else:
                # Không có coin → Bỏ qua (Spot không có Short)
                self.gui_action = "⏭️ Bỏ qua SELL (Spot không Short)"
                self.log_callback(f"[BinanceSpotV3] ⏭️ Tín hiệu SELL nhưng không có coin để bán. Bỏ qua (Spot không hỗ trợ Short).")

        elif action == "BUY":
            if has_coin:
                # Đã có coin → Giữ nguyên
                self.gui_action = "GIỮ LỆNH (Đã có coin)"
            else:
                # Chưa có coin → Mua mới
                now = time.time()
                if (now - self.last_close_time) < 60:
                    self.gui_action = "Chờ Cooldown 60s..."
                else:
                    self.gui_action = "🔥 ĐÃ BẮN LỆNH MUA (BUY) LÊN BINANCE SPOT!"
                    self.open_new_spot_trade(lot_size, sl_pct, tp_pct, preds_info)

        elif action == "TÍN_HIỆU_RÁC" or action == "HOLD":
            if has_coin:
                self.gui_action = "GIỮ LỆNH (LONG)"
            else:
                self.gui_action = f"Bỏ qua ({action})"
        else:
            self.gui_action = f"Bỏ qua ({action})"

    def update_gui_threshold(self):
        bot_cfg = self.config.get("LIVE_BOT", {})
        mse_thr = bot_cfg.get("MSE_THRESHOLD_PERCENTILE", 70)
        prob_thr = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.7)
        self.gui_thr_text = f"🔥 Binance Spot: Prob>{prob_thr} | Cảnh Báo: MSE>{mse_thr}"
