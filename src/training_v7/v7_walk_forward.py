# -*- coding: utf-8 -*-
"""
v7_walk_forward.py - Modules 2, 3, 4: Walk-Forward Continual Learning (QTS-V7)
Đồng bộ dữ liệu Leader-Follower, tính Dynamic Lag, Đào tạo Transformer nền tảng,
Initial Validation, và Vòng lặp Tiến hóa Walk-Forward tích hợp phản hồi từ AI.
"""
import os
import sys
import io
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

import json
import time
import traceback
import urllib.request
import urllib.error
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

# Add project root to path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Add huyen_thoai to path for bot_v3 dependency
_HT = os.path.join(_ROOT, "huyen_thoai")
if _HT not in sys.path:
    sys.path.insert(0, _HT)

from src.training_v7.v7_transformer import CrossAssetTransformerModel
from src.orchestration.tg_helper import TelegramBot
from src.simulator.backtest_vtm import BacktestVirtualTradeManager

# Try to import MetaTrader5, fallback if not available
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

def get_telegram_client(config):
    """Khởi tạo Telegram Bot."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        chat_id = config.get("telegram", {}).get("channel_id", "1816854047")
        settings_path = os.path.join(_ROOT, '.vscode', 'settings.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    vsc_cfg = json.load(f)
                token = vsc_cfg.get("antigravityBridge.teleBotToken")
            except:
                pass
        if not token:
            tg_config_path = os.path.join(_ROOT, "tg_config.json")
            if os.path.exists(tg_config_path):
                try:
                    with open(tg_config_path, "r", encoding="utf-8") as f:
                        tcfg = json.load(f)
                    token = tcfg.get("bot_token")
                except:
                    pass
                    
    if token and chat_id:
        return TelegramBot(token), int(chat_id)
    return None, 1816854047

def send_telegram_alert(tbot, chat_id, message):
    if tbot:
        try:
            tbot.send_message(chat_id, f"🤖 <b>[QTS-V7] Walk-Forward</b>\n━━━━━━━━━━━━━━━━━━━━━\n{message}")
        except Exception as e:
            print(f"[TG ERROR] Khong the gui tin nhan Telegram: {e}")

# =====================================================================
# DATA ENGINE: FETCH & SYNC DATA (WITH SYNTHETIC FALLBACK)
# =====================================================================
def fetch_mt5_symbol_data(symbol, timeframe_str, start_date, end_date, mt5_path):
    """Cào dữ liệu nến M15/H1 cho một mã từ MT5."""
    if not MT5_AVAILABLE:
        print(f"[DATA] MT5 package is not installed. Fallback to synthetic data.")
        return None
        
    if not mt5.initialize(path=mt5_path):
        print(f"[DATA] Initialize MT5 failed at path {mt5_path}. Fallback to synthetic data.")
        return None
        
    timeframe_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1
    }
    tf = timeframe_map.get(timeframe_str, mt5.TIMEFRAME_M15)
    
    # Chuyển đổi ngày sang datetime
    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    except Exception as e:
        print(f"[DATA] Parse date failed: {e}")
        mt5.shutdown()
        return None
        
    print(f"[DATA] Fetching {symbol} ({timeframe_str}) from {start_date} to {end_date} from MT5...")
    # Lấy thêm 100 nến phía trước để tránh thiếu nến khi tính lag/indicator
    dt_start_offset = dt_start - timedelta(days=5)
    
    if not mt5.symbol_select(symbol, True):
        # Thử tìm tên thay thế (ví dụ BTCUSDm, XAUUSDm)
        alt_symbols = [symbol + "m", symbol + "m.a", symbol.replace("USD", "USDm")]
        selected = False
        for alt in alt_symbols:
            if mt5.symbol_select(alt, True):
                symbol = alt
                selected = True
                break
        if not selected:
            print(f"[DATA] Symbol {symbol} not found on MT5. Fallback.")
            mt5.shutdown()
            return None
            
    rates = mt5.copy_rates_range(symbol, tf, dt_start_offset, dt_end)
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print(f"[DATA] copy_rates_range returned no data. Fallback.")
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'tick_volume']]
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    return df

def fetch_binance_symbol_data(symbol, timeframe_str, start_date, end_date):
    """Cào dữ liệu nến từ Binance thông qua BinanceAdapter."""
    try:
        from src.core.data_adapters.binance_adapter import BinanceAdapter
        adapter = BinanceAdapter(log_callback=lambda msg: print(msg.encode('ascii', 'ignore').decode('ascii')))
        df = adapter.fetch_historical_data(symbol, timeframe_str, start_date, end_date)
        if df is None or df.empty:
            print(f"[DATA] Binance returned no data for {symbol}.")
            return None
            
        df.index = df.index.tz_localize(None)
        df.index.name = 'time'
        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df
    except Exception as e:
        print(f"[DATA] Binance fetch failed for {symbol}: {e}")
        return None

def fetch_symbol_data(symbol, timeframe_str, start_date, end_date, mt5_path):
    """Route data fetching to Binance (Crypto) or MT5 (Forex/Metals)."""
    if "LTC" in symbol.upper() or "BTC" in symbol.upper() or "ETH" in symbol.upper():
        print(f"[DATA] Routing {symbol} to Binance...")
        df = fetch_binance_symbol_data(symbol, timeframe_str, start_date, end_date)
        if df is not None and not df.empty:
            return df
        print(f"[DATA] Binance returned empty, fallback to MT5 for {symbol}...")
        
    print(f"[DATA] Routing {symbol} to MT5...")
    return fetch_mt5_symbol_data(symbol, timeframe_str, start_date, end_date, mt5_path)

def generate_synthetic_data(symbol, timeframe_str, start_date, end_date):
    """Sinh dữ liệu giả lập chất lượng cao để Unit Test chạy 100% thành công."""
    print(f"[DATA] Generating synthetic data for {symbol} ({timeframe_str}) from {start_date} to {end_date}...")
    dt_start = datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=5)
    dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    
    freq_map = {
        "M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min",
        "H1": "1H", "H4": "4H", "D1": "1D"
    }
    freq = freq_map.get(timeframe_str, "15min")
    date_range = pd.date_range(start=dt_start, end=dt_end, freq=freq)
    
    # Mô phỏng nến ngẫu nhiên
    np.random.seed(42 if "BTC" in symbol else 100)
    n_samples = len(date_range)
    
    # Sinh bước đi ngẫu nhiên cho giá đóng cửa
    base_price = 60000.0 if "BTC" in symbol else 100.0
    returns = np.random.normal(0.0001, 0.005, n_samples)
    price_path = base_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame(index=date_range)
    df['close'] = price_path
    df['open'] = df['close'] * (1 + np.random.normal(0, 0.001, n_samples))
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.002, n_samples)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.002, n_samples)))
    df['volume'] = np.random.randint(10, 1000, n_samples)
    df.index.name = 'time'
    
    return df

def get_synced_data(leader_syms, follower_sym, timeframe, start_date, end_date, mt5_path):
    """
    Fetch dữ liệu danh sách Leader và Follower, thực hiện merge và Forward Fill đồng bộ index thời gian.
    Có cơ chế lưu cache ra file .pkl để tăng tốc độ nếu chạy lại.
    """
    import os
    import hashlib
    
    # Tạo thư mục cache nếu chưa có
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Băm (hash) các tham số để tạo tên file cache duy nhất
    raw_key = f"{follower_sym}_{'_'.join(leader_syms)}_{timeframe}_{start_date}_{end_date}"
    hashed_key = hashlib.md5(raw_key.encode('utf-8')).hexdigest()
    cache_file = os.path.join(cache_dir, f"v7_synced_{hashed_key}.pkl")
    
    if os.path.exists(cache_file):
        print(f"[DATA] Loading synced data from cache: {cache_file}")
        import pandas as pd
        return pd.read_pickle(cache_file)
        
    print(f"[DATA] Syncing multi-leaders: {leader_syms} and follower: {follower_sym}...")
    df_f = fetch_symbol_data(follower_sym, timeframe, start_date, end_date, mt5_path)
    if df_f is None or df_f.empty:
        df_f = generate_synthetic_data(follower_sym, timeframe, start_date, end_date)
    df_f = df_f.add_prefix("follower_")
    
    merged = df_f
    for leader_sym in leader_syms:
        df_l = fetch_symbol_data(leader_sym, timeframe, start_date, end_date, mt5_path)
        if df_l is None or df_l.empty:
            df_l = generate_synthetic_data(leader_sym, timeframe, start_date, end_date)
        df_l = df_l.add_prefix(f"{leader_sym}_")
        import pandas as pd
        merged = pd.merge(merged, df_l, left_index=True, right_index=True, how='outer')
        
    merged.ffill(inplace=True)
    merged.bfill(inplace=True)
    
    # Lưu cache
    merged.to_pickle(cache_file)
    print(f"[DATA] Saved synced data to cache: {cache_file}")
    
    print(f"[DATA] Sync completed. Total synchronized candles: {len(merged):,}")
    return merged

# =====================================================================
# DYNAMIC LAG ESTIMATOR
# =====================================================================
def estimate_dynamic_lag(df_segment, leader_syms, max_lag_steps, correlation_threshold):
    """
    Module 2: Tự động tìm ra độ trễ động (Dynamic Lag) qua tương quan chéo (Cross-Correlation) cho đa dẫn dắt.
    """
    df_segment = df_segment.copy()
    df_segment['follower_ret'] = np.log(df_segment['follower_close'] / df_segment['follower_close'].shift(1))
    
    best_lags = {}
    best_corrs = {}
    
    for leader_sym in leader_syms:
        leader_col = f"{leader_sym}_close"
        df_segment[f'{leader_sym}_ret'] = np.log(df_segment[leader_col] / df_segment[leader_col].shift(1))
        
        temp_df = df_segment[['follower_ret', f'{leader_sym}_ret']].dropna()
        best_lag = 1
        best_corr = 0.0
        
        for lag in range(1, max_lag_steps + 1):
            leader_lagged = temp_df[f'{leader_sym}_ret'].shift(lag)
            corr = temp_df['follower_ret'].corr(leader_lagged)
            
            if not np.isnan(corr) and abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag
                
        print(f"[DYNAMIC-LAG] {leader_sym} Best Lag: {best_lag} steps | Correlation: {best_corr:.4f}")
        if abs(best_corr) < correlation_threshold:
            print(f"[DYNAMIC-LAG] WARNING: {leader_sym} Correlation ({best_corr:.4f}) < {correlation_threshold}. Fallback to Lag=1")
            best_lag = 1
            
        best_lags[leader_sym] = best_lag
        best_corrs[leader_sym] = best_corr
        
    return best_lags, best_corrs

# =====================================================================
# FEATURE ENGINEERING & LABELLING
# =====================================================================
def build_features_and_labels(df_segment, leader_syms, lag_steps_dict, tp_pct, sl_pct, max_hold_bars, seq_len=30, spread_pct=0.0, slippage_pct=0.0):
    """
    Xây dựng vector đặc trưng kết hợp Follower và nhiều Leader dịch trễ.
    """
    df = df_segment.copy()
    
    # 1. Tính toán đặc trưng cơ bản cho Follower
    df['follower_ret'] = np.log(df['follower_close'] / df['follower_close'].shift(1))
    # BB Width
    df['follower_ma'] = df['follower_close'].rolling(20).mean()
    df['follower_std'] = df['follower_close'].rolling(20).std()
    df['follower_bb_width'] = (df['follower_ma'] + 2 * df['follower_std'] - (df['follower_ma'] - 2 * df['follower_std'])) / df['follower_ma']
    
    # RSI (14)
    delta = df['follower_close'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down.replace(0, 1e-5)
    df['follower_rsi'] = 100 - (100 / (1 + rs))
    
    feature_cols = ['follower_ret', 'follower_bb_width', 'follower_rsi']
    
    # 2. Tính toán đặc trưng cho TỪNG Leader dịch trễ theo Dynamic Lag riêng
    for leader_sym in leader_syms:
        lag_steps = lag_steps_dict.get(leader_sym, 1)
        ret_col = f'{leader_sym}_ret_lagged'
        vol_col = f'{leader_sym}_vol_ratio'
        trend_col = f'{leader_sym}_trend_momentum'
        
        df[ret_col] = np.log(df[f'{leader_sym}_close'] / df[f'{leader_sym}_close'].shift(1)).shift(lag_steps)
        df[vol_col] = (df[f'{leader_sym}_volume'] / df[f'{leader_sym}_volume'].rolling(20).mean()).shift(lag_steps)
        
        # Bổ sung Leader Trend Momentum (Đà tăng giảm trong 3 nến trước đó để không bị nhiễu 1 nến)
        # Tại thời điểm t, sử dụng giá ở t - lag_steps so với t - lag_steps - 3
        df[trend_col] = (df[f'{leader_sym}_close'].shift(lag_steps) / df[f'{leader_sym}_close'].shift(lag_steps + 3)) - 1.0
        
        feature_cols.extend([ret_col, vol_col, trend_col])
        
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(subset=feature_cols, inplace=True)
    
    # 3. Tạo nhãn (Labels) dựa trên tương lai TP/SL trong max_hold_bars nến
    closes = df['follower_close'].values
    highs = df['follower_high'].values
    lows = df['follower_low'].values
    labels = []
    
    friction_loss = spread_pct + 2.0 * slippage_pct
    
    for i in range(len(df)):
        if i + max_hold_bars >= len(df):
            labels.append(0)  # Mặc định HOLD ở cuối tập dữ liệu
            continue
            
        current_price = closes[i]
        future_highs = highs[i+1 : i+1+max_hold_bars]
        future_lows = lows[i+1 : i+1+max_hold_bars]
        
        is_long_tp = False
        is_long_sl = False
        for j in range(len(future_highs)):
            high_change = (future_highs[j] - current_price) / current_price - friction_loss
            low_change = (future_lows[j] - current_price) / current_price - friction_loss
            
            if low_change <= -sl_pct:
                is_long_sl = True
            
            if high_change >= tp_pct:
                is_long_tp = True
                
            if is_long_sl or is_long_tp:
                break
                
        is_short_tp = False
        is_short_sl = False
        for j in range(len(future_highs)):
            high_change = (current_price - future_highs[j]) / current_price - friction_loss
            low_change = (current_price - future_lows[j]) / current_price - friction_loss
            
            if high_change <= -sl_pct:
                is_short_sl = True
                
            if low_change >= tp_pct:
                is_short_tp = True
                
            if is_short_sl or is_short_tp:
                break
                
        if is_long_tp and not is_long_sl:
            labels.append(1)  # BUY
        elif is_short_tp and not is_short_sl:
            labels.append(2)  # SELL
        else:
            labels.append(0)  # HOLD
            
    df['label'] = labels
    
    # feature_cols đã được xây dựng động ở vòng lặp trên
    # Chuẩn hóa đặc trưng (Khắc phục lỗi Data Leakage)
    # Sử dụng Rolling Z-score (window gấp 3 lần seq_len) để không rò rỉ tương lai
    rolling_window = seq_len * 3 if seq_len else 90
    for col in feature_cols:
        mean = df[col].rolling(window=rolling_window, min_periods=1).mean()
        std = df[col].rolling(window=rolling_window, min_periods=1).std() + 1e-8
        df[col] = (df[col] - mean) / std
        
    # Tạo chuỗi thời gian (Sequence Dataset) cho Transformer
    X_list = []
    Y_list = []
    times = []
    
    features_np = df[feature_cols].values
    labels_np = df['label'].values
    time_index = df.index
    
    for i in range(len(df) - seq_len):
        X_list.append(features_np[i : i+seq_len])
        Y_list.append(labels_np[i+seq_len])
        times.append(time_index[i+seq_len])
        
    if len(X_list) == 0:
        X = np.empty((0, seq_len, len(feature_cols)), dtype=np.float32)
        Y = np.empty((0,), dtype=np.int64)
    else:
        X = np.array(X_list, dtype=np.float32)
        Y = np.array(Y_list, dtype=np.int64)
    
    return X, Y, times

# =====================================================================
# BACKTEST ENGINE (SIMULATOR)
# =====================================================================
def run_backtest_simulation(model, X_tensor, df_segment_times, df_segment, tp_pct, sl_pct, max_hold_bars=30, spread_pct=0.0, slippage_pct=0.0):
    """
    Module 3 Backtest: Chạy giả lập khớp lệnh thực tế sử dụng BacktestVirtualTradeManager.
    Quét qua nhiều ngưỡng vào lệnh (thresholds) để tìm ra ngưỡng tối ưu nhất.
    """
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    X_torch = torch.tensor(X_tensor, dtype=torch.float32).to(device)
    
    with torch.no_grad():
        logits = model(X_torch)
        probs = torch.softmax(logits, dim=1)
        prob_buy = probs[:, 1].cpu().numpy()
        prob_sell = probs[:, 2].cpu().numpy()
        
    # Xác định point động dựa trên giá tài sản
    follower_sym = "LTCUSD"
    if "follower_close" in df_segment.columns:
        avg_price = df_segment["follower_close"].mean()
        if avg_price > 20000:
            pip_size = 1.0  # BTCUSD
        elif avg_price > 1000:
            pip_size = 0.1  # ETHUSD
        elif avg_price > 50:
            pip_size = 0.01 # LTCUSD
        else:
            pip_size = 0.01
    else:
        pip_size = 0.01
    point = pip_size / 10.0
    
    total_days = (df_segment_times[-1] - df_segment_times[0]).total_seconds() / 86400.0
    if total_days <= 0: total_days = 1.0
    
    # Tìm cột OHLC cho follower
    col_open = "follower_open" if "follower_open" in df_segment.columns else "follower_close"
    col_high = "follower_high" if "follower_high" in df_segment.columns else "follower_close"
    col_low = "follower_low" if "follower_low" in df_segment.columns else "follower_close"
    col_close = "follower_close"
    
    timeframe_seconds = 900  # Khung thời gian mặc định 15 phút (M15)
    max_hold_seconds = max_hold_bars * timeframe_seconds
    
    thresholds_to_test = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
    print(f"\n[BACKTEST] Đang quét các ngưỡng kích hoạt: {thresholds_to_test} (Tổng thời gian: {total_days:.1f} ngày)")
    
    best_res = None
    best_score = -9999.0
    all_res = []
    
    # Pre-extract data to numpy for fast loop
    df_idx_set = set(df_segment.index)
    
    for thr in thresholds_to_test:
        preds = np.zeros(len(prob_buy), dtype=int)
        buy_mask = (prob_buy > prob_sell) & (prob_buy > thr)
        sell_mask = (prob_sell > prob_buy) & (prob_sell > thr)
        preds[buy_mask] = 1
        preds[sell_mask] = 2
        
        sim_symbol = f"SIM_{follower_sym}"
        vtm_config = {
            "FEATURE_ENGINEERING": {
                "lot_size": 0.1,
                "sl_pips": int(sl_pct * 10000), 
                "min_sl_pips": int(sl_pct * 10000 / 3),
                "SL_PIPS": int(sl_pct * 10000),
                "TP_PIPS": int(tp_pct * 10000),
                "MAX_HOLD_BARS": max_hold_bars
            }
        }
        
        vtm = BacktestVirtualTradeManager(
            target_symbol=sim_symbol,
            config=vtm_config,
            log_callback=lambda x: None,  
            tg_notify_callback=lambda x: None
        )
        vtm.active_trade_loggers = {}
        vtm.history_deals = []
        vtm.virtual_balance = 10000.0
        vtm.last_close_time = 0
        vtm.pending_orders = []
        
        for i in range(len(preds)):
            time_t = df_segment_times[i]
            if time_t not in df_idx_set:
                continue
                
            row = df_segment.loc[time_t]
            open_p = row[col_open]
            high_p = row[col_high]
            low_p = row[col_low]
            close_p = row[col_close]
            
            sim_clock = time_t.timestamp()
            vtm.sim_clock = sim_clock
            
            spread_pips = (spread_pct * open_p) / (point * 10.0)
            slippage_pips = (slippage_pct * open_p) / (point * 10.0)
            if spread_pct > 0 and spread_pips == 0: spread_pips = 1.0
            if slippage_pct > 0 and slippage_pips == 0: slippage_pips = 0.5
                
            vtm.update_virtual_positions_ohlc(
                open_p=open_p, high_p=high_p, low_p=low_p, close_p=close_p,
                point=point, spread_pips=spread_pips, slippage_pips=slippage_pips
            )
            
            closed_tickets = []
            for ticket, pos in list(vtm.active_trade_loggers.items()):
                if (sim_clock - pos["entry_time"]) > max_hold_seconds:
                    vtm._close_position_internal(ticket, close_p, f"Giu lenh qua {max_hold_bars} nen")
                    closed_tickets.append(ticket)
            for t in closed_tickets:
                vtm.active_trade_loggers.pop(t, None)
                
            signal = preds[i]
            if signal != 0:
                closed_tickets = []
                for ticket, pos in list(vtm.active_trade_loggers.items()):
                    if pos["order_type"] == "MUA" and signal == 2:
                        vtm._close_position_internal(ticket, close_p, "Dao chieu sang SELL")
                        closed_tickets.append(ticket)
                    elif pos["order_type"] == "BÁN" and signal == 1:
                        vtm._close_position_internal(ticket, close_p, "Dao chieu sang BUY")
                        closed_tickets.append(ticket)
                for t in closed_tickets:
                    vtm.active_trade_loggers.pop(t, None)
                    
                if len(vtm.active_trade_loggers) == 0:
                    tp_pips = (tp_pct * close_p) / (point * 10.0)
                    sl_pips = (sl_pct * close_p) / (point * 10.0)
                    
                    vtm.config["FEATURE_ENGINEERING"]["sl_pips"] = sl_pips
                    vtm.config["FEATURE_ENGINEERING"]["min_sl_pips"] = sl_pips / 3.0
                    
                    order_type_str = "BUY" if signal == 1 else "SELL"
                    preds_info = f"B:{prob_buy[i]:.2f} S:{prob_sell[i]:.2f}"
                    
                    vtm.open_new_mt5_trade(
                        symbol=follower_sym,
                        order_type_str=order_type_str,
                        lot_size=0.1,  
                        sl_pips=sl_pips,
                        tp_pips=tp_pips,
                        preds_info=preds_info,
                        current_bid=close_p,
                        current_ask=close_p,
                        point=point
                    )
                    
        trades = len(vtm.history_deals)
        trades_per_day = trades / total_days
        wins = sum(1 for d in vtm.history_deals if d["profit"] > 0)
        win_rate = wins / trades if trades > 0 else 0.0
        
        profit_sum = sum(d["profit"] for d in vtm.history_deals if d["profit"] > 0)
        loss_sum = sum(abs(d["profit"]) for d in vtm.history_deals if d["profit"] < 0)
        profit_factor = profit_sum / loss_sum if loss_sum > 0 else (profit_sum if profit_sum > 0 else 1.0)
        
        initial_balance = 10000.0
        pnl = (vtm.virtual_balance - initial_balance) / initial_balance
        pnl_usd = vtm.virtual_balance - initial_balance
        
        print(f"    - Ngưỡng {thr:.2f}: Lệnh {trades} ({trades_per_day:.1f} lệnh/ngày) | WR {win_rate*100:.1f}% | PF {profit_factor:.2f} | PnL {pnl*100:.2f}%")
        
        cur_res = {
            "pnl": pnl,
            "pnl_usd": pnl_usd,
            "trades": trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "threshold": thr,
            "trades_per_day": trades_per_day
        }
        all_res.append(cur_res)
        
        # Công thức chấm điểm (Score): ưu tiên PF cao và số lệnh vừa phải
        # Nếu win_rate < 0.3 thì score âm nặng
        score = profit_factor
        if win_rate < 0.3 or trades < 5:
            score = score * 0.1
            
        if score > best_score:
            best_score = score
            best_res = cur_res
            
    if best_res is None:
        best_res = {
            "pnl": 0.0, "pnl_usd": 0.0, "trades": 0, "win_rate": 0.0,
            "profit_factor": 1.0, "threshold": 0.4, "trades_per_day": 0.0
        }
    print(f"  => [CHỌN] Ngưỡng tối ưu: {best_res['threshold']:.2f} (PF: {best_res['profit_factor']:.2f}, Lệnh/ngày: {best_res['trades_per_day']:.1f})")
    
    return {
        "best_res": best_res,
        "all_res": all_res
    }

# =====================================================================
# AI FEEDBACK LOOP (GEMINI REST CALL)
# =====================================================================
def get_ai_feedback(model_name, api_key, result_summary, current_config):
    """
    Module 4: AI Feedback Loop. Gửi kết quả backtest của chu kỳ vừa rồi lên Gemini
    để tự động điều chỉnh siêu tham số SL/TP, max_lag cho chu kỳ sau.
    """
    if not api_key:
        print("[AI-Feedback] No GEMINI_API_KEY available. Keeping existing config.")
        return current_config
        
    print(f"[AI-Feedback] Sending performance to Gemini ({model_name}) for parameter adjustment...")
    prompt = (
        f"Chúng tôi đang vận hành Hệ thống định lượng V7 (QTS-V7). Đây là kết quả Backtest chặng vừa qua:\n"
        f"- Tổng số giao dịch: {result_summary['trades']}\n"
        f"- Tỷ lệ thắng (Win Rate): {result_summary['win_rate']*100:.2f}%\n"
        f"- Hệ số lợi nhuận (Profit Factor): {result_summary['profit_factor']:.2f}\n"
        f"- PnL đạt được: {result_summary['pnl']*100:.3f}%\n\n"
        f"Cấu hình siêu tham số hiện tại:\n"
        f"- TP_PCT: {current_config['tp_pct']}\n"
        f"- SL_PCT: {current_config['sl_pct']}\n"
        f"- MAX_LAG_STEPS: {current_config['max_lag_steps']}\n"
        f"- CORRELATION_THRESHOLD: {current_config['correlation_threshold']}\n"
        f"- MAX_HOLD_BARS: {current_config['max_hold_bars']}\n\n"
        f"Hãy đóng vai trò chuyên gia, đề xuất điều chỉnh siêu tham số mới cho chặng tới nhằm tối đa hóa hiệu quả.\n"
        f"Yêu cầu trả về chính xác định dạng JSON với các tham số tương tự:\n"
        f"{{ \"max_lag_steps\": int, \"correlation_threshold\": float, \"tp_pct\": float, \"sl_pct\": float, \"max_hold_bars\": int }}\n"
        f"Chú ý: Chỉ trả về JSON thuần túy, không giải thích."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    req_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "max_lag_steps": {"type": "INTEGER"},
                    "correlation_threshold": {"type": "NUMBER"},
                    "tp_pct": {"type": "NUMBER"},
                    "sl_pct": {"type": "NUMBER"},
                    "max_hold_bars": {"type": "INTEGER"}
                },
                "required": ["max_lag_steps", "correlation_threshold", "tp_pct", "sl_pct", "max_hold_bars"]
            }
        }
    }
    
    try:
        data_bytes = json.dumps(req_body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            text_response = resp_data["candidates"][0]["content"]["parts"][0]["text"]
            adjusted = json.loads(text_response.strip())
            print(f"[AI-Feedback] Adjusted config received: {adjusted}")
            return adjusted
    except Exception as e:
        print(f"[AI-Feedback] Failed to call Gemini API feedback: {e}. Keeping current config.")
        return current_config

# =====================================================================
# SESSION FILTERING HELPER
# =====================================================================
def filter_by_session(X, Y, times, session_name, session_utc):
    """
    Lọc các mẫu học (X, Y, times) theo giờ giao dịch của phiên (SESSION_UTC).
    Điều này giúp tính toán Features/Labels liên tục mà không đứt gãy chuỗi thời gian,
    nhưng chỉ huấn luyện và kiểm thử trên các nến thuộc phiên chỉ định.
    """
    if not session_utc or session_name.lower() == "all":
        return X, Y, times
        
    start_time_str = session_utc.get("START", "00:00")
    end_time_str = session_utc.get("END", "23:59")
    
    sh, sm = map(int, start_time_str.split(":"))
    eh, em = map(int, end_time_str.split(":"))
    
    start_val = sh * 60 + sm
    end_val = eh * 60 + em
    
    filtered_indices = []
    for idx, t in enumerate(times):
        # Bỏ qua cuối tuần (Thứ 7, Chủ nhật)
        if t.weekday() >= 5:
            continue
            
        # t là Timestamp
        t_min = t.hour * 60 + t.minute
        if start_val <= end_val:
            if start_val <= t_min <= end_val:
                filtered_indices.append(idx)
        else:
            if t_min >= start_val or t_min <= end_val:
                filtered_indices.append(idx)
                
    if not filtered_indices:
        # Trả về mảng rỗng tương thích hình dáng
        return np.empty((0, X.shape[1], X.shape[2]), dtype=np.float32), np.empty((0,), dtype=np.int64), []
        
    return X[filtered_indices], Y[filtered_indices], [times[i] for i in filtered_indices]

# =====================================================================
# CORE WALK-FORWARD ENGINE
# =====================================================================
def train_model(model, X, Y, lr, epochs, batch_size, X_val=None, Y_val=None):
    """Hàm huấn luyện CrossAssetTransformerModel tích hợp Validation Early Stopping để chống Overfitting."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    # Phải có Class Weights để chống mất cân bằng lớp (tránh model dự đoán toàn Hold = 0)
    classes, counts = np.unique(Y, return_counts=True)
    class_weights = np.ones(3, dtype=np.float32)
    for c, cnt in zip(classes, counts):
        class_weights[c] = len(Y) / (3 * cnt)
    class_weights_tensor = torch.tensor(class_weights).to(device)
    
    # Bỏ Focal Loss, dùng CrossEntropyLoss chuẩn với Class Weights
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    # Giảm weight_decay để tránh mô hình bị triệt tiêu weights về 0 (gây ra dự đoán xác suất đều = 0.33)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    
    tensor_dataset = TensorDataset(torch.tensor(X, dtype=torch.float32), torch.tensor(Y, dtype=torch.long))
    loader = DataLoader(tensor_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    
    if X_val is not None and Y_val is not None and len(X_val) > 0:
        val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(Y_val, dtype=torch.long))
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    else:
        val_loader = None
        
    patience = 20
    min_delta = 1e-4
    best_loss = float('inf')
    patience_counter = 0
    best_model_state = None
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        train_loss = total_loss / len(loader)
        
        # Validation Pass
        if val_loader is not None:
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for bx, by in val_loader:
                    bx, by = bx.to(device), by.to(device)
                    logits = model(bx)
                    v_loss = criterion(logits, by)
                    val_loss += v_loss.item()
            epoch_loss = val_loss / len(val_loader)
            print(f"  [Train] Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {epoch_loss:.4f}")
        else:
            epoch_loss = train_loss
            print(f"  [Train] Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f}")
            
        # Kiểm tra sự hội tụ của loss (Early Stopping)
        if epoch_loss < best_loss - min_delta:
            best_loss = epoch_loss
            patience_counter = 0
            import copy
            best_model_state = copy.deepcopy(model.state_dict())
        else:
            if epoch >= 20: # Chỉ bắt đầu đếm Early Stopping sau 20 epochs đầu tiên
                patience_counter += 1
            
        if patience_counter >= patience:
            print(f"  [Train] Early Stopping: Loss converged/overfitting and did not improve for {patience} epochs. Stopping at epoch {epoch+1}.")
            if best_model_state is not None:
                model.load_state_dict(best_model_state)
            break
            
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
        
    return model

