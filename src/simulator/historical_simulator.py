"""
Historical Brain Simulator - Phiên bản V2
==========================================
Replay dữ liệu lịch sử M1 qua toàn bộ pipeline AI của bot_v3.
Sử dụng V3VirtualTradeManager (module gốc) để quản lý vị thế —
đảm bảo thuật toán 100% giống live: trailing stop, MAX_HOLD_BARS,
reversal, cooldown 60s, KHÔNG mở thêm khi đang có vị thế.

Usage:
    C:\\argo\\venv\\Scripts\\python.exe scripts/run_simulator.py \\
        --config data/bot_config_xag_asian_v5.json \\
        --date 2026-05-14 --session asian
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_LEGACY = os.path.join(_ROOT, "huyen_thoai")
if _LEGACY not in sys.path:
    sys.path.insert(0, _LEGACY)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
#  Hàm tiện ích
# ═══════════════════════════════════════════════════════

def _load_parquet(parquet_path: str) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)
    if not isinstance(df.index, pd.DatetimeIndex):
        if "time" in df.columns:
            df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
            df.set_index("datetime", inplace=True)
        else:
            raise ValueError(f"Không có DatetimeIndex trong {parquet_path}")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="last")]
    df.sort_index(inplace=True)
    return df


def _merge_symbols(symbol_dfs: dict, prefix_map: dict) -> pd.DataFrame:
    renamed_list = []
    for sym_key, df in symbol_dfs.items():
        prefix = prefix_map.get(sym_key, sym_key)
        rename_map = {}
        for col in df.columns:
            if col in ("open", "high", "low", "close", "volume", "real_volume", "spread"):
                rename_map[col] = f"{prefix}_{col}" if col != "volume" else f"{prefix}_volume"
        df_r = df.rename(columns=rename_map)
        keep_cols = [v for v in rename_map.values() if v in df_r.columns]
        renamed_list.append(df_r[keep_cols])

    merged = pd.concat(renamed_list, axis=1)
    merged = merged.loc[:, ~merged.columns.duplicated()].copy()
    merged.sort_index(inplace=True)
    merged.ffill(limit=120, inplace=True)
    vol_cols = [c for c in merged.columns if "volume" in c.lower()]
    merged[vol_cols] = merged[vol_cols].fillna(0)
    return merged


def _add_time_embeddings(df: pd.DataFrame) -> pd.DataFrame:
    try:
        from src.core.feature_engineering import add_time_embeddings
        return add_time_embeddings(df)
    except Exception as e:
        logger.warning(f"[Simulator] Không thể import add_time_embeddings: {e}")
        return df


# ═══════════════════════════════════════════════════════
#  Class Chính
# ═══════════════════════════════════════════════════════

class HistoricalSimulator:
    """
    Giả lập nguồn dữ liệu đầu vào bằng dữ liệu lịch sử M1.

    Thiết kế:
    - Chỉ thay thế NGUỒN DỮ LIỆU (parquet thay MT5 live)
    - Toàn bộ pipeline xử lý và trade logic dùng module gốc của bot_v3
    - V3VirtualTradeManager đảm bảo: không mở 2 lệnh, trailing stop,
      MAX_HOLD_BARS, reversal, cooldown — giống live 100%
    """

    SESSION_HOURS = {
        "asian":  (0, 7),
        "london": (7, 13),
        "ny":     (13, 21),
        "all":    (0, 24),
    }

    def __init__(
        self,
        config_path: str,
        model_path: Optional[str] = None,
        scaler_path: Optional[str] = None,
        window_size: int = 1500,
        log_callback=None,
        force_cpu: bool = False
    ):
        self.force_cpu = force_cpu
        self.log = log_callback or (lambda msg: print(f"[SIM] {msg}"))
        self.window_size = window_size

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        config_id      = self.config.get("CONFIG_ID", "CFG_UNKNOWN")
        target_prefix  = self.config.get("TARGET_PREFIX", "XAGUSD")
        fe_cfg         = self.config.get("FEATURE_ENGINEERING", {})
        self.seq_len   = fe_cfg.get("WINDOW_SIZE", 60)

        workspace_dir = os.path.join(_ROOT, "workspaces", config_id)

        # Auto-detect model path
        if model_path is None:
            brains_dir  = os.path.join(workspace_dir, "brains")
            found       = list(Path(brains_dir).glob("*.pth")) if os.path.exists(brains_dir) else []
            if not found:
                raise FileNotFoundError(f"Không có .pth trong {brains_dir}")
            model_path  = str(sorted(found, key=os.path.getmtime)[-1])
            self.log(f"Auto-detect model: {os.path.basename(model_path)}")

        # Auto-detect scaler path
        if scaler_path is None:
            scaler_json = os.path.join(_ROOT, "data", f"scaler_{config_id}.json")
            scaler_pkl  = os.path.join(_ROOT, "data", f"scaler_{config_id}.pkl")
            if os.path.exists(scaler_json):
                scaler_path = scaler_json
            elif os.path.exists(scaler_pkl):
                scaler_path = scaler_pkl
            else:
                raise FileNotFoundError(f"Không tìm thấy scaler cho {config_id}")
            self.log(f"Auto-detect scaler: {os.path.basename(scaler_path)}")

        self.model_path    = model_path
        self.scaler_path   = scaler_path
        self.config_id     = config_id
        self.target_prefix = target_prefix
        self.raw_dir       = os.path.join(workspace_dir, "data", "raw")

        self._engine        = None
        self._processor     = None
        self._symbol_dfs: dict = {}
        self._merged_full: Optional[pd.DataFrame] = None

    # ── lazy loaders ──────────────────────────────────────

    def _ensure_engine(self):
        if self._engine is not None:
            return

        arch       = self.config.get("TRAINING", {})
        d_model    = arch.get("D_MODEL", 128)
        nhead      = arch.get("N_HEAD", 8)
        num_layers = arch.get("NUM_LAYERS", 3)
        
        if self.config.get("LIVE_BOT", {}).get("MODEL_TYPE", "") == "V6":
            from src.bot_v6.inference_engine_v6 import V6InferenceEngine
            self._engine = V6InferenceEngine(log_callback=self.log, force_cpu=self.force_cpu)
        else:
            from src.bot_v3.inference_engine_v3 import V3InferenceEngine
            self._engine = V3InferenceEngine(log_callback=self.log)

        is_v6 = self.config.get("LIVE_BOT", {}).get("MODEL_TYPE", "") == "V6"
        if is_v6:
            ok = self._engine.load_weights(self.model_path, self.config)
        else:
            ok = self._engine.load_weights(
                model_path=self.model_path,
                num_features=999,
                d_model=d_model,
                nhead=nhead,
                num_attn_layers=num_layers,
                seq_len=self.seq_len
            )
        if not ok:
            raise RuntimeError("Không thể load model weights!")

        bot_cfg     = self.config.get("LIVE_BOT", {})
        raw_mse_thr = bot_cfg.get("MAX_ABSOLUTE_MSE", None)
        if raw_mse_thr is None or raw_mse_thr <= 1.0:
            # Model V5 dùng percentile gate → disable absolute MSE filter
            self._engine.mse_threshold = 99999.0
            self.log("⚠️ MSE gate DISABLED (V5 percentile mode)")
        else:
            self._engine.mse_threshold = raw_mse_thr

        self._engine.prob_threshold = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.53)
        self.log(f"Engine OK | MSE≤{self._engine.mse_threshold} | Prob≥{self._engine.prob_threshold}")

    def _ensure_processor(self, inference_feats):
        if self._processor is not None:
            return
        from src.bot_v3.data_processor_v3 import V3DataProcessor
        model_input_dim = getattr(self._engine, "num_features", None)
        self._processor = V3DataProcessor(
            scaler_path=self.scaler_path,
            inference_feats=inference_feats,
            window_size=self.seq_len,
            config=self.config,
            log_callback=self.log,
            model_input_dim=model_input_dim,
        )

    def _load_parquets(self):
        if not os.path.exists(self.raw_dir):
            raise FileNotFoundError(f"Không có raw dir: {self.raw_dir}")
        parquet_files = list(Path(self.raw_dir).glob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"Không có .parquet trong {self.raw_dir}")
        self.log(f"Loading {len(parquet_files)} parquet files...")
        for pf in parquet_files:
            sym_key = pf.stem.split("_")[0]
            df = _load_parquet(str(pf))
            self._symbol_dfs[sym_key] = df
            self.log(f"  {sym_key}: {len(df):,} nến | {df.index.min()} → {df.index.max()}")

    def _build_full_merged(self):
        if self._merged_full is not None:
            return
        self._load_parquets()
        routing    = self.config.get("DATA_SOURCE", {}).get("ROUTING", {})
        prefix_map = {sym_m.replace("m", "").replace("M", ""): sym_m.replace("m", "").replace("M", "")
                      for sym_m in routing.keys()}
        filtered   = {k: v for k, v in self._symbol_dfs.items() if k in prefix_map}
        if not filtered:
            filtered   = self._symbol_dfs
            prefix_map = {k: k for k in filtered.keys()}
            self.log("⚠️ Không match routing → dùng tất cả parquet")
        self.log(f"Merging {list(filtered.keys())}...")
        merged             = _merge_symbols(filtered, prefix_map)
        merged             = _add_time_embeddings(merged)
        self._merged_full  = merged
        self.log(f"Merged: {len(merged):,} rows × {len(merged.columns)} cols")

    def fetch_history_for_candle(self, candle_time: pd.Timestamp) -> Optional[pd.DataFrame]:
        idx_array = self._merged_full.index.get_indexer([candle_time], method='pad')
        if len(idx_array) == 0 or idx_array[0] == -1:
            return None
        idx = idx_array[0]
        if idx + 1 < self.seq_len + 10:
            return None
        start_idx = max(0, idx + 1 - self.window_size)
        return self._merged_full.iloc[start_idx : idx + 1]

    # ── main run ─────────────────────────────────────────

    def run(self, date_str: str, session: str = "asian") -> pd.DataFrame:
        """
        Chạy simulator cho 1 phiên trong 1 ngày.

        Dùng V3VirtualTradeManager (module gốc bot_v3) để quản lý vị thế:
        - KHÔNG mở 2 lệnh cùng lúc (giống live)
        - Đảo chiều khi có tín hiệu ngược (giống live)
        - Cooldown 60s sau khi đóng lệnh (giống live)
        - MAX_HOLD_BARS: tự động đóng lệnh quá hạn (giống live)
        - Trailing Stop (giống live)
        """
        self.log("=" * 60)
        self.log(f"SIMULATOR V2 | Date={date_str} | Session={session.upper()}")
        self.log("=" * 60)

        self._build_full_merged()
        self._ensure_engine()

        # ── Khởi tạo VirtualTradeManager (module gốc bot_v3) ──
        from src.simulator.backtest_vtm import BacktestVirtualTradeManager

        target_symbol = self.config.get("TARGET_SYMBOL", "XAGUSDm")
        # Tên symbol sim để tránh ghi đè state file bot live
        sim_symbol    = f"SIM_{target_symbol}"
        virtual_tm    = BacktestVirtualTradeManager(
            target_symbol=sim_symbol,
            config=self.config,
            log_callback=self.log,
            tg_notify_callback=lambda x: None,  # Tắt Telegram trong sim
        )
        # Reset state sạch — mỗi lần chạy sim bắt đầu từ đầu
        virtual_tm.active_trade_loggers = {}
        virtual_tm.history_deals        = []
        virtual_tm.virtual_balance      = 10000.0
        virtual_tm.last_close_time      = 0
        self.log(f"✅ VirtualTradeManager OK | Balance={virtual_tm.virtual_balance:.2f}$")
        self.log("📌 Logic trade: KHÔNG mở 2 lệnh, Trailing Stop, MAX_HOLD_BARS, Reversal, Cooldown")

        # ── Khoảng thời gian phiên ──
        target_date   = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        hour_start, hour_end = self.SESSION_HOURS.get(session.lower(), (0, 24))
        session_start = target_date + timedelta(hours=hour_start)
        session_end   = target_date + timedelta(hours=hour_end)

        target_col = f"{self.target_prefix}_close"
        if target_col not in self._merged_full.columns:
            candidates = [c for c in self._merged_full.columns if "close" in c.lower()]
            target_col = candidates[0] if candidates else None
        if target_col is None:
            raise ValueError(f"Không tìm thấy cột close cho {self.target_prefix}")

        prefix = target_col.replace("_close", "")
        open_col = f"{prefix}_open"
        high_col = f"{prefix}_high"
        low_col = f"{prefix}_low"

        session_df = self._merged_full[
            (self._merged_full.index >= session_start) &
            (self._merged_full.index <  session_end) &
            (self._merged_full[target_col].notna())
        ]

        if len(session_df) == 0:
            self.log(f"⚠️ Không có data cho {session} {date_str}")
            self.log(f"   Range: {self._merged_full.index.min()} → {self._merged_full.index.max()}")
            return pd.DataFrame()

        self.log(f"Phiên {session.upper()}: {len(session_df)} nến M1")

        # ── Processor ──
        n_feat = self._engine.num_features
        self._ensure_processor(list(range(n_feat)))

        # ── Point size và Config Backtest ──
        fe_config = self.config.get("FEATURE_ENGINEERING", {})
        point = fe_config.get("PIP_SIZE", 0.001)
        # Anh có thể map slippage và spread mặc định từ config, ở đây lấy cứng hoặc từ data
        default_spread_pips = self.config.get("SIMULATOR", {}).get("SPREAD_PIPS", 1.0)
        slippage_pips = self.config.get("SIMULATOR", {}).get("SLIPPAGE_PIPS", 0.5) 

        # ── Khoảng thời gian phiên ──
        # ── Biến lưu tín hiệu chờ khớp (Mô phỏng Latency) ──
        # ĐÃ BỎ: Thay bằng BacktestVirtualTradeManager

        # ── Replay từng nến ──
        results       = []
        candle_times  = session_df.index.tolist()
        self.log(f"Replay {len(candle_times)} nến...")

        for candle_time in candle_times:
            row = session_df.loc[candle_time]
            close_p = row[target_col]
            open_p = row[open_col] if open_col in session_df.columns else close_p
            high_p = row[high_col] if high_col in session_df.columns else close_p
            low_p = row[low_col] if low_col in session_df.columns else close_p
            
            # Nếu parquet lưu spread theo points, quy đổi ra pips (chia 10)
            c_spread = f"{prefix}_spread"
            raw_spread = row.get(c_spread, default_spread_pips * 10)
            spread_pips = raw_spread / 10.0 if raw_spread > 0 else default_spread_pips

            virtual_tm.sim_clock = candle_time.timestamp()

            # Bước 1: Dùng hàm OHLC để khớp pending, sweep râu và dời trailing
            virtual_tm.update_virtual_positions_ohlc(
                open_p=open_p,
                high_p=high_p,
                low_p=low_p,
                close_p=close_p,
                point=point,
                spread_pips=spread_pips,
                slippage_pips=slippage_pips
            )

            # Bước 2: Lấy window lịch sử cho pipeline AI
            window_df = self.fetch_history_for_candle(candle_time)
            if window_df is None:
                continue

            # Bước 3: FE + Scale + Inference
            try:
                tensor, p_err = self._processor.ingest_and_scale(window_df)
            except Exception as e:
                self.log(f"⚠️ [{candle_time.strftime('%H:%M')}] Pipeline lỗi: {e}")
                continue

            if p_err or tensor is None:
                continue

            action, mse, probs = self._engine.predict(tensor)
            if action is None:
                continue

            # Bước 4: Chờ khớp lệnh ở nến tiếp theo (Mô phỏng Latency)
            if action in ("BUY", "SELL"):
                close_ask = close_p + (spread_pips * point * 10)
                virtual_tm.execute_trade(
                    action=action,
                    probs_dict=probs,
                    mse_loss=mse,
                    current_bid=close_p,
                    current_ask=close_ask,
                    point=point,
                    actual_target_sym=target_symbol,
                )

            # Bước 5: Ghi log
            results.append({
                "time":        candle_time,
                "close":       close_p,
                "action":      action,
                "gui_action":  "PENDING_EXEC" if action in ("BUY", "SELL") else virtual_tm.gui_action,
                "buy_prob":    probs.get("buy", 0),
                "sell_prob":   probs.get("sell", 0),
                "hold_prob":   probs.get("hold", 0),
                "mse":         mse,
                "n_positions": len(virtual_tm.active_trade_loggers),
                "balance":     virtual_tm.virtual_balance,
            })

            if action in ("BUY", "SELL"):
                self.log(
                    f"🔔 [{candle_time.strftime('%H:%M')}] {action} | "
                    f"B={probs.get('buy',0):.2f} S={probs.get('sell',0):.2f} | "
                    f"→ PENDING_EXEC (Delay sang nến kế)"
                )

        # ── Tổng kết ──
        result_df = pd.DataFrame(results)
        self._print_summary(virtual_tm, result_df, date_str, session)
        return result_df

    def _print_summary(self, virtual_tm, result_df: pd.DataFrame, date_str: str, session: str):
        deals  = virtual_tm.history_deals
        n_win  = sum(1 for d in deals if d.get("profit", 0) > 0)
        n_loss = sum(1 for d in deals if d.get("profit", 0) <= 0)
        total  = n_win + n_loss
        wr     = n_win / total * 100 if total > 0 else 0
        pnl    = sum(d.get("profit", 0) for d in deals)

        n_buy  = len(result_df[result_df["action"] == "BUY"])  if not result_df.empty else 0
        n_sell = len(result_df[result_df["action"] == "SELL"]) if not result_df.empty else 0

        self.log("")
        self.log("╔══════════════════════════════════════════╗")
        self.log(f"║  KẾT QUẢ: {session.upper()} {date_str}")
        self.log("╠══════════════════════════════════════════╣")
        self.log(f"║  Tín hiệu BUY / SELL  : {n_buy} / {n_sell}")
        self.log(f"║  Lệnh đóng (W/L)      : {total} ({n_win}W/{n_loss}L)")
        self.log(f"║  Win Rate             : {wr:.1f}%")
        self.log(f"║  P&L ($)              : {pnl:+.4f}")
        self.log(f"║  Balance cuối ($)     : {virtual_tm.virtual_balance:.2f}")
        self.log("╠══════════════════════════════════════════╣")
        
        import os
        import json
        log_file = "simulator_daily_results.csv"
        write_header = not os.path.exists(log_file)
        with open(log_file, "a", encoding="utf-8") as f:
            if write_header:
                f.write("Date,Session,Total_Signals,BUY_Signals,SELL_Signals,Total_Deals,Win,Loss,WinRate_%,PnL,End_Balance\n")
            f.write(f"{date_str},{session.upper()},{n_buy+n_sell},{n_buy},{n_sell},{total},{n_win},{n_loss},{wr:.1f},{pnl:.4f},{virtual_tm.virtual_balance:.2f}\n")

        # ThÃªm kÃªt quáº£ vÃ o metric cá»§a bá»™ nÃ£o
        if hasattr(self, 'model_path') and self.model_path:
            try:
                run_dir = os.path.dirname(os.path.dirname(self.model_path))
                metrics_path = os.path.join(run_dir, "results", "training_metrics_v3.json")
                if os.path.exists(metrics_path):
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        metrics_data = json.load(f)
                    
                    if "simulator_results" not in metrics_data:
                        metrics_data["simulator_results"] = []
                        
                    metrics_data["simulator_results"].append({
                        "date": date_str,
                        "session": session.upper(),
                        "total_signals": n_buy + n_sell,
                        "buy": n_buy,
                        "sell": n_sell,
                        "deals": total,
                        "win": n_win,
                        "loss": n_loss,
                        "win_rate": wr,
                        "pnl": pnl,
                        "balance": virtual_tm.virtual_balance
                    })
                    
                    with open(metrics_path, "w", encoding="utf-8") as f:
                        json.dump(metrics_data, f, indent=4)
            except Exception as e:
                self.log(f"Lá»—i ghi metric vÃ o bÃ£o: {e}")

        if deals:
            self.log("║  CHI TIẾT LỆNH:")
            for d in deals:
                icon  = "✅" if d.get("profit", 0) > 0 else "❌"
                t     = d.get("close_time", "?")
                t_str = t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)
                self.log(
                    f"║  {icon} {d.get('order_type','?'):4} "
                    f"In={d.get('entry_price',0):.4f} "
                    f"Out={d.get('close_price',0):.4f} "
                    f"PnL={d.get('profit',0):+.4f} "
                    f"[{d.get('reason','?')}] @{t_str}"
                )
        self.log("╚══════════════════════════════════════════╝")
