import os
import sys
import pandas as pd
import numpy as np
import torch
from dataclasses import dataclass, field
from typing import List
from numba import njit

@njit
def fast_simulate_loop(buy_probs, sell_probs, opens, highs, lows, threshold, tp_pct, sl_pct, spread_pct, max_hold_bars):
    n_buy = 0
    n_sell = 0
    n_win = 0
    n_rows = len(buy_probs)
    next_free_bar = 0
    
    for i in range(n_rows - 1):
            
        is_buy = buy_probs[i] > threshold
        is_sell = sell_probs[i] > threshold
        
        if is_buy and not is_sell:
            t_entry = i + 1
            entry_price = opens[t_entry]
            tp_price = entry_price * (1.0 + tp_pct + spread_pct)
            sl_price = entry_price * (1.0 - sl_pct + spread_pct)
            
            limit_idx = t_entry + max_hold_bars
            if limit_idx > n_rows:
                limit_idx = n_rows
                
            trade_result = 0
            trade_closed_at = limit_idx
            
            for j in range(t_entry, limit_idx):
                if highs[j] >= tp_price:
                    trade_result = 1
                    trade_closed_at = j + 1
                    break
                elif lows[j] <= sl_price:
                    trade_result = 0
                    trade_closed_at = j + 1
                    break
                    
            if trade_result == 1:
                n_win += 1
            n_buy += 1
            
        elif is_sell and not is_buy:
            t_entry = i + 1
            entry_price = opens[t_entry]
            tp_price = entry_price * (1.0 - tp_pct - spread_pct)
            sl_price = entry_price * (1.0 + sl_pct - spread_pct)
            
            limit_idx = t_entry + max_hold_bars
            if limit_idx > n_rows:
                limit_idx = n_rows
                
            trade_result = 0
            trade_closed_at = limit_idx
            
            for j in range(t_entry, limit_idx):
                if lows[j] <= tp_price:
                    trade_result = 1
                    trade_closed_at = j + 1
                    break
                elif highs[j] >= sl_price:
                    trade_result = 0
                    trade_closed_at = j + 1
                    break
                    
            if trade_result == 1:
                n_win += 1
            n_sell += 1
            
    return n_buy, n_sell, n_win
    
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if os.path.join(_ROOT, 'huyen_thoai') not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, 'huyen_thoai'))