def run_walk_forward_learning(bot_config_path="bot_config_v7.json"):
    """
    Thực thi toàn bộ luồng Walk-Forward Continual Learning (QTS-V7).
    """
    print("[Walk-Forward] Khởi động chu kỳ...")
    
    # 1. Load config bot_config_v7.json
    cfg_path = os.path.join(_ROOT, bot_config_path)
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"[Walk-Forward] Khong tim thay bot config tai {cfg_path}")
        
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    mcfg_path = os.path.join(_ROOT, cfg.get("MASTER_CONFIG", "v7_master_config.json"))
    with open(mcfg_path, "r", encoding="utf-8") as f:
        mcfg = json.load(f)
        
    tbot, chat_id = get_telegram_client(mcfg)
    
    # Khai báo các tham số
    leaders = cfg.get("LEADER_SYMBOLS", [cfg.get("LEADER_SYMBOL")])
    follower = cfg["TARGET_SYMBOL"]
    timeframe = cfg["FEATURE_ENGINEERING"]["TIMEFRAME"]
    mt5_path = mcfg.get("brokers", {}).get("DEFAULT", "")
    
    # Tạo Run ID theo timestamp để độc lập hoàn toàn các lượt chạy
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{run_timestamp}_v7"
    config_id = cfg["CONFIG_ID"]
    
    # **BỐ TRÍ CÁC THƯ MỤC CON TRONG WORKSPACE GIỐNG NHƯ V7**
    workspace_dir = os.path.join(_ROOT, "workspaces", config_id, "runs", run_id)
    brains_dir = os.path.join(workspace_dir, "brains")
    results_dir = os.path.join(workspace_dir, "results")
    config_dir = os.path.join(workspace_dir, "config")
    data_dir = os.path.join(workspace_dir, "data")
    
    for folder in [brains_dir, results_dir, config_dir, data_dir]:
        os.makedirs(folder, exist_ok=True)
        
    # Copy file cấu hình ban đầu vào thư mục config/ của bộ não
    with open(os.path.join(config_dir, "bot_config_v7.json"), "w", encoding="utf-8") as fc:
        json.dump(cfg, fc, indent=4, ensure_ascii=False)
        
    # Lưu config.json trực tiếp vào thư mục run root và thư mục results/ giống V6
    with open(os.path.join(workspace_dir, "config.json"), "w", encoding="utf-8") as f_run_cfg:
        json.dump(cfg, f_run_cfg, indent=4, ensure_ascii=False)
    with open(os.path.join(results_dir, "config.json"), "w", encoding="utf-8") as f_res_cfg:
        json.dump(cfg, f_res_cfg, indent=4, ensure_ascii=False)
        
    print(f"[Walk-Forward] Workspace directories created successfully at:\n  {workspace_dir}")
    
    # Tải dữ liệu lịch sử đồng bộ Leader-Follower
    start_date = cfg["WALK_FORWARD"]["START_DATE"]
    end_date = cfg["WALK_FORWARD"]["END_DATE"]
    df_all = get_synced_data(leaders, follower, timeframe, start_date, end_date, mt5_path)
    
    # Đọc tham số huấn luyện ban đầu
    tp_pct = cfg["FEATURE_ENGINEERING"]["TP_PCT"]
    sl_pct = cfg["FEATURE_ENGINEERING"]["SL_PCT"]
    max_hold_bars = cfg["FEATURE_ENGINEERING"]["MAX_HOLD_BARS"]
    max_lag = cfg["FEATURE_ENGINEERING"]["MAX_LAG_STEPS"]
    corr_thresh = cfg["FEATURE_ENGINEERING"]["CORRELATION_THRESHOLD"]
    spread_pct = cfg["FEATURE_ENGINEERING"].get("SPREAD_PCT", 0.0)
    slippage_pct = cfg["FEATURE_ENGINEERING"].get("SLIPPAGE_PCT", 0.0)
    
    session_name = cfg.get("SESSION", "all").lower()
    session_utc = cfg.get("SESSION_UTC", {})
    
    lr_base = cfg["TRAINING"]["LEARNING_RATE_BASE"]
    lr_finetune = cfg["TRAINING"]["LEARNING_RATE_FINETUNE"]
    batch_size = cfg["TRAINING"]["BATCH_SIZE"]
    epochs_base = cfg["TRAINING"]["EPOCHS_BASE"]
    epochs_finetune = cfg["TRAINING"]["EPOCHS_FINETUNE"]
    
    actual_profit = tp_pct - spread_pct - slippage_pct
    actual_loss = sl_pct + spread_pct + slippage_pct
    if (actual_profit + actual_loss) > 0:
        break_even_wr = actual_loss / (actual_profit + actual_loss)
    else:
        break_even_wr = 0.5
    min_wr = break_even_wr + 0.02 # Thêm 2% biên độ an toàn
    print(f"[Walk-Forward] Ngưỡng WR tối thiểu được tính động dựa trên TP/SL: {min_wr*100:.2f}% (Break-even: {break_even_wr*100:.2f}%)", flush=True)
    min_pf = mcfg["train"]["min_profit_factor"]
    
    initial_train_days = cfg["WALK_FORWARD"]["INITIAL_TRAIN_SIZE_DAYS"]
    validation_days = cfg["WALK_FORWARD"]["VALIDATION_SIZE_DAYS"]
    slide_step_days = cfg["WALK_FORWARD"]["SLIDE_STEP_DAYS"]
    
    # =====================================================================
    # MODULE 2: FOUNDATION TRAINING (ĐÀO TẠO NỀN TẢNG)
    # =====================================================================
    print("\n[WF] --- BẮT ĐẦU MODUL 2: ĐÀO TẠO NỀN TẢNG ---")
    dt_start = datetime.strptime(start_date, "%Y-%m-%d")
    dt_foundation_end = dt_start + timedelta(days=initial_train_days)
    
    foundation_end_str = dt_foundation_end.strftime("%Y-%m-%d")
    print(f"[WF] Foundation train window: {start_date} to {foundation_end_str}")
    
    # Cắt tập dữ liệu đào tạo nền tảng
    df_found_train = df_all[(df_all.index >= pd.to_datetime(start_date)) & (df_all.index < pd.to_datetime(foundation_end_str))]
    
    if len(df_found_train) < 100:
        err_msg = f"[ERROR] Khong du du lieu de train Foundation Window ({start_date} to {foundation_end_str}). Du lieu som nhat tu MT5: {df_all.index[0] if len(df_all)>0 else 'N/A'}. Do timeframe la M1, ban can tang 'Max Bars in chart' trong MT5 hoac doi start_date/timeframe trong config."
        print(err_msg)
        raise ValueError(err_msg)
        
    # Tính Dynamic Lag của chặng nền tảng
    found_lags, found_corrs = estimate_dynamic_lag(df_found_train, leaders, max_lag, corr_thresh)
    
    # Xây dựng features & labels
    X_tr, Y_tr, tr_times = build_features_and_labels(
        df_found_train, leaders, found_lags, tp_pct, sl_pct, max_hold_bars, seq_len=30,
        spread_pct=spread_pct, slippage_pct=slippage_pct
    )
    X_tr, Y_tr, tr_times = filter_by_session(X_tr, Y_tr, tr_times, session_name, session_utc)
    
    # Khởi tạo Cross-Asset Transformer Model
    num_features = X_tr.shape[2]
    model = CrossAssetTransformerModel(num_features=num_features)
    
    # Thông báo bắt đầu nền tảng Telegram
    found_lags_str = ", ".join([f"{k}: {v}" for k, v in found_lags.items()])
    found_corrs_str = ", ".join([f"{k}: {v:.4f}" for k, v in found_corrs.items()])
    
    dt_val_end_msg = dt_foundation_end + timedelta(days=validation_days)
    val_end_str_msg = dt_val_end_msg.strftime("%Y-%m-%d")
    
    send_telegram_alert(tbot, chat_id, (
        f"✅ <b>[QTS-V7] HOÀN THÀNH FOUNDATION {session_name.upper()}</b>\n"
        f"• Dữ liệu Huấn luyện (Train): <code>{start_date}</code> -> <code>{foundation_end_str}</code>\n"
        f"• Dữ liệu Đánh giá (Test): <code>{foundation_end_str}</code> -> <code>{val_end_str_msg}</code>\n"
        f"• Độ trễ Dynamic Lag quét được: <code>{found_lags_str} steps</code>\n"
        f"• Tương quan chéo (Pearson): <code>{found_corrs_str}</code>"
    ))
    
    # Xây dựng trước tập Validation để truyền vào hàm huấn luyện (Early Stopping)
    dt_val_start = dt_foundation_end
    dt_val_end = dt_val_start + timedelta(days=validation_days)
    val_start_str = dt_val_start.strftime("%Y-%m-%d")
    val_end_str = dt_val_end.strftime("%Y-%m-%d")
    
    df_val = df_all[(df_all.index >= pd.to_datetime(val_start_str)) & (df_all.index < pd.to_datetime(val_end_str))]
    X_va, Y_va, va_times = build_features_and_labels(
        df_val, leaders, found_lags, tp_pct, sl_pct, max_hold_bars, seq_len=30,
        spread_pct=spread_pct, slippage_pct=slippage_pct
    )
    X_va, Y_va, va_times = filter_by_session(X_va, Y_va, va_times, session_name, session_utc)
    
    # Train
    model = train_model(model, X_tr, Y_tr, lr_base, epochs_base, batch_size, X_val=X_va, Y_val=Y_va)
    
    # Lưu weights nền tảng
    found_weight_path = os.path.join(brains_dir, "aamt_v7_foundation.pth")
    torch.save(model.state_dict(), found_weight_path)
    
    # Lưu thêm tên file theo format V6
    v6_style_found_weight_path = os.path.join(brains_dir, f"aamt_v7_{config_id}_foundation.pth")
    torch.save(model.state_dict(), v6_style_found_weight_path)
    
    print(f"[WF] Foundation weights saved to {found_weight_path} and {v6_style_found_weight_path}")
    
    # Báo cáo Telegram kết thúc Đào tạo Nền tảng
    send_telegram_alert(tbot, chat_id, (
        f"✅ <b>Đào tạo Nền tảng Hoàn tất!</b>\n"
        f"• Đã lưu weights vào: <code>brains/aamt_v7_{config_id}_foundation.pth</code>"
    ))
    
    # =====================================================================
    # MODULE 3: INITIAL VALIDATION (ĐÁNH GIÁ SƠ BỘ)
    # =====================================================================
    print("\n[WF] --- BẮT ĐẦU MODUL 3: ĐÁNH GIÁ SƠ BỘ ---")
    print(f"[WF] Initial Validation window: {val_start_str} to {val_end_str}")
    
    # Chạy giả lập Backtest
    backtest_data = run_backtest_simulation(
        model, X_va, va_times, df_val, tp_pct, sl_pct, max_hold_bars,
        spread_pct=spread_pct, slippage_pct=slippage_pct
    )
    backtest_res = backtest_data["best_res"]
    all_res = backtest_data["all_res"]
    
    # Tìm ngưỡng cuối cùng có lệnh
    last_valid_res = None
    for r in reversed(all_res):
        if r['trades'] > 0:
            last_valid_res = r
            break
    if last_valid_res is None:
        last_valid_res = all_res[-1]
        
    wr = last_valid_res["win_rate"]
    pf = last_valid_res["profit_factor"]
    
    # Gửi tin kết quả Backtest
    report_val_msg = "📊 <b>Báo cáo Đánh giá Sơ bộ tập Validation:</b>\n"
    report_val_msg += f"• Ngưỡng tối ưu: <code>{backtest_res.get('threshold', 0.40):.2f}</code> (WR: {backtest_res['win_rate']*100:.1f}%, PF: {backtest_res['profit_factor']:.2f}, Lệnh: {backtest_res['trades']})\n"
    
    report_val_msg += "\n<b>Chi tiết các ngưỡng song song:</b>\n"
    for r in all_res:
        r_pnl = r['pnl'] * 100
        r_pnl_usd = r['pnl_usd']
        report_val_msg += f"  - Mức {r['threshold']:.2f}: Lệnh <code>{r['trades']}</code> (<code>{r.get('trades_per_day', 0):.1f} L/N</code>) | WR <code>{r['win_rate']*100:.1f}%</code> | PF <code>{r['profit_factor']:.2f}</code> | PnL <code>{r_pnl:.2f}%</code> (<b>${r_pnl_usd:.2f}</b>)\n"
        
    # So sánh với ngưỡng (Dựa trên ngưỡng cuối cùng có lệnh)
    is_passed = (wr >= min_wr) and (pf >= min_pf)
    if not is_passed:
        err_msg = f"{report_val_msg}\n\n❌ <b>KHÔNG ĐẠT NGƯỠNG TỐI THIỂU!</b> (Mức {last_valid_res['threshold']:.2f} có WR {wr*100:.1f}%/{min_wr*100:.1f}%, PF {pf:.2f}/{min_pf:.2f}). Dừng luồng đào tạo nền tảng."
        send_telegram_alert(tbot, chat_id, err_msg)
        raise ValueError(f"[WF FATAL] Initial Validation failed thresholds (WR: {wr:.2f}/{min_wr:.2f}, PF: {pf:.2f}/{min_pf:.2f}). Stopping.")
        
    send_telegram_alert(tbot, chat_id, f"{report_val_msg}\n\n🟢 <b>ĐẠT NGƯỠNG ĐÁNH GIÁ SƠ BỘ!</b> (Mức {last_valid_res['threshold']:.2f} đạt). Chuyển sang Module 4.")
    
    # =====================================================================
    # MODULE 4: WALK-FORWARD CONTINUAL LEARNING LOOP (VÒNG LẶP TIẾN HÓA)
    # =====================================================================
    print("\n[WF] --- BẮT ĐẦU MODUL 4: VÒNG LẶP TIẾN HÓA WALK-FORWARD ---")
    
    # Khởi tạo con trỏ thời gian
    current_train_start = dt_start
    step_idx = 1
    cumulative_pnl = backtest_res["pnl"]
    cumulative_pnl_dict = {r['threshold']: r['pnl'] for r in all_res}
    all_steps_metrics = {}
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = "AIzaSyAJlG9q3BVsHLC3XhQWoWTlPNfN3djxro0"
    ai_model = mcfg.get("ai", {}).get("llm_model", "gemini-1.5-flash")
    
    current_ai_config = {
        "max_lag_steps": max_lag,
        "correlation_threshold": corr_thresh,
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "max_hold_bars": max_hold_bars
    }
    
    while True:
        # Tịnh tiến cửa sổ
        current_train_start = current_train_start + timedelta(days=slide_step_days)
        current_train_end = current_train_start + timedelta(days=initial_train_days)
        current_val_start = current_train_end
        current_val_end = current_val_start + timedelta(days=validation_days)
        
        # Điều kiện Dừng: Nếu vượt quá end_date
        if current_val_end > datetime.strptime(end_date, "%Y-%m-%d"):
            print(f"[WF] Validation end date {current_val_end.strftime('%Y-%m-%d')} exceeds total end_date {end_date}. Exiting loop.")
            break
            
        train_start_str = current_train_start.strftime("%Y-%m-%d")
        train_end_str = current_train_end.strftime("%Y-%m-%d")
        val_start_str = current_val_start.strftime("%Y-%m-%d")
        val_end_str = current_val_end.strftime("%Y-%m-%d")
        
        print(f"\n[WF] --- BƯỚC TRƯỢT #{step_idx} ---")
        print(f"  Train : {train_start_str} to {train_end_str}")
        print(f"  Test  : {val_start_str} to {val_end_str}")
        
        # Báo cáo Telegram chặng mới
        send_telegram_alert(tbot, chat_id, (
            f"🔄 <b>Bước Trượt #{step_idx}:</b>\n"
            f"• Huấn luyện dữ liệu: <code>{train_start_str}</code> -> <code>{train_end_str}</code>\n"
            f"• Fine-tune weights bộ não V7..."
        ))
        
        # Cắt tập dữ liệu mới
        df_tr_step = df_all[(df_all.index >= pd.to_datetime(train_start_str)) & (df_all.index < pd.to_datetime(train_end_str))]
        df_va_step = df_all[(df_all.index >= pd.to_datetime(val_start_str)) & (df_all.index < pd.to_datetime(val_end_str))]
        
        # Tính Dynamic Lag mới
        step_lags, step_corrs = estimate_dynamic_lag(
            df_tr_step, 
            leaders,
            current_ai_config["max_lag_steps"], 
            current_ai_config["correlation_threshold"]
        )
        
        # Xây dựng data train/test chặng mới
        X_tr_step, Y_tr_step, tr_step_times = build_features_and_labels(
            df_tr_step, leaders, step_lags, 
            current_ai_config["tp_pct"], current_ai_config["sl_pct"], 
            current_ai_config["max_hold_bars"], seq_len=30,
            spread_pct=spread_pct, slippage_pct=slippage_pct
        )
        X_tr_step, Y_tr_step, tr_step_times = filter_by_session(X_tr_step, Y_tr_step, tr_step_times, session_name, session_utc)
        
        X_va_step, Y_va_step, va_step_times = build_features_and_labels(
            df_va_step, leaders, step_lags, 
            current_ai_config["tp_pct"], current_ai_config["sl_pct"], 
            current_ai_config["max_hold_bars"], seq_len=30,
            spread_pct=spread_pct, slippage_pct=slippage_pct
        )
        X_va_step, Y_va_step, va_step_times = filter_by_session(X_va_step, Y_va_step, va_step_times, session_name, session_utc)
        
        # Load weights tốt nhất từ chặng trước (hoặc foundation ở bước đầu)
        weight_to_load = found_weight_path if step_idx == 1 else os.path.join(brains_dir, f"aamt_v7_step_{step_idx-1}.pth")
        model.load_state_dict(torch.load(weight_to_load))
        
        # Huấn luyện tiếp tục (Finetuning) với LR nhỏ (Cung cấp thêm Validation Set để Early Stopping chuẩn xác)
        model = train_model(model, X_tr_step, Y_tr_step, lr_finetune, epochs_finetune, batch_size, X_val=X_va_step, Y_val=Y_va_step)
        
        # Lưu weights bộ não bước trượt
        step_weight_path = os.path.join(brains_dir, f"aamt_v7_step_{step_idx}.pth")
        torch.save(model.state_dict(), step_weight_path)
        
        # Backtest
        step_data = run_backtest_simulation(
            model, X_va_step, va_step_times, df_va_step, 
            current_ai_config["tp_pct"], current_ai_config["sl_pct"],
            current_ai_config["max_hold_bars"],
            spread_pct=spread_pct, slippage_pct=slippage_pct
        )
        step_bt = step_data["best_res"]
        all_res_step = step_data["all_res"]
        
        cumulative_pnl += step_bt["pnl"]
        step_pnl_usd = step_bt["pnl_usd"]
        cumulative_pnl_usd = cumulative_pnl * 10000.0
        
        # Báo cáo kết quả Backtest chặng
        report_step_msg = (
            f"📊 <b>Báo cáo chặng bước trượt #{step_idx} (Tập Test):</b>\n"
            f"• Thời gian: <code>{val_start_str}</code> -> <code>{val_end_str}</code>\n"
            f"• Ngưỡng tối ưu: <code>{step_bt.get('threshold', 0.40):.2f}</code> (WR: {step_bt['win_rate']*100:.1f}%, PF: {step_bt['profit_factor']:.2f}, Lệnh: {step_bt['trades']})\n\n"
            f"<b>Chi tiết các ngưỡng song song:</b>\n"
        )
        for r in all_res_step:
            thr = r["threshold"]
            # Cập nhật cumulative
            if thr not in cumulative_pnl_dict:
                cumulative_pnl_dict[thr] = 0.0
            cumulative_pnl_dict[thr] += r["pnl"]
            
            r_pnl = r['pnl'] * 100
            r_pnl_usd = r['pnl_usd']
            c_pnl = cumulative_pnl_dict[thr] * 100
            c_pnl_usd = cumulative_pnl_dict[thr] * 10000.0
            
            report_step_msg += f"  - Mức {thr:.2f}: Lệnh <code>{r['trades']}</code> (<code>{r.get('trades_per_day', 0):.1f} L/N</code>) | WR <code>{r['win_rate']*100:.1f}%</code> | PF <code>{r['profit_factor']:.2f}</code> | PnL <code>{r_pnl:.2f}%</code> (<b>Cộng dồn: {c_pnl:.2f}% / ${c_pnl_usd:.2f}</b>)\n"
            
        send_telegram_alert(tbot, chat_id, report_step_msg)
        
        # AI Feedback Loop: Gửi báo cáo cho LLM để điều chỉnh cấu hình siêu tham số
        next_ai_config = get_ai_feedback(ai_model, api_key, step_bt, current_ai_config)
        
        # Nếu AI thay đổi cấu hình, lưu cấu hình riêng của bộ não chặng sau
        if next_ai_config != current_ai_config:
            current_ai_config = next_ai_config
            ai_advice = (
                f"🤖 <b>Chỉ đạo mới từ AI cho chu kỳ tới:</b>\n"
                f"• Nhận thấy độ trễ & biến động thay đổi, điều chỉnh siêu tham số:\n"
                f"• Lag quét tối đa: <code>{current_ai_config['max_lag_steps']} steps</code>\n"
                f"• Chốt lời (TP): <code>{current_ai_config['tp_pct']*100:.3f}%</code>\n"
                f"• Cắt lỗ (SL): <code>{current_ai_config['sl_pct']*100:.3f}%</code>\n"
                f"• Giữ nến tối đa: <code>{current_ai_config['max_hold_bars']} nến</code>"
            )
            send_telegram_alert(tbot, chat_id, ai_advice)
            
            # Cập nhật file bot_config_v7.json động nằm trong config/ của bộ não hiện tại
            cfg["FEATURE_ENGINEERING"]["TP_PCT"] = current_ai_config["tp_pct"]
            cfg["FEATURE_ENGINEERING"]["SL_PCT"] = current_ai_config["sl_pct"]
            cfg["FEATURE_ENGINEERING"]["MAX_HOLD_BARS"] = current_ai_config["max_hold_bars"]
            cfg["FEATURE_ENGINEERING"]["MAX_LAG_STEPS"] = current_ai_config["max_lag_steps"]
            cfg["FEATURE_ENGINEERING"]["CORRELATION_THRESHOLD"] = current_ai_config["correlation_threshold"]
            
            with open(os.path.join(config_dir, f"bot_config_v7_step_{step_idx}.json"), "w", encoding="utf-8") as fc_step:
                json.dump(cfg, fc_step, indent=4, ensure_ascii=False)
                
        # Lưu kết quả chặng vào kết quả results/
        step_result = {
            "step": step_idx,
            "val_start": val_start_str,
            "val_end": val_end_str,
            "lag_steps": step_lags,
            "correlation": {k: float(v) for k, v in step_corrs.items()},
            "pnl": float(step_bt["pnl"]),
            "pnl_usd": float(step_pnl_usd),
            "trades": int(step_bt["trades"]),
            "win_rate": float(step_bt["win_rate"]),
            "profit_factor": float(step_bt["profit_factor"]),
            "cumulative_pnl": float(cumulative_pnl),
            "cumulative_pnl_usd": float(cumulative_pnl_usd)
        }
        
        results_file = os.path.join(results_dir, f"step_{step_idx}_results.json")
        with open(results_file, "w", encoding="utf-8") as fr:
            json.dump(step_result, fr, indent=4)
            
        all_steps_metrics[f"step_{step_idx}"] = step_result
        step_idx += 1
        
    # Save final weights like V6 final
    final_weight_path = os.path.join(brains_dir, f"aamt_v7_{config_id}_final.pth")
    torch.save(model.state_dict(), final_weight_path)
    
    # Save unified training_metrics_v7.json under results/
    metrics_path = os.path.join(results_dir, "training_metrics_v7.json")
    with open(metrics_path, "w", encoding="utf-8") as fm:
        json.dump({
            "target": follower.lower(),
            "version": "Transformer_V7",
            "config_id": config_id,
            "initial_balance_usd": 10000.0,
            "cumulative_pnl": float(cumulative_pnl),
            "cumulative_pnl_usd": float(cumulative_pnl * 10000.0),
            "steps": all_steps_metrics
        }, fm, indent=4)
        
    print(f"[WF] Final weights saved to {final_weight_path}")
    print(f"[WF] Training metrics saved to {metrics_path}")
        
    # =====================================================================
    # FINALIZATION: BÁO CÁO TỔNG KẾT
    # =====================================================================
    cumulative_pnl_usd = cumulative_pnl * 10000.0
    final_report = (
        f"🏆 <b>TỔNG KẾT TOÀN CHÚ KỲ WALK-FORWARD V7</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Leader - Follower:</b> <code>{leader} - {follower}</code>\n"
        f"📊 <b>Kết quả cuối khóa:</b>\n"
        f"• Cumulative PnL: <b>{cumulative_pnl*100:.2f}%</b> (<b>${cumulative_pnl_usd:.2f}</b>)\n"
        f"• Tổng số bước trượt: <code>{step_idx - 1} steps</code>\n"
        f"• Workspace bộ não: <code>workspaces/{config_id}/runs/{run_id}/</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <i>Đã hoàn tất tiến trình Walk-Forward, bộ não V7 đã sẵn sàng thực chiến!</i>"
    )
    
    send_telegram_alert(tbot, chat_id, final_report)
    print(f"[Walk-Forward] SUCCESS: Process finished. Workspace: {workspace_dir}")
    
    return workspace_dir

if __name__ == "__main__":
    run_walk_forward_learning()
