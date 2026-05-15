"""
Historical Brain Simulator - Phiên bản V1
==========================================
Replay dữ liệu lịch sử M1 qua toàn bộ pipeline AI của bot_v3 (FE → Scale → Inference),
KHÔNG cần MT5 live, KHÔNG sửa code bot gốc.

Cơ chế hoạt động:
  - Đọc file .parquet lịch sử (đã có sẵn trong workspace/data/raw/)
  - Merge các symbol (XAGUSD, XAUUSD, BTC, ETH...) theo timestamp
  - Với mỗi nến M1 trong khoảng thời gian muốn kiểm tra:
      → Cắt cửa sổ trượt 1500 nến gần nhất
      → Chạy qua V3DataProcessor (FE + Scale)
      → Chạy qua V3InferenceEngine (AI predict)
      → Ghi nhận tín hiệu + tính P&L ảo theo TP/SL
  - Output: bảng kết quả từng tín hiệu + tổng kết thống kê

Usage:
    python scripts/run_simulator.py \\
        --config data/bot_config_xag_asian_v5.json \\
        --date 2026-05-14 \\
        --session asian
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
#  Hàm tiện ích
# ═══════════════════════════════════════════════════════

def _load_parquet(parquet_path: str) -> pd.DataFrame:
    """Load một file parquet, trả về DataFrame với index là DatetimeTzAware UTC."""
    df = pd.read_parquet(parquet_path)
    if not isinstance(df.index, pd.DatetimeIndex):
        if "time" in df.columns:
            df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
            df.set_index("datetime", inplace=True)
        else:
            raise ValueError(f"Không có cột time hay DatetimeIndex trong {parquet_path}")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="last")]
    df.sort_index(inplace=True)
    return df


def _merge_symbols(symbol_dfs: dict, prefix_map: dict) -> pd.DataFrame:
    """
    Merge nhiều symbol DataFrame thành 1 wide DataFrame giống cấu trúc
    mà MT5DataManager.get_live_merged_data_in_memory() trả về.

    symbol_dfs: {sym_key: df}  e.g. {"XAGUSD": df_xag, "XAUUSD": df_xau}
    prefix_map: {sym_key: mapped_prefix}  e.g. {"XAGUSD": "XAGUSD", "XAUUSD": "XAUUSD"}
    """
    renamed_list = []
    for sym_key, df in symbol_dfs.items():
        prefix = prefix_map.get(sym_key, sym_key)
        rename_map = {}
        for col in df.columns:
            if col in ("open", "high", "low", "close", "volume", "real_volume", "spread"):
                if col == "volume":
                    rename_map[col] = f"{prefix}_volume"
                else:
                    rename_map[col] = f"{prefix}_{col}"
        df_r = df.rename(columns=rename_map)
        # Giữ lại chỉ các cột đã được rename (loại bỏ cột không liên quan)
        keep_cols = [v for v in rename_map.values() if v in df_r.columns]
        renamed_list.append(df_r[keep_cols])

    merged = pd.concat(renamed_list, axis=1)
    merged = merged.loc[:, ~merged.columns.duplicated()].copy()
    merged.sort_index(inplace=True)
    merged.ffill(limit=120, inplace=True)

    # Fill volume NaN = 0
    vol_cols = [c for c in merged.columns if "volume" in c.lower()]
    merged[vol_cols] = merged[vol_cols].fillna(0)

    return merged


def _add_time_embeddings(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm time embeddings (giống logic trong mt5_data_manager)."""
    try:
        from src.core.feature_engineering import add_time_embeddings
        return add_time_embeddings(df)
    except Exception as e:
        logger.warning(f"[Simulator] Không thể import add_time_embeddings: {e}. Bỏ qua.")
        return df


# ═══════════════════════════════════════════════════════
#  Class Chính
# ═══════════════════════════════════════════════════════

