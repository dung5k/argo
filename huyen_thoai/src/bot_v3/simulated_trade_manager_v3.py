import time
from datetime import datetime, timezone


class SimulatedTradeManagerV3:
    """
    Paper Trading Manager — giả lập lệnh có đầy đủ logic như giao dịch thật:
    - Mở/Đóng vị thế ảo với giá thật từ market
    - SL/TP tự động kiểm tra mỗi nến M1
    - Đảo chiều khi tín hiệu ngược
    - Cooldown 60s sau khi đóng lệnh
    - Tính P&L tích lũy, Win Rate, P&L trong ngày
    """

    def __init__(self, target_symbol: str, config: dict,
                 log_callback=None, tg_notify_callback=None,
                 get_price_fn=None):
        self.target_symbol = target_symbol
        self.config = config
        self.log_callback = log_callback or print
        self.tg_notify = tg_notify_callback or (lambda x: None)
        self.get_price_fn = get_price_fn  # () -> float

        # Dùng để tg_notify & custom_print logic check "đang giữ lệnh"
        self.active_trade_loggers: dict = {}  # ticket -> position dict

        self.gui_action: str = "🎭 SIM — Chờ Tín Hiệu"
        self.gui_thr_text: str = "-"
        self.exchange = None

        self.last_close_time = 0.0
        self._ticket_counter = 1000

        # Thống kê tổng hợp
        self.total_trades = 0
        self.win_trades = 0
        self.total_pnl_usdt = 0.0

        # Thống kê trong ngày (reset mỗi ngày UTC)
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self._daily_date = datetime.now(timezone.utc).date()

    # ------------------------------------------------------------------
    # Khởi tạo — không cần làm gì vì là giả lập
    # ------------------------------------------------------------------
    def init_mt5(self): pass
    def init_client(self): pass
    def sync_existing_positions(self): pass
    def update_gui_threshold(self):
        bot_cfg = self.config.get("LIVE_BOT", {})
        prob_thr = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.7)
        self.gui_thr_text = f"🎭 SIM | Prob>{prob_thr:.3f}"

    # ------------------------------------------------------------------
    # Tiện ích nội bộ
    # ------------------------------------------------------------------
    def _next_ticket(self) -> int:
        self._ticket_counter += 1
        return self._ticket_counter

    def _get_price(self) -> float:
        if self.get_price_fn:
            try:
                return float(self.get_price_fn())
            except Exception:
                pass
        return 0.0

    def _calc_pnl(self, pos: dict, current_price: float) -> float:
        entry = pos["entry_price"]
        qty = pos["qty"]
        if pos["side"] == "BUY":
            return (current_price - entry) * qty
        else:
            return (entry - current_price) * qty

    def _check_sl_tp(self, pos: dict, current_price: float):
        sl = pos["sl_price"]
        tp = pos["tp_price"]
        if pos["side"] == "BUY":
            if current_price <= sl:
                return "SL"
            if current_price >= tp:
                return "TP"
        else:
            if current_price >= sl:
                return "SL"
            if current_price <= tp:
                return "TP"
        return None

    # ------------------------------------------------------------------
    # Mở / Đóng vị thế ảo
    # ------------------------------------------------------------------
    def _open_position(self, side: str, current_price: float,
                       qty: float, sl_pct: float, tp_pct: float) -> int:
        ticket = self._next_ticket()
        if side == "BUY":
            sl_price = current_price * (1 - sl_pct)
            tp_price = current_price * (1 + tp_pct)
        else:
            sl_price = current_price * (1 + sl_pct)
            tp_price = current_price * (1 - tp_pct)

        self.active_trade_loggers[ticket] = {
            "side": side,
            "entry_price": current_price,
            "qty": qty,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "entry_time": time.time(),
            "last_pnl_notify_time": 0.0,
        }
        self.total_trades += 1

        msg = (
            f"🎭 [SIM] ĐÃ MỞ {side} #{ticket}\n"
            f"Giá vào: {current_price:.4f}\n"
            f"SL: {sl_price:.4f} ({sl_pct*100:.1f}%) | "
            f"TP: {tp_price:.4f} ({tp_pct*100:.1f}%)\n"
            f"Qty: {qty}"
        )
        self.log_callback(
            f"[SimTM] 🔥 MỞ {side} #{ticket} | "
            f"Giá: {current_price:.4f} | SL: {sl_price:.4f} | "
            f"TP: {tp_price:.4f} | Qty: {qty}"
        )
        self.tg_notify(msg)
        return ticket

    def _close_position(self, ticket: int, reason: str, current_price: float):
        pos = self.active_trade_loggers.pop(ticket, None)
        if not pos:
            return

        pnl = self._calc_pnl(pos, current_price)
        self.total_pnl_usdt += pnl
        if pnl > 0:
            self.win_trades += 1

        # Reset daily stats nếu sang ngày mới (UTC)
        today = datetime.now(timezone.utc).date()
        if today != self._daily_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_wins = 0
            self._daily_date = today

        self.daily_pnl += pnl
        self.daily_trades += 1
        if pnl > 0:
            self.daily_wins += 1

        elapsed_min = int((time.time() - pos["entry_time"]) / 60)
        pnl_icon = "🟢" if pnl >= 0 else "🔴"
        wr_pct = (self.win_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        d_wr_pct = (self.daily_wins / self.daily_trades * 100) if self.daily_trades > 0 else 0.0

        msg = (
            f"🎭 [SIM] CHỐT {pos['side']} #{ticket}\n"
            f"Lý do: {reason}\n"
            f"Vào: {pos['entry_price']:.4f} → Ra: {current_price:.4f}\n"
            f"{pnl_icon} P&L: {pnl:+.2f} USDT | Giữ: {elapsed_min}p\n"
            f"📅 Hôm nay: {self.daily_pnl:+.2f} USDT | "
            f"WR ngày: {d_wr_pct:.1f}% ({self.daily_wins}/{self.daily_trades})\n"
            f"📊 Tổng: {self.total_pnl_usdt:+.2f} USDT | "
            f"WR all: {wr_pct:.1f}% ({self.win_trades}/{self.total_trades})"
        )
        self.log_callback(f"[SimTM] {msg}")
        self.tg_notify(msg)
        self.last_close_time = time.time()

    # ------------------------------------------------------------------
    # Điểm vào chính — gọi mỗi nến M1
    # ------------------------------------------------------------------
    def execute_trade(self, action: str, probs_dict: dict,
                      mse_loss: float, actual_target_sym: str = None):
        current_price = self._get_price()
        if current_price <= 0:
            self.log_callback("[SimTM] ⚠️ Không lấy được giá thị trường.")
            return

        fe_cfg = self.config.get("FEATURE_ENGINEERING", {})
        sl_pct = fe_cfg.get("SL_PCT", 0.005)
        tp_pct = fe_cfg.get("TP_PCT", 0.007)

        exec_cfg = self.config.get("LIVE_BOT", {}).get("SIMULATED_EXECUTION", {})
        qty = exec_cfg.get("LOT_SIZE", 0.5)

        # --- Bước 1: Kiểm tra SL/TP cho các lệnh đang mở ---
        just_closed = False
        for ticket in list(self.active_trade_loggers.keys()):
            pos = self.active_trade_loggers.get(ticket)
            if not pos:
                continue
            hit = self._check_sl_tp(pos, current_price)
            if hit:
                self._close_position(ticket, hit, current_price)
                just_closed = True

        has_open = len(self.active_trade_loggers) > 0

        # --- Bước 2: Đảo chiều nếu signal ngược ---
        for ticket in list(self.active_trade_loggers.keys()):
            pos = self.active_trade_loggers.get(ticket)
            if not pos:
                continue
            if pos["side"] == "BUY" and action == "SELL":
                self.gui_action = f"[SIM] ĐẢO CHIỀU: CHỐT BUY #{ticket}"
                self._close_position(ticket, "Đảo chiều sang SELL", current_price)
                has_open = False
                just_closed = True
            elif pos["side"] == "SELL" and action == "BUY":
                self.gui_action = f"[SIM] ĐẢO CHIỀU: CHỐT SELL #{ticket}"
                self._close_position(ticket, "Đảo chiều sang BUY", current_price)
                has_open = False
                just_closed = True
            elif action in ("HOLD", "TÍN_HIỆU_RÁC"):
                pnl = self._calc_pnl(pos, current_price)
                pnl_icon = "🟢" if pnl >= 0 else "🔴"
                self.gui_action = (
                    f"[SIM] GIỮ {pos['side']} #{ticket} "
                    f"{pnl_icon} {pnl:+.2f}$"
                )

        # --- Bước 3: Mở lệnh mới nếu không có vị thế ---
        if not has_open:
            cooldown_remain = 60 - (time.time() - self.last_close_time)
            if just_closed and cooldown_remain > 0:
                self.gui_action = f"[SIM] Cooldown {int(cooldown_remain)}s..."
            elif action == "BUY":
                t = self._open_position("BUY", current_price, qty, sl_pct, tp_pct)
                self.gui_action = f"[SIM] 🔥 MỞ BUY #{t} @ {current_price:.4f}"
            elif action == "SELL":
                t = self._open_position("SELL", current_price, qty, sl_pct, tp_pct)
                self.gui_action = f"[SIM] 🔥 MỞ SELL #{t} @ {current_price:.4f}"
            else:
                self.gui_action = f"[SIM] Bỏ qua ({action})"

    # ------------------------------------------------------------------
    # Báo cáo vị thế hiện tại (hiển thị trong msg_pred log mỗi phút)
    # ------------------------------------------------------------------
    def get_active_positions_report(self) -> str:
        if not self.active_trade_loggers:
            return ""

        current_price = self._get_price()
        lines = []
        for ticket, pos in self.active_trade_loggers.items():
            pnl = self._calc_pnl(pos, current_price)
            pnl_icon = "🟢" if pnl >= 0 else "🔴"
            elapsed = int((time.time() - pos["entry_time"]) / 60)
            lines.append(
                f"  {pnl_icon} {pos['side']} #{ticket} | "
                f"Vào: {pos['entry_price']:.4f} | "
                f"P&L: {pnl:+.2f}$ | {elapsed}p"
            )
        return "🎭 [SIM] Vị thế:\n" + "\n".join(lines)

    def get_daily_pnl_summary(self) -> str:
        """Tóm tắt lãi/lỗ hôm nay (đã đóng + đang mở)."""
        today = datetime.now(timezone.utc).date()
        if today != self._daily_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_wins = 0
            self._daily_date = today

        current_price = self._get_price()
        unrealized = sum(
            self._calc_pnl(p, current_price)
            for p in self.active_trade_loggers.values()
        )
        today_total = self.daily_pnl + unrealized
        d_wr_pct = (self.daily_wins / self.daily_trades * 100) if self.daily_trades > 0 else 0.0
        wr_pct = (self.win_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0

        icon = "🟢" if today_total >= 0 else "🔴"
        return (
            f"{icon} Hôm nay: {today_total:+.2f} USDT "
            f"(Đóng: {self.daily_pnl:+.2f} | Mở: {unrealized:+.2f})\n"
            f"  WR ngày: {d_wr_pct:.1f}% ({self.daily_wins}/{self.daily_trades}) | "
            f"Tổng all: {self.total_pnl_usdt+unrealized:+.2f} USDT | "
            f"WR all: {wr_pct:.1f}%"
        )
