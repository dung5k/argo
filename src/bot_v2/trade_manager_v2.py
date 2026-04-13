import time
import traceback
from datetime import datetime, time as dtime


class V2TradeManager:
    """Quản lý thực thi lệnh Giao dịch lên máy chủ MT5 (MetaTrader 5).

    Trách nhiệm duy nhất: nhận tín hiệu dự báo → quyết định → gửi lệnh MT5 → cập nhật GUI.
    Mọi logic notification, build request, send lệnh được tách riêng để UT độc lập.
    """

    MAGIC_NUMBER = 101010

    def __init__(self, target_symbol: str, config: dict, log_callback=None, tg_notify_callback=None):
        self.target_symbol = target_symbol
        self.config = config
        self.log_callback = log_callback or print
        self.tg_notify = tg_notify_callback or (lambda x: None)

        # ticket → {status, entry_price, order_type, entry_time, notified_1min}
        self.active_trade_loggers: dict = {}
        self.gui_action: str = "-"
        self.gui_thr_text: str = "-"

        # Late-import MT5 để có thể chạy UT trên môi trường không có Windows
        self.mt5 = None

    # -------------------------------------------------------------------------
    # INIT
    # -------------------------------------------------------------------------

    def init_mt5(self) -> bool:
        """Khởi tạo module MetaTrader5. Trả về True nếu thành công."""
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.log_callback("[TradeManager] ✅ Module MT5 đã sẵn sàng.")
            return True
        except ImportError:
            self.log_callback("[TradeManager] ❌ Module MetaTrader5 không tồn tại (môi trường test?).")
            return False

    # -------------------------------------------------------------------------
    # DAILY PnL
    # -------------------------------------------------------------------------

    def _get_daily_pnl(self) -> float:
        """Tính tổng PnL thực hiện trong ngày hôm nay (từ 0h đến hiện tại)."""
        if not self.mt5:
            return 0.0
        try:
            now = datetime.now()
            dt_from = datetime.combine(now.date(), dtime(0, 0, 0))
            deals = self.mt5.history_deals_get(dt_from, now)
            total = sum(d.profit for d in deals) if deals else 0.0
            return total
        except Exception as e:
            self.log_callback(f"[TradeManager] ⚠️ Lỗi tính Daily PnL: {e}")
            return 0.0

    # -------------------------------------------------------------------------
    # ORDER REQUEST BUILDERS  (pure functions – no MT5 calls, fully UT-able)
    # -------------------------------------------------------------------------

    def _build_close_request(self, position) -> dict:
        """Xây dựng dict request đóng vị thế (không gọi MT5, chỉ tính toán)."""
        tick = self.mt5.symbol_info_tick(position.symbol)
        if tick is None:
            raise ValueError(f"[TradeManager] Không lấy được tick cho {position.symbol}")

        if position.type == self.mt5.ORDER_TYPE_BUY:
            order_type = self.mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = self.mt5.ORDER_TYPE_BUY
            price = tick.ask

        return {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": 20,
            "magic": self.MAGIC_NUMBER,
            "comment": "AI Close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

    def _build_open_request(self, symbol: str, order_type, lot_size: float,
                            sl_pips: float, tp_pips: float) -> dict:
        """Xây dựng dict request mở vị thế mới (không gọi MT5, chỉ tính toán)."""
        point_info = self.mt5.symbol_info(symbol)
        if point_info is None:
            raise ValueError(f"[TradeManager] Không lấy được symbol_info cho {symbol}")
        point = point_info.point

        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ValueError(f"[TradeManager] Không lấy được tick cho {symbol}")

        if order_type == self.mt5.ORDER_TYPE_BUY:
            price = tick.ask
            sl = price - sl_pips * 10 * point
            tp = price + tp_pips * 10 * point
        else:
            price = tick.bid
            sl = price + sl_pips * 10 * point
            tp = price - tp_pips * 10 * point

        return {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot_size),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": self.MAGIC_NUMBER,
            "comment": "AI Entry",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

    # -------------------------------------------------------------------------
    # ORDER SENDER
    # -------------------------------------------------------------------------

    def _send_order(self, request: dict) -> tuple:
        """Gửi request lên MT5. Trả về (success: bool, result)."""
        result = self.mt5.order_send(request)
        if result is None:
            self.log_callback(f"[TradeManager] ❌ order_send trả về None cho {request.get('symbol')}")
            return False, None
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            self.log_callback(
                f"[TradeManager] ❌ Lỗi order_send retcode={result.retcode} comment='{result.comment}' "
                f"symbol={request.get('symbol')} type={request.get('type')} vol={request.get('volume')}"
            )
            return False, result
        return True, result

    # -------------------------------------------------------------------------
    # CLOSE POSITION
    # -------------------------------------------------------------------------

    def close_mt5_position(self, position) -> bool:
        """Đóng một vị thế MT5 đang sống. Trả về True nếu đóng thành công."""
        if not self.mt5:
            self.log_callback("[TradeManager] ❌ close_mt5_position: MT5 chưa được khởi tạo.")
            return False

        symbol = position.symbol
        ticket = position.ticket
        o_type_str = "MUA" if position.type == self.mt5.ORDER_TYPE_BUY else "BÁN"
        self.log_callback(f"[TradeManager] 🔄 Đang đóng lệnh {o_type_str} #{ticket} ({symbol})...")

        try:
            request = self._build_close_request(position)
        except ValueError as e:
            self.log_callback(f"[TradeManager] ❌ Build close request thất bại: {e}")
            return False

        success, result = self._send_order(request)
        if not success:
            return False

        self.log_callback(f"[TradeManager] ✅ Đóng lệnh #{ticket} thành công. retcode={result.retcode}")
        self.active_trade_loggers.pop(ticket, None)

        pnl = getattr(position, 'profit', 0.0)
        daily_pnl = self._get_daily_pnl()
        icon = "💰" if pnl > 0 else "🩸"
        msg = (
            f"🔴 [ĐÓNG LỆNH AI] Chốt lệnh {o_type_str}\n"
            f"* Mã: {symbol}\n"
            f"* Ticket: {ticket}\n"
            f"* Lợi nhuận: {icon} {pnl:.2f} USD\n"
            f"📊 Lãi/Lỗ ngày: {daily_pnl:.2f} USD"
        )
        self.log_callback(f"[TradeManager] 📨 Gửi TG: {msg[:80]}...")
        try:
            self.tg_notify(msg)
        except Exception as e:
            self.log_callback(f"[TradeManager] ⚠️ Lỗi gửi Telegram close: {e}")

        return True

    # -------------------------------------------------------------------------
    # OPEN POSITION
    # -------------------------------------------------------------------------

    def open_new_mt5_trade(self, symbol: str, order_type, lot_size: float,
                           sl_pips: float, tp_pips: float, prediction: float):
        """Mở một vị thế mới. Trả về ticket nếu thành công, None nếu thất bại."""
        if not self.mt5:
            self.log_callback("[TradeManager] ❌ open_new_mt5_trade: MT5 chưa được khởi tạo.")
            return None

        o_type_str = "MUA (BUY)" if order_type == self.mt5.ORDER_TYPE_BUY else "BÁN (SELL)"
        self.log_callback(
            f"[TradeManager] 🎯 Chuẩn bị bắn lệnh {o_type_str} "
            f"| symbol={symbol} | lot={lot_size} | sl={sl_pips}p | tp={tp_pips}p | pred={prediction:.4f}"
        )

        try:
            request = self._build_open_request(symbol, order_type, lot_size, sl_pips, tp_pips)
        except ValueError as e:
            self.log_callback(f"[TradeManager] ❌ Build open request thất bại: {e}")
            return None

        self.log_callback(
            f"[TradeManager] 📤 Gửi lệnh: price={request['price']} sl={request['sl']:.2f} tp={request['tp']:.2f}"
        )
        success, result = self._send_order(request)
        if not success:
            return None

        ticket = result.order
        self.log_callback(f"[TradeManager] ✅ Lệnh thành công! Ticket=#{ticket} price={request['price']}")

        self.active_trade_loggers[ticket] = {
            "status": "OPEN",
            "entry_price": float(request['price']),
            "order_type": "MUA" if order_type == self.mt5.ORDER_TYPE_BUY else "BÁN",
            "entry_time": time.time(),
            "notified_1min": False,
        }

        daily_pnl = self._get_daily_pnl()
        msg = (
            f"🟢 [VÀO LỆNH] AI Đã thực hiện lệnh {o_type_str}\n"
            f"* Mã: {symbol}\n"
            f"* Ticket: {ticket}\n"
            f"* Giá: {request['price']}\n"
            f"* Khối lượng: {request['volume']} lot\n"
            f"* Tỉ lệ Vượt Cản: {prediction * 100:.2f}%\n"
            f"📊 Lãi/Lỗ ngày: {daily_pnl:.2f} USD"
        )
        self.log_callback(f"[TradeManager] 📨 Gửi TG: {msg[:80]}...")
        try:
            self.tg_notify(msg)
        except Exception as e:
            self.log_callback(f"[TradeManager] ⚠️ Lỗi gửi Telegram open: {e}")

        return ticket

    # -------------------------------------------------------------------------
    # POSITION TRACKER (1-min notify & auto-close detect)
    # -------------------------------------------------------------------------

    def _track_open_positions(self, symbol: str, active_tickets: dict):
        """Kiểm tra PnL sau 1 phút và phát hiện lệnh bị sàn tự đóng (SL/TP)."""
        for tkt in list(self.active_trade_loggers.keys()):
            log_data = self.active_trade_loggers[tkt]

            if tkt in active_tickets:
                # Lệnh vẫn đang sống – kiểm tra 1-min notify
                pos = active_tickets[tkt]
                elapsed = time.time() - log_data.get('entry_time', time.time())
                if not log_data.get('notified_1min', False) and elapsed >= 60:
                    pnl = getattr(pos, 'profit', 0.0)
                    icon = "💰" if pnl > 0 else "🩸"
                    daily_pnl = self._get_daily_pnl()
                    msg = (
                        f"⏳ [CẬP NHẬT 1 PHÚT]\n"
                        f"* Mã: {symbol}\n"
                        f"* Ticket: {tkt}\n"
                        f"* Trạng thái lãi lỗ: {icon} {pnl:.2f} USD\n"
                        f"📊 Lãi/Lỗ ngày: {daily_pnl:.2f} USD"
                    )
                    self.log_callback(f"[TradeManager] ⏳ 1-min notify #{tkt} PnL={pnl:.2f}")
                    try:
                        self.tg_notify(msg)
                    except Exception as e:
                        self.log_callback(f"[TradeManager] ⚠️ Lỗi gửi Telegram 1-min: {e}")
                    log_data['notified_1min'] = True
            else:
                # Lệnh biến mất khỏi danh sách đang chạy → bị sàn đóng (SL/TP)
                self.log_callback(f"[TradeManager] 🔍 Ticket #{tkt} không còn trong active_tickets → Kiểm tra lịch sử...")
                deal_pnl = 0.0
                try:
                    deals = self.mt5.history_deals_get(position=tkt)
                    if deals:
                        deal_pnl = sum(d.profit for d in deals if d.entry == self.mt5.DEAL_ENTRY_OUT)
                        self.log_callback(f"[TradeManager] 📋 Tìm thấy {len(deals)} deals cho #{tkt}, PnL={deal_pnl:.2f}")
                    else:
                        self.log_callback(f"[TradeManager] ⚠️ Không tìm thấy deals lịch sử cho #{tkt}")
                except Exception as e:
                    self.log_callback(f"[TradeManager] ❌ Lỗi truy vấn deals #{tkt}: {e}")

                icon = "💰" if deal_pnl > 0 else "🩸"
                o_type = log_data.get('order_type', 'UNKNOWN')
                daily_pnl = self._get_daily_pnl()
                msg = (
                    f"🔴 [ĐÃ ĐÓNG LỆNH] Lệnh {o_type} đóng (SL/TP sàn)\n"
                    f"* Mã: {symbol}\n"
                    f"* Ticket: {tkt}\n"
                    f"* Lãi/Lỗ lệnh: {icon} {deal_pnl:.2f} USD\n"
                    f"📊 Lãi/Lỗ ngày: {daily_pnl:.2f} USD"
                )
                self.log_callback(f"[TradeManager] 🔴 Auto-close detected #{tkt} deal_pnl={deal_pnl:.2f}")
                try:
                    self.tg_notify(msg)
                except Exception as e:
                    self.log_callback(f"[TradeManager] ⚠️ Lỗi gửi Telegram auto-close: {e}")

                self.active_trade_loggers.pop(tkt, None)

    # -------------------------------------------------------------------------
    # THRESHOLD DECISION  (pure business logic, no MT5 calls – fully UT-able)
    # -------------------------------------------------------------------------

    def _decide_action(self, prediction: float, live_cfg: dict) -> str:
        """Quyết định hành động dựa trên prediction và threshold config.
        Trả về: 'BUY_ENTRY' | 'SELL_ENTRY' | 'CLOSE_BUY' | 'CLOSE_SELL' | 'HOLD'
        """
        buy_entry  = live_cfg.get("BUY_ENTRY_THR", 0.60)
        sell_entry = live_cfg.get("SELL_ENTRY_THR", 0.40)
        close_buy  = live_cfg.get("CLOSE_BUY_THR", 0.45)
        close_sell = live_cfg.get("CLOSE_SELL_THR", 0.55)

        self.log_callback(
            f"[TradeManager] 🔢 Thresholds – BUY>{buy_entry} SELL<{sell_entry} "
            f"CloseBUY<{close_buy} CloseSELL>{close_sell} | pred={prediction:.4f}"
        )

        if prediction >= buy_entry:
            return "BUY_ENTRY"
        if prediction <= sell_entry:
            return "SELL_ENTRY"
        if prediction <= close_buy:
            return "CLOSE_BUY"
        if prediction >= close_sell:
            return "CLOSE_SELL"
        return "HOLD"

    # -------------------------------------------------------------------------
    # MAIN ORCHESTRATOR
    # -------------------------------------------------------------------------

    def manage_mt5_positions(self, prediction: float, actual_target_sym: str = None,
                             lot_size: float = 0.01, sl_pips: float = 50, tp_pips: float = 100):
        """Orchestrator chính: nhận prediction → track → quyết định → thực thi lệnh."""
        if not self.mt5:
            self.log_callback("[TradeManager] ❌ manage_mt5_positions: MT5 chưa được khởi tạo.")
            return

        symbol = actual_target_sym or self.target_symbol
        self.log_callback(f"[TradeManager] ▶ Bắt đầu chu kỳ quản lý vị thế | symbol={symbol} | pred={prediction:.4f}")

        if self.mt5.symbol_info(symbol) is None:
            self.log_callback(f"[TradeManager] ⚠️ Không tìm thấy mã {symbol} trên MT5! Bỏ qua chu kỳ.")
            return

        live_cfg = self.config.get("LIVE_TRADING", {})
        cfg_lot  = live_cfg.get("lot_size", lot_size)
        cfg_sl   = live_cfg.get("sl_pips", sl_pips)
        cfg_tp   = live_cfg.get("tp_pips", tp_pips)
        self.update_gui_threshold()

        # 1. Lấy danh sách positions hiện tại
        positions = self.mt5.positions_get(symbol=symbol) or []
        active_tickets = {pos.ticket: pos for pos in positions}
        self.log_callback(f"[TradeManager] 📊 Đang có {len(positions)} vị thế mở cho {symbol}.")

        # 2. Theo dõi PnL & phát hiện SL/TP tự đóng
        self._track_open_positions(symbol, active_tickets)

        # 3. Cập nhật lại positions sau khi _track có thể đã xóa
        positions = self.mt5.positions_get(symbol=symbol) or []
        has_open = bool(positions)
        just_closed = False

        # 4. Kiểm tra đóng lệnh theo tín hiệu AI
        for pos in positions:
            action = self._decide_action(prediction, live_cfg)
            if pos.type == self.mt5.ORDER_TYPE_BUY and action == "CLOSE_BUY":
                self.gui_action = f"ĐÃ CHỐT BIÊN BUY (#{pos.ticket})"
                self.log_callback(f"[TradeManager] 📉 Đóng BUY #{pos.ticket} vì pred={prediction:.4f} <= close_buy threshold")
                if self.close_mt5_position(pos):
                    has_open = False
                    just_closed = True
            elif pos.type == self.mt5.ORDER_TYPE_SELL and action == "CLOSE_SELL":
                self.gui_action = f"ĐÃ CHỐT BIÊN SELL (#{pos.ticket})"
                self.log_callback(f"[TradeManager] 📈 Đóng SELL #{pos.ticket} vì pred={prediction:.4f} >= close_sell threshold")
                if self.close_mt5_position(pos):
                    has_open = False
                    just_closed = True
            elif pos.type == self.mt5.ORDER_TYPE_BUY:
                self.gui_action = f"ĐANG KHÓA LÃI BUY (#{pos.ticket})"
            else:
                self.gui_action = f"ĐANG KHÓA LÃI SELL (#{pos.ticket})"

        # 5. Mở lệnh mới nếu không có vị thế
        if not has_open and not just_closed:
            action = self._decide_action(prediction, live_cfg)
            if action == "BUY_ENTRY":
                self.gui_action = "🔥 ĐÃ BẮN LỆNH MUA (BUY)!"
                self.log_callback(f"[TradeManager] 🔥 Mở BUY | pred={prediction:.4f} >= buy_entry threshold")
                self.open_new_mt5_trade(symbol, self.mt5.ORDER_TYPE_BUY, cfg_lot, cfg_sl, cfg_tp, prediction)
            elif action == "SELL_ENTRY":
                self.gui_action = "🔥 ĐÃ BẮN LỆNH BÁN (SELL)!"
                self.log_callback(f"[TradeManager] 🔥 Mở SELL | pred={prediction:.4f} <= sell_entry threshold")
                self.open_new_mt5_trade(symbol, self.mt5.ORDER_TYPE_SELL, cfg_lot, cfg_sl, cfg_tp, prediction)
            else:
                self.gui_action = "Thị trường Lưỡng Lự (Quan Sát)"
                self.log_callback(f"[TradeManager] 👁 Không có tín hiệu rõ ràng. Quan sát.")

        self.log_callback(f"[TradeManager] ✔ Kết thúc chu kỳ | action='{self.gui_action}'")

    # -------------------------------------------------------------------------
    # GUI HELPER
    # -------------------------------------------------------------------------

    def update_gui_threshold(self):
        """Cập nhật text hiển thị ngưỡng lên GUI."""
        live_cfg = self.config.get("LIVE_TRADING", {})
        buy_thr  = live_cfg.get("BUY_ENTRY_THR", 0.60)
        sell_thr = live_cfg.get("SELL_ENTRY_THR", 0.40)
        self.gui_thr_text = f"🔥 V2 Ngưỡng: BUY>{int(buy_thr * 100)}% | SELL<{int(sell_thr * 100)}%"