class HistoricalSimulator:
    """
    Giả lập nguồn dữ liệu đầu vào bằng dữ liệu lịch sử M1.
    Chạy toàn bộ pipeline AI: FE → Scale → Inference.
    """

    # Phiên giao dịch theo UTC
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
    ):
        self.log = log_callback or (lambda msg: print(f"[SIM] {msg}"))
        self.window_size = window_size  # Số nến rolling window

        # Load config
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        config_id = self.config.get("CONFIG_ID", "CFG_UNKNOWN")
        target_prefix = self.config.get("TARGET_PREFIX", "XAGUSD")
        fe_cfg = self.config.get("FEATURE_ENGINEERING", {})
        self.seq_len = fe_cfg.get("WINDOW_SIZE", 60)  # Window size cho model (60-90 nến)
        self.tp_pct = fe_cfg.get("TP_PCT", 0.003)
        self.sl_pct = fe_cfg.get("SL_PCT", 0.003)

        # Auto-detect paths nếu không truyền vào
        workspace_dir = os.path.join(_ROOT, "workspaces", config_id)
        if model_path is None:
            brains_dir = os.path.join(workspace_dir, "brains")
            found_models = list(Path(brains_dir).glob("*.pth")) if os.path.exists(brains_dir) else []
            if not found_models:
                raise FileNotFoundError(f"Không tìm thấy file .pth trong {brains_dir}")
            # Lấy file mới nhất
            model_path = str(sorted(found_models, key=os.path.getmtime)[-1])
            self.log(f"Auto-detect model: {os.path.basename(model_path)}")

        if scaler_path is None:
            # Thử json trước, fallback pkl
            scaler_json = os.path.join(_ROOT, "data", f"scaler_{config_id}.json")
            scaler_pkl = os.path.join(_ROOT, "data", f"scaler_{config_id}.pkl")
            if os.path.exists(scaler_json):
                scaler_path = scaler_json
            elif os.path.exists(scaler_pkl):
                scaler_path = scaler_pkl
            else:
                raise FileNotFoundError(f"Không tìm thấy scaler cho {config_id}")
            self.log(f"Auto-detect scaler: {os.path.basename(scaler_path)}")

        self.model_path = model_path
        self.scaler_path = scaler_path
        self.config_id = config_id
        self.target_prefix = target_prefix

        # Raw data directory
        self.raw_dir = os.path.join(workspace_dir, "data", "raw")

        # Khởi tạo engine + processor
        self._engine = None
        self._processor = None
        self._symbol_dfs: dict = {}      # Cache các parquet đã load
        self._merged_full: Optional[pd.DataFrame] = None  # Full merged dataframe

    def _ensure_engine(self):
        """Lazy-load model weights."""
        if self._engine is not None:
            return
        from src.bot_v3.inference_engine_v3 import V3InferenceEngine

        arch = self.config.get("TRAINING", {})
        d_model = arch.get("D_MODEL", 128)
        nhead = arch.get("N_HEAD", 8)
        num_layers = arch.get("NUM_LAYERS", 3)

        self._engine = V3InferenceEngine(log_callback=self.log)
        ok = self._engine.load_weights(
            model_path=self.model_path,
            num_features=999,   # Sẽ bị auto-detect từ weights
            d_model=d_model,
            nhead=nhead,
            num_attn_layers=num_layers,
            window_size=self.seq_len,
        )
        if not ok:
            raise RuntimeError("Không thể load model weights!")

        # Set ngưỡng từ config
        bot_cfg = self.config.get("LIVE_BOT", {})

        # Model V5 dùng percentile-based MSE gate trong training (MSE_GATE_PERCENTILE=0.05),
        # không có mse_threshold_value cố định. Dùng giá trị rất lớn để disable MSE filter
        # trong simulator (chỉ lọc bằng probability threshold)
        raw_mse_thr = bot_cfg.get("MAX_ABSOLUTE_MSE", None)
        if raw_mse_thr is None or raw_mse_thr <= 1.0:
            # Disable MSE gate — model V5 không dùng fixed threshold
            self._engine.mse_threshold = 99999.0
            self.log("⚠️ MSE gate DISABLED (model V5 dùng percentile gate, không phải absolute)")
        else:
            self._engine.mse_threshold = raw_mse_thr

        self._engine.prob_threshold = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.53)
        self.log(f"Engine sẵn sàng | MSE≤{self._engine.mse_threshold} | Prob≥{self._engine.prob_threshold}")

    def _ensure_processor(self, inference_feats):
        """Khởi tạo DataProcessor."""
        if self._processor is not None:
            return
        from src.bot_v3.data_processor_v3 import V3DataProcessor

        model_input_dim = getattr(self._engine, "num_features", None) if self._engine else None
        self._processor = V3DataProcessor(
            scaler_path=self.scaler_path,
            inference_feats=inference_feats,
            window_size=self.seq_len,
            config=self.config,
            log_callback=self.log,
            model_input_dim=model_input_dim,
        )

    def _load_parquets(self):
        """Load tất cả parquet symbols cần thiết."""
        if not os.path.exists(self.raw_dir):
            raise FileNotFoundError(f"Thư mục raw data không tồn tại: {self.raw_dir}")

        parquet_files = list(Path(self.raw_dir).glob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"Không có file .parquet nào trong {self.raw_dir}")

        self.log(f"Đang load {len(parquet_files)} parquet files...")
        for pf in parquet_files:
            # Tên file: XAGUSD_MT5_1M_2026.parquet → sym_key = "XAGUSD"
            sym_key = pf.stem.split("_")[0]
            df = _load_parquet(str(pf))
            self._symbol_dfs[sym_key] = df
            self.log(f"  {sym_key}: {len(df):,} nến | {df.index.min()} → {df.index.max()}")

    def _build_full_merged(self):
        """Merge tất cả symbols thành 1 wide DataFrame."""
        if self._merged_full is not None:
            return

        self._load_parquets()

        # Build prefix map từ config ROUTING
        routing = self.config.get("DATA_SOURCE", {}).get("ROUTING", {})
        # routing: {"XAGUSDm": "EXNESS", ...}
        # sym_key trong parquet: "XAGUSD" (không có m)
        prefix_map = {}
        for sym_m in routing.keys():
            sym_key = sym_m.replace("m", "").replace("M", "")
            # Target prefix: XAGUSD → cột sẽ là XAGUSD_close v.v.
            prefix_map[sym_key] = sym_key

        # Lọc chỉ symbols có trong parquet
        filtered_dfs = {k: v for k, v in self._symbol_dfs.items() if k in prefix_map}
        if not filtered_dfs:
            # Fallback: dùng tất cả symbols có
            filtered_dfs = self._symbol_dfs
            prefix_map = {k: k for k in filtered_dfs.keys()}
            self.log("⚠️ Không match routing → dùng tất cả parquet có sẵn")

        self.log(f"Merging {list(filtered_dfs.keys())}...")
        merged = _merge_symbols(filtered_dfs, prefix_map)

        # Thêm time embeddings (hour_sin, hour_cos, is_asian, v.v.)
        merged = _add_time_embeddings(merged)
        self._merged_full = merged
        self.log(f"Merged xong: {len(merged):,} rows × {len(merged.columns)} cols | {merged.index.min()} → {merged.index.max()}")

    def fetch_history_for_candle(self, candle_time: pd.Timestamp) -> Optional[pd.DataFrame]:
        """
        Lấy window dữ liệu kết thúc tại `candle_time` (giống cách bot lấy 1500 nến live).
        Trả về DataFrame với tối đa self.window_size nến gần nhất.
        """
        df = self._merged_full
        # Lọc đến candle_time (inclusive)
        subset = df[df.index <= candle_time]
        if len(subset) < self.seq_len + 10:
            return None
        return subset.tail(self.window_size)

    def run(
        self,
        date_str: str,
        session: str = "asian",
        extra_days_before: int = 2,
    ) -> pd.DataFrame:
        """
        Chạy simulator cho toàn bộ khoảng thời gian của 1 phiên trong 1 ngày.

        Args:
            date_str: Ngày cần giả lập, định dạng "YYYY-MM-DD"
            session: "asian" | "london" | "ny" | "all"
            extra_days_before: Số ngày lịch sử cần trước ngày mục tiêu để warm-up FE

        Returns:
            DataFrame kết quả với các tín hiệu + P&L
        """
        self.log(f"{'='*60}")
        self.log(f"SIMULATOR KHỞI ĐỘNG | Date={date_str} | Session={session.upper()}")
        self.log(f"{'='*60}")

        # 1. Build full merged data
        self._build_full_merged()

        # 2. Lazy-load engine
        self._ensure_engine()

        # 3. Xác định khoảng thời gian phiên
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        hour_start, hour_end = self.SESSION_HOURS.get(session.lower(), (0, 24))
        session_start = target_date + timedelta(hours=hour_start)
        session_end   = target_date + timedelta(hours=hour_end)

        # Lấy tất cả nến M1 trong phiên
        target_col = f"{self.target_prefix}_close"
        if target_col not in self._merged_full.columns:
            # Thử tên khác
            close_candidates = [c for c in self._merged_full.columns if "close" in c.lower()]
            if close_candidates:
                target_col = close_candidates[0]
            else:
                raise ValueError(f"Không tìm thấy cột close cho {self.target_prefix}")

        session_df = self._merged_full[
            (self._merged_full.index >= session_start) &
            (self._merged_full.index < session_end) &
            (self._merged_full[target_col].notna())
        ]

        if len(session_df) == 0:
            self.log(f"⚠️ KHÔNG CÓ DỮ LIỆU cho phiên {session} ngày {date_str}!")
            self.log(f"   Data range trong file: {self._merged_full.index.min()} → {self._merged_full.index.max()}")
            return pd.DataFrame()

        self.log(f"Phiên {session.upper()} có {len(session_df)} nến M1 ({session_start} → {session_end} UTC)")

        # 4. Khởi tạo processor (lazy, cần engine đã load để biết num_features)
        # Dùng integer list làm inference_feats (auto-trim mode)
        n_feat = self._engine.num_features
        self._ensure_processor(list(range(n_feat)))

        # 5. Replay từng nến
        results = []
        active_trade = None  # {"side": "BUY"|"SELL", "entry_price": x, "tp": x, "sl": x, "entry_time": t}

        candle_times = session_df.index.tolist()
        self.log(f"Bắt đầu replay {len(candle_times)} nến...")

        for i, candle_time in enumerate(candle_times):
            # Lấy window lịch sử
            window_df = self.fetch_history_for_candle(candle_time)
            if window_df is None:
                continue

            # Kiểm tra nếu đang giữ lệnh → check close
            close_price = session_df.loc[candle_time, target_col]
            pnl = 0.0
            trade_closed = None

            if active_trade:
                if active_trade["side"] == "BUY":
                    if close_price >= active_trade["tp"]:
                        pnl = active_trade["tp"] - active_trade["entry_price"]
                        trade_closed = "WIN"
                    elif close_price <= active_trade["sl"]:
                        pnl = active_trade["sl"] - active_trade["entry_price"]
                        trade_closed = "LOSS"
                elif active_trade["side"] == "SELL":
                    if close_price <= active_trade["tp"]:
                        pnl = active_trade["entry_price"] - active_trade["tp"]
                        trade_closed = "WIN"
                    elif close_price >= active_trade["sl"]:
                        pnl = active_trade["entry_price"] - active_trade["sl"]
                        trade_closed = "LOSS"

                if trade_closed:
                    results.append({
                        "time": candle_time,
                        "close": close_price,
                        "action": f"CLOSE_{active_trade['side']} ({trade_closed})",
                        "buy_prob": None, "sell_prob": None, "hold_prob": None,
                        "mse": None,
                        "pnl": pnl,
                        "trade_result": trade_closed,
                    })
                    active_trade = None
                    continue

            # Chạy pipeline AI
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

            row = {
                "time": candle_time,
                "close": close_price,
                "action": action,
                "buy_prob": probs.get("buy", 0),
                "sell_prob": probs.get("sell", 0),
                "hold_prob": probs.get("hold", 0),
                "mse": mse,
                "pnl": 0.0,
                "trade_result": "",
            }

            # Thực thi tín hiệu (chỉ khi IDLE)
            if action in ("BUY", "SELL") and active_trade is None:
                tp_price = close_price * (1 + self.tp_pct) if action == "BUY" else close_price * (1 - self.tp_pct)
                sl_price = close_price * (1 - self.sl_pct) if action == "BUY" else close_price * (1 + self.sl_pct)
                active_trade = {
                    "side": action,
                    "entry_price": close_price,
                    "tp": tp_price,
                    "sl": sl_price,
                    "entry_time": candle_time,
                }
                row["action"] = f"{action} (OPEN)"
                self.log(f"🔔 [{candle_time.strftime('%H:%M')}] {action} @ {close_price:.4f} | TP={tp_price:.4f} SL={sl_price:.4f}")

            results.append(row)

        # Tổng kết
        result_df = pd.DataFrame(results)
        self._print_summary(result_df, date_str, session)
        return result_df

    def _print_summary(self, result_df: pd.DataFrame, date_str: str, session: str):
        """In bảng tổng kết kết quả."""
        if result_df.empty:
            self.log("Không có kết quả nào để tổng kết.")
            return

        signals = result_df[result_df["action"].isin(["BUY (OPEN)", "SELL (OPEN)"])]
        closed  = result_df[result_df["trade_result"].isin(["WIN", "LOSS"])]

        n_buy  = len(signals[signals["action"] == "BUY (OPEN)"])
        n_sell = len(signals[signals["action"] == "SELL (OPEN)"])
        n_win  = len(closed[closed["trade_result"] == "WIN"])
        n_loss = len(closed[closed["trade_result"] == "LOSS"])
        total_signals = n_buy + n_sell
        total_closed  = n_win + n_loss
        win_rate = n_win / total_closed * 100 if total_closed > 0 else 0
        total_pnl = closed["pnl"].sum() if not closed.empty else 0

        self.log("")
        self.log("╔══════════════════════════════════════╗")
        self.log(f"║  KẾT QUẢ SIMULATOR: {session.upper()} {date_str}   ")
        self.log("╠══════════════════════════════════════╣")
        self.log(f"║  Tổng tín hiệu BUY : {n_buy:>4}")
        self.log(f"║  Tổng tín hiệu SELL: {n_sell:>4}")
        self.log(f"║  Đã đóng lệnh      : {total_closed:>4} ({n_win}W / {n_loss}L)")
        self.log(f"║  Win Rate          : {win_rate:>6.1f}%")
        self.log(f"║  P&L tổng (pct)    : {total_pnl:>+.4f}")
        self.log("╚══════════════════════════════════════╝")