def load_crypto_parquets(raw_dir: str, target_sym: str, target_prefix: str):
    all_files = [f for f in os.listdir(raw_dir) if f.endswith(".parquet")]
    sym_files = [f for f in all_files if target_prefix.upper() in f.upper()]
    
    dfs = []
    for fname in sorted(sym_files):
        dfs.append(pd.read_parquet(os.path.join(raw_dir, fname)))
        
    df = pd.concat(dfs)
    if "time" in df.columns:
        df.set_index("time", inplace=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
        
    df = df[~df.index.duplicated(keep='first')].sort_index()
    rename_map = {c: f"{target_prefix}_{c}" for c in df.columns}
    df = df.rename(columns=rename_map)
    return df


@dataclass
class ThresholdMetricsV6:
    threshold: float
    total_signals: int
    win_rate: float
    n_buy: int = 0
    n_sell: int = 0
    balanced_score: float = 0.0
    tus_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    expected_value: float = 0.0

    def __str__(self) -> str:
        b_ratio = min(self.n_buy, self.n_sell) / max(1, max(self.n_buy, self.n_sell))
        return (
            f">={self.threshold*100:.0f}%: "
            f"WR={self.win_rate*100:.1f}% | "
            f"Score={self.balanced_score:.3f} | "
            f"N={self.total_signals} ({self.n_buy}B/{self.n_sell}S Bal:{b_ratio:.2f})"
        )

@dataclass
class EpochEvalResultV6:
    threshold_metrics: List[ThresholdMetricsV6] = field(default_factory=list)
    max_threshold: float = 0.53
    best_score: float = 0.0
    val_loss: float = float("inf")
    val_mse: float = float("inf")
    val_ce: float = float("inf")

    def composite_score(self) -> float:
        if len(self.threshold_metrics) < 4:
            if not self.threshold_metrics: return 0.0
            return max(m.balanced_score for m in self.threshold_metrics)
        l3 = self.threshold_metrics[2].balanced_score
        l4 = self.threshold_metrics[3].balanced_score
        return (2.0 * l4 + 1.0 * l3) / 3.0

    def format_summary(self) -> str:
        parts = [str(m) for m in self.threshold_metrics]
        composite = self.composite_score()
        return (
            f"V6 Simulator Score [{composite:.3f}] - Loss(MSE:{self.val_mse:.4f}/CE:{self.val_loss-self.val_mse:.4f})\n"
            + "  " + " | ".join(parts)
        )

class SimulatorEvaluatorV6:
    def __init__(self, raw_dir: str, target_sym: str, config: dict, freq_min_N: int = 15, freq_max_N: int = 1000):
        self.raw_dir = raw_dir
        self.target_sym = target_sym
        self.n_thresholds = 4
        self.freq_min_N = freq_min_N
        self.freq_max_N = freq_max_N
        self.val_days = 1.0

        
        # Load raw prices once
        target_prefix = config.get("TARGET_PREFIX", config.get("FEATURE_ENGINEERING", {}).get("TARGET_PREFIX", ""))
        if not target_prefix:
            target_prefix = target_sym.upper()
        self.target_prefix = target_prefix
        
        unique_symbols = {target_sym: []}
        suffix = config.get("DATA_SOURCE", {}).get("DATASET_SUFFIX", "2026")
        self.df_raw = load_crypto_parquets(raw_dir, target_sym, target_prefix)
        
        # Quant Configs
        fe_cfg = config.get("FEATURE_ENGINEERING", {})
        self.tp_pct = fe_cfg.get("TP_PCT", 0.003)
        self.sl_pct = fe_cfg.get("SL_PCT", 0.003)
        self.spread_pct = fe_cfg.get("SPREAD_PCT", 0.0005)
        self.max_hold_bars = fe_cfg.get("MAX_HOLD_BARS", 96)
        
    def _simulate_threshold(self, df_merged: pd.DataFrame, threshold: float) -> ThresholdMetricsV6:
        buy_probs = df_merged['prob_buy'].values
        sell_probs = df_merged['prob_sell'].values
        opens = df_merged[f'{self.target_prefix}_open'].values
        highs = df_merged[f'{self.target_prefix}_high'].values
        lows = df_merged[f'{self.target_prefix}_low'].values
        
        n_buy, n_sell, n_win = fast_simulate_loop(
            buy_probs, sell_probs, opens, highs, lows, 
            threshold, self.tp_pct, self.sl_pct, self.spread_pct, self.max_hold_bars
        )

        n_signals = n_buy + n_sell
        win_rate = n_win / n_signals if n_signals > 0 else 0.0
        
        gross_profit = n_win * 2.0
        gross_loss = (n_signals - n_win) * 1.0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (99.9 if gross_profit > 0 else 0.0)
        expected_value = (gross_profit - gross_loss) / n_signals if n_signals > 0 else 0.0
        
        tus_score = 1.0 - abs(n_buy - n_sell) / n_signals if n_signals > 0 else 0.0
        risk_factor = tus_score if tus_score > 0 else 0.1
        
        # simple freq factor - BỎ GIỚI HẠN SỐ LỆNH
        freq_factor = 1.0
            
        trades_per_day = n_signals / max(1.0, self.val_days)
            
        score = max(0.0, expected_value * n_signals) * risk_factor * freq_factor * win_rate * trades_per_day
        
        return ThresholdMetricsV6(
            threshold=threshold,
            total_signals=n_signals,
            n_buy=n_buy,
            n_sell=n_sell,
            win_rate=win_rate,
            balanced_score=score,
            tus_score=tus_score,
            profit_factor=profit_factor,
            expected_value=expected_value
        )
        
    def _find_max_threshold(self, df_merged: pd.DataFrame) -> float:
        max_thresh = 0.53
        buy_probs = df_merged['prob_buy'].values
        sell_probs = df_merged['prob_sell'].values
        
        for t_int in range(99, 53, -1):
            t = t_int / 100.0
            is_buy = buy_probs > t
            is_sell = sell_probs > t
            # very rough estimate ignoring lockouts just to scale threshold
            n_sig = np.sum(is_buy & ~is_sell) + np.sum(is_sell & ~is_buy)
            if n_sig >= self.freq_min_N:
                max_thresh = t
                break
        return max_thresh

    def evaluate(self, logits: torch.Tensor, T_val: np.ndarray, val_loss: float, val_mse: float, val_ce: float = float("inf")) -> EpochEvalResultV6:
        probs = torch.softmax(logits, dim=1)
        prob_sell = probs[:, 0].cpu().numpy()
        prob_buy = probs[:, 1].cpu().numpy() # In V6: 0=Sell, 1=Buy, 2=Hold
        
        if T_val is None:
            print("⚠️ CẢNH BÁO: T_val is None! Không thể chạy Simulator. Trả về dummy result.")
            return EpochEvalResultV6(
                val_ce_loss=val_ce,
                win_rate=0.0,
                pnl=0.0,
                max_dd=0.0,
                num_trades=0,
                score=0.0,
                val_mse_loss=val_mse,
                trade_logs=pd.DataFrame()
            )

        # Reconstruct timeseries
        # T_val is array of Unix timestamps in seconds
        val_times = pd.to_datetime(T_val, unit='s', utc=True)
        
        # Determine the boundaries of evaluation
        min_time = val_times.min()
        max_time = val_times.max() + pd.Timedelta(minutes=self.max_hold_bars + 1)
        
        # Subset df_raw
        df_sub = self.df_raw.loc[(self.df_raw.index >= min_time) & (self.df_raw.index <= max_time)].copy()
        
        df_probs = pd.DataFrame({'prob_buy': prob_buy, 'prob_sell': prob_sell}, index=val_times)
        
        # Join (df_sub retains all minute candles, even without signals)
        df_merged = df_sub.join(df_probs, how='left')
        df_merged['prob_buy'] = df_merged['prob_buy'].fillna(0.0)
        df_merged['prob_sell'] = df_merged['prob_sell'].fillna(0.0)
        
        # Dynamic Min_N based on duration
        days = (max_time - min_time).days
        self.freq_min_N = max(15, int(days * 1.5)) # Expecting 1.5 trades per day

        max_thresh = self._find_max_threshold(df_merged)
        
        if max_thresh > 0.54:
            step = (max_thresh - 0.53) / (self.n_thresholds - 1)
            thresholds = [round(0.53 + step * i, 4) for i in range(self.n_thresholds)]
        else:
            thresholds = [0.53, 0.54, 0.55, 0.56]
            max_thresh = 0.56
            
        metrics_list = []
        for t in thresholds:
            m = self._simulate_threshold(df_merged, t)
            metrics_list.append(m)
            
        best_score = max((m.balanced_score for m in metrics_list), default=0.0)
        
        return EpochEvalResultV6(
            threshold_metrics=metrics_list,
            max_threshold=max_thresh,
            best_score=best_score,
            val_loss=val_loss,
            val_mse=val_mse,
            val_ce=val_ce
        )
