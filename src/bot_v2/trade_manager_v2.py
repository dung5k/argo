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

        # ticket → {status, entry_price, order_type, entry_time, last_pnl_notify_time}
        self.active_trade_loggers: dict = {}
        self.gui_action: str = "-"
        self.gui_thr_text: str = "-"

        # Late-import MT5 để có thể chạy UT trên môi trường không có Windows
        self.mt5 = None

        # Track to prevent spam: kỳ gửi notify khởi động lần đầu
        self._positions_synced = False

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

    def sync_existing_positions(self, symbol: str = None):
        """Quét các lệnh đang tồn tại trên sàn và đăng ký vào active_trade_loggers nếu chưa có.
        Gọi 1 lần sau khi bot khởi động để không bỏ sót các lệnh đã có sẵn.
        """
        if not self.mt5:
            return
        sym = symbol or self.target_symbol
        try:
            positions = self.mt5.positions_get(symbol=sym) or []
            new_count = 0
            for pos in positions:
                if pos.ticket not in self.active_trade_loggers:
                    o_type = "MUA" if pos.type == self.mt5.ORDER_TYPE_BUY else "BÁN"
                    open_time_ts = getattr(pos, 'time', time.time())
                    self.active_trade_loggers[pos.ticket] = {
                        "status": "OPEN",
                        "entry_price": float(getattr(pos, 'price_open', 0.0)),
                        "order_type": o_type,
                        "entry_time": float(open_time_ts),
                        "last_pnl_notify_time": 0.0,  # 0 → sẽ gửi ngay trong chu kỳ tiếp theo
                    }
                    new_count += 1
                    self.log_callback(
                        f"[TradeManager] 🔄 Đăng ký lệnh sẵn có #{pos.ticket} "
                        f"{o_type} @ {pos.price_open} vol={pos.volume}"
                    )
            if new_count:
                self.log_callback(f"[TradeManager] 📢 Sync xong: đăng ký {new_count} lệnh sẵn có để track PnL.")
            else:
                self.log_callback(f"[TradeManager] ℹ️ Không có lệnh mới cần sync (total tracked={len(self.active_trade_loggers)}).")
        except Exception as e:
            self.log_callback(f"[TradeManager] ⚠️ sync_existing_positions lỗi: {e}")

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

    def close_mt5_position(self, position, close_reason: str = "AI Signal") -> bool:
        """Đóng một vị thế MT5 đang sống. Trả về True nếu đóng thành công."""
        if not self.mt5:
            self.log_callback("[TradeManager] ❌ close_mt5_position: MT5 chưa được khởi tạo.")
            return False

        symbol = position.symbol
        ticket = position.ticket
        o_type_str = "MUA" if position.type == self.mt5.ORDER_TYPE_BUY else "BÁN"
        self.log_callback(f"[TradeManager] 🔄 Đang đóng lệnh {o_type_str} #{ticket} ({symbol}) | Lý do: {close_reason}")

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
        self.last_close_time = time.time()

        pnl = getattr(position, 'profit', 0.0)
        daily_pnl = self._get_daily_pnl()
        icon = "💰" if pnl > 0 else "🩸"
        msg = (
            f"🔴 [ĐÓNG LỆNH] Chốt lệnh {o_type_str}"
            f"\n* Mã: {symbol}"
            f"\n* Ticket: {ticket}"
            f"\n* Lý do: ⚠️ {close_reason}"
            f"\n* Lợi nhuận: {icon} {pnl:.2f} USD"
            f"\n📊 Lãi/Lỗ ngày: {daily_pnl:.2f} USD"
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
            "last_pnl_notify_time": time.time(),  # Khởi đầu = now, notify đầu tiên sau 60s
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
    # POSITION TRACKER (periodic PnL notify & auto-close detect)
    # -------------------------------------------------------------------------

    def _track_open_positions(self, symbol: str, active_tickets: dict, prediction: float = None):
        """Kiểm tra PnL theo chu kỳ 1 phút (lặp lại mãi) và phát hiện lệnh bị sàn tự đóng (SL/TP)."""
        now = time.time()
        for tkt in list(self.active_trade_loggers.keys()):
            log_data = self.active_trade_loggers[tkt]

            if tkt in active_tickets:
                # Lệnh vẫn đang sống – kiểm tra có đến kỳ gửi notify chưa
                pos = active_tickets[tkt]
                last_notify = log_data.get('last_pnl_notify_time', 0.0)
                elapsed_since_notify = now - last_notify

                if elapsed_since_notify >= 60:
                    pnl = getattr(pos, 'profit', 0.0)
                    icon = "💰" if pnl > 0 else "🩸"
                    daily_pnl = self._get_daily_pnl()
                    open_time_str = datetime.fromtimestamp(
                        log_data.get('entry_time', now)
                    ).strftime('%H:%M:%S')

                    # Xây dựng cấu trúc AI signal line
                    if prediction is not None:
                        buy_thr  = self.config.get("LIVE_TRADING", {}).get("BUY_ENTRY_THR", 0.60)
                        sell_thr = self.config.get("LIVE_TRADING", {}).get("SELL_ENTRY_THR", 0.40)
                        if prediction >= buy_thr:
                            ai_signal = f"🟢 BÒ ({prediction*100:.1f}%)"
                        elif prediction <= sell_thr:
                            ai_signal = f"🔴 GẤU ({prediction*100:.1f}%)"
                        else:
                            ai_signal = f"⚪ LƯỢNG LỰ ({prediction*100:.1f}%)"
                    else:
                        ai_signal = "N/A"

                    msg = (
                        f"⏳ [CẬP NHẬT PnL]"
                        f"\n* Mã: {symbol}"
                        f"\n* Ticket: {tkt} ({log_data.get('order_type','?')})"
                        f"\n* Mở lúc: {open_time_str}"
                        f"\n* Lãi/lỗ: {icon} {pnl:.2f} USD"
                        f"\n🧠 AI hiện tại: {ai_signal}"
                        f"\n📊 Lãi/Lỗ ngày: {daily_pnl:.2f} USD"
                    )
                    self.log_callback(
                        f"[TradeManager] ⏳ Notify PnL #{tkt} | pnl={pnl:.2f} | ai={ai_signal} | elapsed={elapsed_since_notify:.0f}s"
                    )
                    try:
                        self.tg_notify(msg)
                    except Exception as e:
                        self.log_callback(f"[TradeManager] ⚠️ Lỗi gửi Telegram 1-min: {e}")
                    log_data['last_pnl_notify_time'] = now  # reset đồng hồ cho lần sau
                else:
                    self.log_callback(
                        f"[TradeManager] ⏳ #{tkt} PnL notify trong {60 - elapsed_since_notify:.0f}s nữa..."
                    )
            else:
                # Lệnh biến mất khỏi danh sách đang chạy → bị sàn đóng (SL/TP) hoặc do MT5 API bị trễ
                self.log_callback(f"[TradeManager] 🔍 Ticket #{tkt} không còn trong active_tickets → Kiểm tra lịch sử...")
                deal_pnl = 0.0
                close_reason_auto = "Sàn đóng (SL/TP)"
                deals_found = False
                try:
                    deals = self.mt5.history_deals_get(position=tkt)
                    if deals:
                        deals_found = True
                        exit_deals = [d for d in deals if d.entry == self.mt5.DEAL_ENTRY_OUT]
                        deal_pnl = sum(d.profit for d in exit_deals)
                        self.log_callback(f"[TradeManager] 📋 Tìm thấy {len(deals)} deals cho #{tkt}, PnL={deal_pnl:.2f}")

                        if exit_deals:
                            mt5_reason = exit_deals[-1].reason
                            if mt5_reason == self.mt5.DEAL_REASON_SL:
                                close_reason_auto = "🛑 Dừng lỗ SL (Stop Loss)"
                            elif mt5_reason == self.mt5.DEAL_REASON_TP:
                                close_reason_auto = "🎯 Chốt lãi TP (Take Profit)"
                            elif mt5_reason == self.mt5.DEAL_REASON_EXPERT:
                                close_reason_auto = "🧠 Expert Advisor đóng"
                            elif mt5_reason == self.mt5.DEAL_REASON_CLIENT:
                                close_reason_auto = "👤 Người dùng đóng thủ công"
                            elif mt5_reason == self.mt5.DEAL_REASON_MARGIN:
                                close_reason_auto = "⚠️ Margin Call (Ký quỹ không đủ)"
                            else:
                                close_reason_auto = f"Sàn đóng (reason_code={mt5_reason})"
                            self.log_callback(f"[TradeManager] 🔍 Lý do đóng #{tkt}: {close_reason_auto}")
                    else:
                        self.log_callback(f"[TradeManager] ⚠️ Không tìm thấy deals lịch sử cho #{tkt}")
                except Exception as e:
                    self.log_callback(f"[TradeManager] ❌ Lỗi truy vấn deals #{tkt}: {e}")

                # MT5 Sync Lag check: Nếu chưa có deal lịch sử và lệnh vừa mới được tạo < 20 giây -> Có thể do MT5 API trả chậm
                if not deals_found:
                    elapsed_since_open = now - log_data.get('entry_time', now)
                    if elapsed_since_open < 30:
                        self.log_callback(f"[TradeManager] ⏳ Lệnh #{tkt} vừa mở {elapsed_since_open:.1f}s trước, nhưng MT5 chưa cập nhật. Chờ đồng bộ (Grace Period)...")
                        continue

                icon = "💰" if deal_pnl > 0 else "🩸"
                o_type = log_data.get('order_type', 'UNKNOWN')
                entry_price = log_data.get('entry_price', 0.0)
                open_time_str = datetime.fromtimestamp(log_data.get('entry_time', now)).strftime('%H:%M:%S')
                daily_pnl = self._get_daily_pnl()
                msg = (
                    f"🔴 [ĐÃ ĐÓNG LỆNH]"
                    f"\n* Mã: {symbol}"
                    f"\n* Ticket: {tkt} ({o_type})"
                    f"\n* Mở lúc: {open_time_str} @ {entry_price}"
                    f"\n* Lý do: {close_reason_auto}"
                    f"\n* Lãi/Lỗ lệnh: {icon} {deal_pnl:.2f} USD"
                    f"\n📊 Lãi/Lỗ ngày: {daily_pnl:.2f} USD"
                )
                self.log_callback(f"[TradeManager] 🔴 Auto-close #{tkt} reason='{close_reason_auto}' pnl={deal_pnl:.2f}")
                try:
                    self.tg_notify(msg)
                except Exception as e:
                    self.log_callback(f"[TradeManager] ⚠️ Lỗi gửi Telegram auto-close: {e}")

                self.active_trade_loggers.pop(tkt, None)
    # -------------------------------------------------------------------------
    # DYNAMIC TRAILING STOP
    # -------------------------------------------------------------------------

    def _dynamic_trailing_stop(self, pos, live_cfg: dict):
        """Tính toán và gửi lệnh kéo Cắt Lỗ (Trailing SL) dồn ép theo thời gian."""
        sl_pips = live_cfg.get("sl_pips", 50)
        # Ngưỡng trailing tối thiểu (ST min), mặc định 15 pips nếu không có config
        min_sl_pips = live_cfg.get("min_sl_pips", 15)
        
        point_info = self.mt5.symbol_info(pos.symbol)
        if not point_info:
            return
            
        point = point_info.point
        pip_value = 10 * point
        
        ST_nguong_raw = sl_pips * pip_value
        ST_min_raw = min_sl_pips * pip_value
        
        elapsed_time = time.time() - pos.time
        
        # Công thức: ST_dong = ST_nguong - (ST_nguong / 600) * elapsed
        # Sau 10 phút (600s), ST_dong = 0
        ST_dong = ST_nguong_raw - (ST_nguong_raw / 600.0) * elapsed_time
        
        if ST_dong < ST_min_raw:
            ST_dong = ST_min_raw
            
        current_price = pos.price_current
        entry_price = pos.price_open
        current_sl = pos.sl
        
        # Step độ nhạy tối thiểu cho MT5 (Tránh dời SL nhỏ giọt spam quá nhiều)
        step_min = 3 * pip_value 
        updated = False
        new_sl = current_sl
        
        if pos.type == self.mt5.ORDER_TYPE_BUY:
            if (current_price - entry_price) > ST_dong:
                calc_sl = current_price - ST_dong
                # SL chỉ được phép tăng lên (dời lên để bảo vệ lãi)
                if current_sl == 0.0 or (calc_sl - current_sl) > step_min:
                    new_sl = calc_sl
                    updated = True
        else: # ORDER_TYPE_SELL
            if (entry_price - current_price) > ST_dong:
                calc_sl = current_price + ST_dong
                # SL chỉ được phép giảm xuống (dời xuống bảo vệ lãi)
                if current_sl == 0.0 or (current_sl - calc_sl) > step_min:
                    new_sl = calc_sl
                    updated = True
        
        # Log liên tục trạng thái phai nhạt của ST theo chu kỳ 10 giây để quan sát
        if hasattr(self, '_last_trace_st') and (time.time() - self._last_trace_st < 10):
            pass
        else:
            self._last_trace_st = time.time()
            profit_pips = ((current_price - entry_price) if pos.type == self.mt5.ORDER_TYPE_BUY else (entry_price - current_price)) / pip_value
            self.log_callback(f"[TradeManager] ⏱️ Trailing Động (#{pos.ticket}): Lãi {profit_pips:.1f} pips | Ngưỡng ST chờ = {ST_dong/pip_value:.1f} pips")
                    
        if updated:
            request = {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "symbol": pos.symbol,
                "sl": float(new_sl),
                "tp": float(pos.tp),
                "magic": self.MAGIC_NUMBER
            }
            success, result = self._send_order(request)
            if success:
                self.log_callback(f"[TradeManager] 🛡️ Dời Cắt Lỗ Động lệnh #{pos.ticket} thành công! Lãi bị khóa SL mới: {new_sl:.4f} (ST_dong={ST_dong/pip_value:.1f} pips)")
            else:
                self.log_callback(f"[TradeManager] ⚠️ Dời Cắt Lỗ Động thất bại cho #{pos.ticket}. Retcode={result.retcode}")

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
        self._track_open_positions(symbol, active_tickets, prediction=prediction)

        # 3. Cập nhật lại positions sau khi _track có thể đã xóa
        positions = self.mt5.positions_get(symbol=symbol) or []
        has_open = bool(positions) or (len(self.active_trade_loggers) > 0)
        just_closed = False

        # 4. Kiểm tra đóng lệnh theo tín hiệu AI
        for pos in positions:
            # Trailing Stop Động
            self._dynamic_trailing_stop(pos, live_cfg)

            action = self._decide_action(prediction, live_cfg)
            if pos.type == self.mt5.ORDER_TYPE_BUY and action == "CLOSE_BUY":
                close_buy_thr = live_cfg.get('CLOSE_BUY_THR', 0.45)
                reason = f"AI đảo chiều: pred={prediction*100:.1f}% < ngưỡng đóng BUY ({close_buy_thr*100:.0f}%)"
                self.gui_action = f"ĐÃ CHỐT BIÊN BUY (#{pos.ticket})"
                self.log_callback(f"[TradeManager] 📉 Đóng BUY #{pos.ticket} | {reason}")
                if self.close_mt5_position(pos, close_reason=reason):
                    has_open = False
                    just_closed = True
            elif pos.type == self.mt5.ORDER_TYPE_SELL and action == "CLOSE_SELL":
                close_sell_thr = live_cfg.get('CLOSE_SELL_THR', 0.55)
                reason = f"AI đảo chiều: pred={prediction*100:.1f}% > ngưỡng đóng SELL ({close_sell_thr*100:.0f}%)"
                self.gui_action = f"ĐÃ CHỐT BIÊN SELL (#{pos.ticket})"
                self.log_callback(f"[TradeManager] 📈 Đóng SELL #{pos.ticket} | {reason}")
                if self.close_mt5_position(pos, close_reason=reason):
                    has_open = False
                    just_closed = True
            elif pos.type == self.mt5.ORDER_TYPE_BUY:
                self.gui_action = f"ĐANG KHÓA LÃI BUY (#{pos.ticket})"
            else:
                self.gui_action = f"ĐANG KHÓA LÃI SELL (#{pos.ticket})"

        # 5. Mở lệnh mới nếu không có vị thế
        if not has_open and not just_closed:
            action = self._decide_action(prediction, live_cfg)
            
            # Anti-Spam / Whip-saw mechanism
            now = time.time()
            last_close = getattr(self, "last_close_time", 0)
            if (now - last_close) < 60:
                self.gui_action = f"Chờ Cooldown 60s để vào lệnh..."
                self.log_callback(f"[TradeManager] ⏳ Cooldown active (còn {60 - (now - last_close):.0f}s). Bỏ qua {action}.")
            else:
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
