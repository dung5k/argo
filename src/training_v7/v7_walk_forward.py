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
import torch.nn.functional as F

class FocalLoss(nn.Module):
    def __init__(self, weight=None, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.weight = weight
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, weight=self.weight, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

class PnLAwareLoss(nn.Module):
    def __init__(self, weight=None, gamma=2.0):
        super(PnLAwareLoss, self).__init__()
        self.focal = FocalLoss(weight=weight, gamma=gamma, reduction='none')

    def forward(self, inputs, targets, sample_weights):
        # Calculate unreduced focal loss
        loss = self.focal(inputs, targets)
        # Apply sample weights (PnL/ATR weights)
        weighted_loss = loss * sample_weights
        return weighted_loss.mean()

# Add project root to path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Add huyen_thoai to path for bot_v3 dependency
_HT = os.path.join(_ROOT, "huyen_thoai")
if _HT not in sys.path:
    sys.path.insert(0, _HT)

from src.training_v7.v7_transformer import CrossAssetTransformerModel, TemporalFusionTransformerModel
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
        cols = ['open', 'high', 'low', 'close', 'volume']
        if 'taker_buy_volume' in df.columns:
            cols.extend(['taker_buy_volume', 'taker_sell_volume'])
        df = df[cols]
        return df
    except Exception as e:
        print(f"[DATA] Binance fetch failed for {symbol}: {e}")
        return None

def fetch_symbol_data(symbol, timeframe_str, start_date, end_date, mt5_path):
    """Route data fetching to Binance (Crypto) or MT5 (Forex/Metals)."""
    is_crypto = ("USD" in symbol.upper() and not any(x in symbol.upper() for x in ["XAU", "XAG", "EUR", "GBP", "JPY"])) or any(c in symbol.upper() for c in ["BTC", "ETH", "LTC", "NEAR", "SOL", "BNB"])
    
    if is_crypto:
        print(f"[DATA] Routing {symbol} to Binance...")
        df = fetch_binance_symbol_data(symbol, timeframe_str, start_date, end_date)
        if df is not None and not df.empty:
            return df
        print(f"[DATA] Binance returned empty for {symbol}. KHÔNG FALLBACK TẠO FAKE DATA!")
        return None
        
    print(f"[DATA] Routing {symbol} to MT5...")
    df = fetch_mt5_symbol_data(symbol, timeframe_str, start_date, end_date, mt5_path)
    if df is not None and not df.empty:
        return df
    print(f"[DATA] MT5 returned empty for {symbol}.")
    return None

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
        print(f"[DATA] LỖI: Dữ liệu Follower ({follower_sym}) rỗng! Không sử dụng data giả lập.")
        return None
    df_f = df_f.add_prefix("follower_")
    
    merged = df_f
    for leader_sym in leader_syms:
        df_l = fetch_symbol_data(leader_sym, timeframe, start_date, end_date, mt5_path)
        if df_l is None or df_l.empty:
            print(f"[DATA] LỖI: Dữ liệu Leader ({leader_sym}) rỗng! Không sử dụng data giả lập.")
            return None
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
# FEATURE ENGINEERING & LABELLING
# =====================================================================
def build_features_and_labels(df_segment, leader_syms, tp_pct, sl_pct, max_hold_bars, seq_len=30, spread_pct=0.0, slippage_pct=0.0, scaler_dict=None, use_dynamic_atr=False, atr_tp_mult=3.0, atr_sl_mult=2.0, min_atr_pct=0.0):
    """
    Xây dựng vector đặc trưng kết hợp Follower và nhiều Leader dịch trễ.
    """
    df = df_segment.copy()
    
    # 1. Tính toán đặc trưng cơ bản cho Follower
    # [M1-OPTIMIZED] Rolling windows scaled x5 cho M1 (100 nến M1 ≈ 20 nến M5)
    roll_slow = 100  # BB, Volume MA
    roll_fast = 70   # RSI, ATR
    mom_shift = 15   # Momentum lookback (15 nến M1 ≈ 3 nến M5)
    
    df['follower_ret'] = np.log(df['follower_close'] / df['follower_close'].shift(1))
    df['follower_open_ret'] = np.log(df['follower_open'] / df['follower_close'].shift(1))
    df['follower_high_ret'] = np.log(df['follower_high'] / df['follower_close'].shift(1))
    df['follower_low_ret'] = np.log(df['follower_low'] / df['follower_close'].shift(1))
    df['follower_vol_ratio'] = df['follower_volume'] / df['follower_volume'].rolling(roll_slow).mean()
    
    # BB Width (scaled)
    df['follower_ma'] = df['follower_close'].rolling(roll_slow).mean()
    df['follower_std'] = df['follower_close'].rolling(roll_slow).std()
    df['follower_bb_width'] = (df['follower_ma'] + 2 * df['follower_std'] - (df['follower_ma'] - 2 * df['follower_std'])) / df['follower_ma']
    
    # RSI (scaled)
    delta = df['follower_close'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(com=roll_fast-1, adjust=False).mean()
    ema_down = down.ewm(com=roll_fast-1, adjust=False).mean()
    rs = ema_up / ema_down.replace(0, 1e-5)
    df['follower_rsi'] = 100 - (100 / (1 + rs))
    
    # ATR (scaled)
    high_low = df['follower_high'] - df['follower_low']
    high_close = np.abs(df['follower_high'] - df['follower_close'].shift(1))
    low_close = np.abs(df['follower_low'] - df['follower_close'].shift(1))
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['follower_atr_pct'] = true_range.rolling(roll_fast).mean() / df['follower_close']
    
    feature_cols = ['follower_ret', 'follower_open_ret', 'follower_high_ret', 'follower_low_ret', 'follower_vol_ratio', 'follower_bb_width', 'follower_rsi', 'follower_atr_pct']
    
    # [NEW] Orderbook Imbalance / CVD if available from Binance
    if 'follower_taker_buy_volume' in df.columns and 'follower_taker_sell_volume' in df.columns:
        df['follower_vol_delta'] = (df['follower_taker_buy_volume'] - df['follower_taker_sell_volume']) / (df['follower_volume'].replace(0, 1e-5))
        df['follower_cvd'] = df['follower_vol_delta'].rolling(roll_slow).sum()
        feature_cols.extend(['follower_vol_delta', 'follower_cvd'])
        
    # 2. Tính toán đặc trưng cho TỪNG Leader
    for leader_sym in leader_syms:
        ret_col = f'{leader_sym}_ret'
        vol_col = f'{leader_sym}_vol_ratio'
        trend_col = f'{leader_sym}_trend_momentum'
        bb_col = f'{leader_sym}_bb_width'
        rsi_col = f'{leader_sym}_rsi'
        
        # Lợi nhuận
        df[ret_col] = np.log(df[f'{leader_sym}_close'] / df[f'{leader_sym}_close'].shift(1))
        
        # Khối lượng (scaled)
        df[vol_col] = df[f'{leader_sym}_volume'] / df[f'{leader_sym}_volume'].rolling(roll_slow).mean()
        # Động lượng Trend (scaled)
        df[trend_col] = (df[f'{leader_sym}_close'] / df[f'{leader_sym}_close'].shift(mom_shift)) - 1.0
        
        # BB Width cho Leader (scaled)
        ma = df[f'{leader_sym}_close'].rolling(roll_slow).mean()
        std = df[f'{leader_sym}_close'].rolling(roll_slow).std()
        df[bb_col] = (ma + 2 * std - (ma - 2 * std)) / ma
        
        # RSI cho Leader (scaled)
        delta_l = df[f'{leader_sym}_close'].diff()
        up_l = delta_l.clip(lower=0)
        down_l = -delta_l.clip(upper=0)
        ema_up_l = up_l.ewm(com=roll_fast-1, adjust=False).mean()
        ema_down_l = down_l.ewm(com=roll_fast-1, adjust=False).mean()
        rs_l = ema_up_l / ema_down_l.replace(0, 1e-5)
        df[rsi_col] = 100 - (100 / (1 + rs_l))
        
        # [NEW] Relative Strength: Follower/Leader ratio (Sức mạnh tương đối)
        rs_ratio_col = f'{leader_sym}_relative_strength'
        df[rs_ratio_col] = np.log(df['follower_close'] / df[f'{leader_sym}_close'])
        df[rs_ratio_col] = df[rs_ratio_col] - df[rs_ratio_col].rolling(roll_slow).mean()  # Detrended
        
        # [NEW] Rolling Correlation: Pearson 30 nến (30 phút trên M1)
        corr_col = f'{leader_sym}_rolling_corr'
        df[corr_col] = df['follower_ret'].rolling(30).corr(df[ret_col])
        
        # [NEW] Market Regime: Leader momentum flag (bull=1, bear=-1, chop=0)
        regime_col = f'{leader_sym}_regime'
        leader_mom = (df[f'{leader_sym}_close'] / df[f'{leader_sym}_close'].shift(mom_shift)) - 1.0
        df[regime_col] = 0.0
        df.loc[leader_mom > 0.001, regime_col] = 1.0   # Bull
        df.loc[leader_mom < -0.001, regime_col] = -1.0  # Bear
        
        feature_cols.extend([ret_col, vol_col, trend_col, bb_col, rsi_col, rs_ratio_col, corr_col, regime_col])
        
        # [NEW] Orderbook Imbalance / CVD if available from Binance
        buy_vol_col = f'{leader_sym}_taker_buy_volume'
        sell_vol_col = f'{leader_sym}_taker_sell_volume'
        if buy_vol_col in df.columns and sell_vol_col in df.columns:
            vd_col = f'{leader_sym}_vol_delta'
            cvd_col = f'{leader_sym}_cvd'
            df[vd_col] = (df[buy_vol_col] - df[sell_vol_col]) / (df[f'{leader_sym}_volume'].replace(0, 1e-5))
            df[cvd_col] = df[vd_col].rolling(roll_slow).sum()
            feature_cols.extend([vd_col, cvd_col])
        
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(subset=feature_cols, inplace=True)
    
    # 3. Tạo nhãn (Labels) dựa trên tương lai TP/SL trong max_hold_bars nến
    closes = df['follower_close'].values
    highs = df['follower_high'].values
    lows = df['follower_low'].values
    labels = []
    
    friction_loss = spread_pct + 2.0 * slippage_pct
    
    if use_dynamic_atr and 'follower_atr_pct' in df.columns:
        atr_pcts = df['follower_atr_pct'].values
    else:
        atr_pcts = None
    
    for i in range(len(df)):
        if i + max_hold_bars >= len(df):
            labels.append(0)  # Mặc định HOLD ở cuối tập dữ liệu
            continue
            
        current_price = closes[i]
        future_highs = highs[i+1 : i+1+max_hold_bars]
        future_lows = lows[i+1 : i+1+max_hold_bars]
        
        # [NEW] Kiểm tra 2 điều kiện filter (Chuyên gia đề xuất)
        # 1. Market Regime (ATR Filter)
        current_atr = atr_pcts[i] if atr_pcts is not None else 0.0
        if current_atr < min_atr_pct:
            labels.append(0) # Volatility quá thấp -> Bắt buộc HOLD
            continue
        
        if atr_pcts is not None:
            current_tp_pct = atr_pcts[i] * atr_tp_mult
            current_sl_pct = atr_pcts[i] * atr_sl_mult
        else:
            current_tp_pct = tp_pct
            current_sl_pct = sl_pct
        
        is_long_tp = False
        is_long_sl = False
        for j in range(len(future_highs)):
            high_change = (future_highs[j] - current_price) / current_price - friction_loss
            low_change = (future_lows[j] - current_price) / current_price - friction_loss
            
            if low_change <= -current_sl_pct:
                is_long_sl = True
            
            if high_change >= current_tp_pct:
                is_long_tp = True
                
            if is_long_sl or is_long_tp:
                break
                
        is_short_tp = False
        is_short_sl = False
        for j in range(len(future_highs)):
            high_change = (current_price - future_highs[j]) / current_price - friction_loss
            low_change = (current_price - future_lows[j]) / current_price - friction_loss
            
            if high_change <= -current_sl_pct:
                is_short_sl = True
                
            if low_change >= current_tp_pct:
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
    
    # [NEW] Calculate PnL Weights for custom loss function
    # Normalize ATR to use as a weight multiplier. Higher ATR -> Higher Weight
    if 'follower_atr_pct' in df.columns:
        atr_series = df['follower_atr_pct'].fillna(0)
        # Avoid division by zero, scale to mean 1.0
        mean_atr = atr_series.mean()
        if mean_atr > 0:
            df['pnl_weight'] = (atr_series / mean_atr).clip(0.1, 5.0) 
        else:
            df['pnl_weight'] = 1.0
    else:
        df['pnl_weight'] = 1.0

    
    # feature_cols đã được xây dựng động ở vòng lặp trên
    # Chuẩn hóa đặc trưng (Khắc phục lỗi Data Leakage)
    # Bỏ Rolling window ngắn. Chuyển sang sử dụng RobustScaler trên toàn bộ cửa sổ Foundation Train
    if scaler_dict is None:
        scaler_dict = {}
        is_train = True
    else:
        is_train = False
        
    for col in feature_cols:
        if is_train:
            median = df[col].median()
            iqr = df[col].quantile(0.75) - df[col].quantile(0.25)
            if iqr == 0:
                iqr = 1e-8
            scaler_dict[col] = {'median': median, 'iqr': iqr}
        else:
            median = scaler_dict.get(col, {}).get('median', 0.0)
            iqr = scaler_dict.get(col, {}).get('iqr', 1e-8)
            
        df[col] = ((df[col] - median) / iqr).fillna(0.0).clip(-10.0, 10.0)
        
    # Tạo chuỗi thời gian (Sequence Dataset) cho Transformer
    X_list = []
    Y_list = []
    W_list = []
    times = []
    
    features_np = df[feature_cols].values
    labels_np = df['label'].values
    weights_np = df['pnl_weight'].values
    time_index = df.index
    
    for i in range(len(df) - seq_len):
        X_list.append(features_np[i : i+seq_len])
        Y_list.append(labels_np[i+seq_len])
        W_list.append(weights_np[i+seq_len])
        times.append(time_index[i+seq_len])
        
    if len(X_list) == 0:
        X = np.empty((0, seq_len, len(feature_cols)), dtype=np.float32)
        Y = np.empty((0,), dtype=np.int64)
        W = np.empty((0,), dtype=np.float32)
    else:
        X = np.array(X_list, dtype=np.float32)
        Y = np.array(Y_list, dtype=np.int64)
        W = np.array(W_list, dtype=np.float32)
    
    return X, Y, W, times, scaler_dict

# =====================================================================
# BACKTEST ENGINE (SIMULATOR)
# =====================================================================
def run_backtest_simulation(model, X_tensor, df_segment_times, df_segment, tp_pct, sl_pct, follower_sym, max_hold_bars=30, spread_pct=0.0, slippage_pct=0.0, min_atr_pct=0.0):
    """
    Module 3 Backtest: Chạy giả lập khớp lệnh thực tế sử dụng BacktestVirtualTradeManager.
    Quét qua nhiều ngưỡng vào lệnh (thresholds) để tìm ra ngưỡng tối ưu nhất.
    """
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    X_torch = torch.tensor(X_tensor, dtype=torch.float32).to(device)
    
    with torch.no_grad():
        logits, _ = model(X_torch)
        probs = torch.softmax(logits, dim=1)
        prob_buy = probs[:, 1].cpu().numpy()
        prob_sell = probs[:, 2].cpu().numpy()
        
    # Tính ATR để đồng bộ với cơ chế Dynamic ATR trong quá trình Train
    if "follower_high" in df_segment.columns and "follower_low" in df_segment.columns and "follower_close" in df_segment.columns:
        high_low = df_segment['follower_high'] - df_segment['follower_low']
        high_close = np.abs(df_segment['follower_high'] - df_segment['follower_close'].shift(1))
        low_close = np.abs(df_segment['follower_low'] - df_segment['follower_close'].shift(1))
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr_pcts_series = true_range.rolling(14).mean() / df_segment['follower_close']
    else:
        atr_pcts_series = None
        
    # Xác định point động dựa trên giá tài sản
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
    
    thresholds_to_test = [0.35, 0.38, 0.40, 0.45, 0.50]
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
        
        last_trade_idx = -9999
        cooldown_bars = 10
        
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
            
            if len(closed_tickets) > 0:
                last_trade_idx = i
                
            signal = preds[i]
            
            # [NEW] Apply Filters to Predictions
            if signal != 0:
                if min_atr_pct > 0 and atr_pcts_series is not None:
                    try:
                        current_atr = atr_pcts_series.loc[time_t]
                        if current_atr < min_atr_pct:
                            signal = 0
                    except:
                        pass
            
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
                    if i - last_trade_idx >= cooldown_bars:
                        last_trade_idx = i
                        
                        current_atr = np.nan
                        if atr_pcts_series is not None:
                            try:
                                current_atr = atr_pcts_series.iloc[i]
                            except:
                                pass
                                
                        if not pd.isna(current_atr):
                            current_tp = current_atr * 3.0
                            current_sl = current_atr * 2.0
                        else:
                            current_tp = tp_pct
                            current_sl = sl_pct
                            
                        tp_pips = (current_tp * close_p) / (point * 10.0)
                        sl_pips = (current_sl * close_p) / (point * 10.0)
                        
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
    
    max_buy = float(np.max(prob_buy)) if len(prob_buy) > 0 else 0.0
    min_buy = float(np.min(prob_buy)) if len(prob_buy) > 0 else 0.0
    max_sell = float(np.max(prob_sell)) if len(prob_sell) > 0 else 0.0
    min_sell = float(np.min(prob_sell)) if len(prob_sell) > 0 else 0.0
    
    return {
        "best_res": best_res,
        "all_res": all_res,
        "prob_stats": {
            "max_buy": max_buy, "min_buy": min_buy,
            "max_sell": max_sell, "min_sell": min_sell
        }
    }

# =====================================================================
# AI FEEDBACK LOOP (GEMINI REST CALL)
# =====================================================================
def get_ai_feedback(model_name, api_key, result_summary, current_config, training_history=None):
    """
    Module 4: AI Feedback Loop. Gửi kết quả backtest, lịch sử các chặng, và mã nguồn
    để Gemini phân tích và đưa ra Ý TƯỞNG ĐỘT PHÁ, tự do điều chỉnh cấu trúc mạng và dữ liệu.
    """
    if not api_key:
        print("[AI-Feedback] No GEMINI_API_KEY available. Keeping existing config.")
        return current_config
        
    print(f"[AI-Feedback] Sending performance and FULL HISTORY to Gemini ({model_name})...")
    
    import json
    history_str = json.dumps(training_history, indent=2, ensure_ascii=False) if training_history else "Chưa có lịch sử (Bước 1)"

    prompt = f"""Chúng tôi đang vận hành Hệ thống định lượng V7 (QTS-V7). Đây là kết quả Backtest chặng vừa qua:
- Tổng số giao dịch: {result_summary['trades']}
- Tỷ lệ thắng (Win Rate): {result_summary['win_rate']*100:.2f}%
- Hệ số lợi nhuận (Profit Factor): {result_summary['profit_factor']:.2f}
- PnL đạt được: {result_summary['pnl']*100:.3f}%

Cấu hình siêu tham số hiện tại:
- TIMEFRAME: {current_config.get('timeframe', 'M5')}
- LEADERS: {current_config.get('leaders', ['BTCUSD', 'ETHUSD', 'SOLUSD'])}
- LEARNING_RATE: {current_config.get('learning_rate', 0.00005)}
- EPOCHS: {current_config.get('epochs', 500)}
- TP_PCT: {current_config.get('tp_pct')}
- SL_PCT: {current_config.get('sl_pct')}
- MAX_LAG_STEPS: {current_config.get('max_lag_steps')}
- CORRELATION_THRESHOLD: {current_config.get('correlation_threshold')}
- MAX_HOLD_BARS: {current_config.get('max_hold_bars')}

===============================
[LỊCH SỬ ĐÀO TẠO CÁC CHẶNG TRƯỚC (WALK-FORWARD HISTORY)]
{history_str}
===============================
[TÓM TẮT KIẾN TRÚC HỆ THỐNG V7]
- Mô hình: Mạng Nơ-ron nhân tạo sử dụng PyTorch.
- Logic Data: Dùng giá của các mã `leaders` (ví dụ BTCUSD, ETHUSD) làm tín hiệu dẫn dắt dự đoán mã follower.
- Đào tạo: Kỹ thuật Walk-Forward (cuốn chiếu liên tục). Tối ưu weights qua `learning_rate` và `epochs`.
- Chiến thuật: Chốt lời/cắt lỗ theo `tp_pct` / `sl_pct`, giữ tối đa `max_hold_bars` nến.
- Lọc tín hiệu: Dùng `max_lag_steps` tìm độ trễ tối ưu, `correlation_threshold` lọc tương quan lõi.
===============================

Hãy đóng vai trò chuyên gia Quant. Dựa vào KẾT QUẢ HIỆN TẠI, LỊCH SỬ CÁC BƯỚC TRƯỚC và KIẾN TRÚC HỆ THỐNG, hãy đưa ra Ý TƯỞNG ĐỘT PHÁ (ai_reasoning) và đề xuất điều chỉnh siêu tham số mới để tối ưu lợi nhuận.
Đặc quyền siêu cấp: Bạn ĐƯỢC PHÉP thay đổi 'timeframe' (VD: 'M1', 'M5', 'M15', 'H1'), thay đổi danh sách 'leaders' (chọn các mã crypto như BTCUSD, ETHUSD, SOLUSD, BNBUSD, v.v.), và thay đổi 'learning_rate', 'epochs' của mạng Nơ-ron.
Trách nhiệm Phân tích:
- Khi số lượng lệnh quá ÍT hoặc quá NHIỀU, hoặc PnL sụt giảm, bạn cần phân tích sâu TẠI SAO điều đó xảy ra dựa trên dữ liệu.
- Đừng chỉ chỉnh sửa tham số một cách máy móc. Hãy đề xuất giải pháp tận gốc rễ (trong trường `ai_reasoning`). Nếu bạn cho rằng thuật toán hiện tại, mô hình Pytorch, hay các hàm Loss/Threshold cần sửa đổi code để khắc phục vấn đề, hãy ĐỀ XUẤT RÕ RÀNG ý tưởng sửa code đó. Hệ thống sẽ để bạn tự do định hướng.

Yêu cầu trả về JSON thuần túy (KHÔNG dùng markdown backticks) với các trường sau:
{{ "ai_reasoning": string, "timeframe": string, "leaders": array of string, "learning_rate": float, "epochs": int, "max_lag_steps": int, "correlation_threshold": float, "tp_pct": float, "sl_pct": float, "max_hold_bars": int }}
"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    req_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "ai_reasoning": {"type": "STRING"},
                    "timeframe": {"type": "STRING"},
                    "leaders": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "learning_rate": {"type": "NUMBER"},
                    "epochs": {"type": "INTEGER"},
                    "max_lag_steps": {"type": "INTEGER"},
                    "correlation_threshold": {"type": "NUMBER"},
                    "tp_pct": {"type": "NUMBER"},
                    "sl_pct": {"type": "NUMBER"},
                    "max_hold_bars": {"type": "INTEGER"}
                },
                "required": ["ai_reasoning", "timeframe", "leaders", "learning_rate", "epochs", "max_lag_steps", "correlation_threshold", "tp_pct", "sl_pct", "max_hold_bars"]
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
        with urllib.request.urlopen(req, timeout=40) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            text_response = resp_data["candidates"][0]["content"]["parts"][0]["text"]
            adjusted = json.loads(text_response.strip())
            print(f"[AI-Feedback] Adjusted config received successfully.")
            return adjusted
    except Exception as e:
        print(f"[AI-Feedback] Failed to call Gemini API feedback: {e}. Keeping current config.")
        return current_config

# =====================================================================
# SESSION FILTERING HELPER
# =====================================================================
def filter_by_session(X, Y, W, times, session_name, session_utc):
    """
    Lọc dữ liệu Train/Val theo giờ giao dịch của phiên (Tránh học rác ngoài giờ)
    Loại bỏ cuối tuần.
    """
    if session_name == "all":
        # Vẫn bỏ qua cuối tuần
        filtered_indices = []
        for idx, t in enumerate(times):
            if t.weekday() < 5:
                filtered_indices.append(idx)
        if not filtered_indices:
            return np.empty((0, X.shape[1], X.shape[2]), dtype=np.float32), np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32), []
        return X[filtered_indices], Y[filtered_indices], W[filtered_indices], [times[i] for i in filtered_indices]
        
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
        return np.empty((0, X.shape[1], X.shape[2]), dtype=np.float32), np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32), []
        
    return X[filtered_indices], Y[filtered_indices], W[filtered_indices], [times[i] for i in filtered_indices]

# =====================================================================
# CORE WALK-FORWARD ENGINE
# =====================================================================
def train_model(model, X, Y, W, lr, epochs, batch_size, X_val=None, Y_val=None, W_val=None):
    """Hàm huấn luyện CrossAssetTransformerModel tích hợp Validation Early Stopping để chống Overfitting."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    # Nới lỏng Class Weights để giảm áp lực, tránh Overfitting (chuyển từ 1:100 xuống 1:5)
    class_weights = np.array([1.0, 5.0, 5.0], dtype=np.float32)
    
    class_weights_tensor = torch.tensor(class_weights).to(device)
    
    # Sử dụng PnL-Aware Loss thay cho FocalLoss trực tiếp
    # Giảm gamma xuống 0.5 để bớt cực đoan
    criterion = PnLAwareLoss(weight=class_weights_tensor, gamma=0.5)
    # [NEW V6] Reconstruction Loss để chống học vẹt (Dùng SmoothL1Loss chống nổ gradient)
    recon_criterion = nn.SmoothL1Loss()
    
    # Custom PnL-Aware Focal Loss logic will handle the W weights
    # Giảm base LR xuống 1e-4 và bắt buộc dùng Scheduler có warmup (OneCycleLR)
    lr = 1e-4
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    
    tensor_dataset = TensorDataset(torch.tensor(X, dtype=torch.float32), torch.tensor(Y, dtype=torch.long), torch.tensor(W, dtype=torch.float32))
    loader = DataLoader(tensor_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=lr, steps_per_epoch=len(loader), epochs=epochs
    )
    
    if X_val is not None and Y_val is not None and W_val is not None and len(X_val) > 0:
        val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(Y_val, dtype=torch.long), torch.tensor(W_val, dtype=torch.float32))
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    else:
        val_loader = None
        
    patience = 20
    min_delta = 1e-4
    best_cls_loss = float('inf')
    best_recon_loss = float('inf')
    cls_patience_counter = 0
    recon_patience_counter = 0
    best_model_state = None
    
    is_warmup = True
    warmup_min_epochs = 5
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        total_cls = 0.0
        total_recon = 0.0
        
        for batch_x, batch_y, batch_w in loader:
            batch_x, batch_y, batch_w = batch_x.to(device), batch_y.to(device), batch_w.to(device)
            optimizer.zero_grad()
            logits, recon = model(batch_x)
            
            # PnL-Aware custom loss using batch_w
            loss_cls = criterion(logits, batch_y, batch_w)
            loss_recon = recon_criterion(recon, batch_x)
            
            if is_warmup:
                # Giai đoạn 1: Autoencoder Warmup
                loss = loss_recon
            else:
                # Giai đoạn 2: Classification Fine-tuning
                loss = loss_cls + 0.01 * loss_recon
                
            loss.backward()
            optimizer.step()
            scheduler.step()
            
            total_loss += loss.item()
            total_cls += loss_cls.item()
            total_recon += loss_recon.item()
            
        train_loss = total_loss / len(loader)
        train_cls_loss = total_cls / len(loader)
        
        # Validation Pass
        if val_loader is not None:
            model.eval()
            val_loss = 0.0
            val_cls = 0.0
            with torch.no_grad():
                for bx, by, bw in val_loader:
                    bx, by, bw = bx.to(device), by.to(device), bw.to(device)
                    logits, recon = model(bx)
                    # PnL-Aware custom loss using bw
                    loss_cls = criterion(logits, by, bw)
                    loss_recon = recon_criterion(recon, bx)
                    
                    if is_warmup:
                        v_loss = loss_recon
                    else:
                        v_loss = loss_cls + 0.01 * loss_recon
                        
                    val_loss += v_loss.item()
                    val_cls += loss_cls.item()
            epoch_loss = val_loss / len(val_loader)
            epoch_cls_loss = val_cls / len(val_loader)
            
            if is_warmup:
                print(f"  [Warmup] Epoch {epoch+1}/{epochs} | Train Recon: {train_loss:.4f} | Val Recon: {epoch_loss:.4f}")
            else:
                print(f"  [Train] Epoch {epoch+1}/{epochs} | Train CLS: {train_cls_loss:.4f} | Val CLS: {epoch_cls_loss:.4f}")
        else:
            epoch_loss = train_loss
            epoch_cls_loss = train_cls_loss
            if is_warmup:
                print(f"  [Warmup] Epoch {epoch+1}/{epochs} | Train Recon: {train_loss:.4f}")
            else:
                print(f"  [Train] Epoch {epoch+1}/{epochs} | Train CLS: {train_cls_loss:.4f}")
            
        # Kiểm tra sự hội tụ của loss (Early Stopping)
        if is_warmup:
            val_metric = epoch_loss if val_loader is not None else epoch_loss
            if val_metric < best_recon_loss - min_delta:
                best_recon_loss = val_metric
                recon_patience_counter = 0
            else:
                recon_patience_counter += 1
                
            if epoch >= warmup_min_epochs and recon_patience_counter >= 5:
                print(f"  [Warmup] Hoàn thành Warmup tại epoch {epoch+1} do Recon Loss hội tụ.")
                is_warmup = False
                cls_patience_counter = 0
        else:
            val_metric = epoch_cls_loss if val_loader is not None else epoch_cls_loss
            if val_metric < best_cls_loss - min_delta:
                best_cls_loss = val_metric
                cls_patience_counter = 0
                import copy
                best_model_state = copy.deepcopy(model.state_dict())
            else:
                cls_patience_counter += 1
                
            if cls_patience_counter >= patience:
                print(f"  [Train] Early Stopping: CLS Loss converged/overfitting and did not improve for {patience} epochs. Stopping at epoch {epoch+1}.")
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
    
    if df_all is None or df_all.empty:
        msg = f"❌ [QTS-V7] LỖI DỮ LIỆU: Không lấy được dữ liệu chuẩn cho {follower} hoặc {leaders}. Hệ thống từ chối huấn luyện để bảo vệ chất lượng mô hình!"
        print(msg)
        send_telegram_alert(tbot, chat_id, msg)
        return None
        
    # Đọc tham số huấn luyện ban đầu
    tp_pct = cfg["FEATURE_ENGINEERING"]["TP_PCT"]
    sl_pct = cfg["FEATURE_ENGINEERING"]["SL_PCT"]
    max_hold_bars = cfg["FEATURE_ENGINEERING"]["MAX_HOLD_BARS"]
    spread_pct = cfg["FEATURE_ENGINEERING"].get("SPREAD_PCT", 0.0)
    slippage_pct = cfg["FEATURE_ENGINEERING"].get("SLIPPAGE_PCT", 0.0)
    
    min_atr_pct = cfg.get("FILTERS", {}).get("MIN_ATR_PCT", 0.0)
    
    session_name = cfg.get("SESSION", "all").lower()
    session_utc = cfg.get("SESSION_UTC", {})
    
    lr_base = cfg["TRAINING"]["LEARNING_RATE_BASE"]
    lr_finetune = cfg["TRAINING"]["LEARNING_RATE_FINETUNE"]
    batch_size = cfg["TRAINING"]["BATCH_SIZE"]
    epochs_base = cfg["TRAINING"]["EPOCHS_BASE"]
    epochs_finetune = cfg["TRAINING"]["EPOCHS_FINETUNE"]
    
    max_lag = mcfg.get("features", {}).get("max_lag", 15)
    corr_thresh = mcfg.get("features", {}).get("correlation_threshold", 0.85)
    
    min_wr = mcfg["train"].get("min_win_rate_threshold", 0.40)
    print(f"[Walk-Forward] Ngưỡng WR tối thiểu lấy từ Config: {min_wr*100:.2f}%", flush=True)
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
        
    # Xây dựng features & labels
    X_all, Y_all, W_all, all_times, train_scaler = build_features_and_labels(
        df_found_train, leaders, tp_pct, sl_pct, max_hold_bars, seq_len=90,
        spread_pct=spread_pct, slippage_pct=slippage_pct, use_dynamic_atr=True,
        min_atr_pct=min_atr_pct
    )
    X_all, Y_all, W_all, all_times = filter_by_session(X_all, Y_all, W_all, all_times, session_name, session_utc)
    
    # [NEW] Phân tách xen kẽ Train/Val: 3 tuần Train, 1 tuần Val
    train_mask = []
    val_mask = []
    for t in all_times:
        days_diff = (t - dt_start).days
        if days_diff % 28 < 21:
            train_mask.append(True)
            val_mask.append(False)
        else:
            train_mask.append(False)
            val_mask.append(True)
            
    train_mask = np.array(train_mask)
    val_mask = np.array(val_mask)
    
    if len(train_mask) == 0 or not np.any(train_mask):
        err_msg = f"❌ <b>[QTS-V7] LỖI DỮ LIỆU</b>: Không có dữ liệu Train sau khi chia chu kỳ!"
        print(err_msg.replace("<b>", "").replace("</b>", ""))
        send_telegram_alert(tbot, chat_id, err_msg)
        return None
        
    X_tr = X_all[train_mask]
    Y_tr = Y_all[train_mask]
    W_tr = W_all[train_mask]
    tr_times = [all_times[i] for i in range(len(all_times)) if train_mask[i]]
    
    X_va = X_all[val_mask]
    Y_va = Y_all[val_mask]
    W_va = W_all[val_mask]
    va_times = [all_times[i] for i in range(len(all_times)) if val_mask[i]]
    
    # Kiểm tra phân phối nhãn trước khi Train
    unique, counts = np.unique(Y_tr, return_counts=True)
    label_counts = dict(zip(unique, counts))
    buy_count = label_counts.get(1, 0)
    sell_count = label_counts.get(2, 0)
    total_samples = len(Y_tr)
    
    buy_pct = (buy_count / total_samples) * 100 if total_samples > 0 else 0
    sell_pct = (sell_count / total_samples) * 100 if total_samples > 0 else 0
    
    if buy_pct < 1.0 or sell_pct < 1.0 or (buy_count + sell_count) < 20:
        err_msg = f"❌ <b>[QTS-V7] LỖI NHÃN DỮ LIỆU</b>: Tập Train không đủ nhãn BUY/SELL! (Buy: {buy_count} [{buy_pct:.2f}%], Sell: {sell_count} [{sell_pct:.2f}%], Tổng: {total_samples}). Thuật toán từ chối huấn luyện để tránh Bias 100% HOLD."
        print(err_msg.replace("<b>", "").replace("</b>", ""))
        send_telegram_alert(tbot, chat_id, err_msg)
        return None
    
    # Khởi tạo Temporal Fusion Transformer Model với cấu hình động từ AI (nếu có), mặc định về 64/4/3
    num_features = X_tr.shape[2]
    d_model_cfg = cfg["TRAINING"].get("D_MODEL", 128)
    nhead_cfg = cfg["TRAINING"].get("NHEAD", 8)
    num_layers_cfg = cfg["TRAINING"].get("NUM_LAYERS", 4)
    
    # Ép kiểu an toàn để d_model luôn chia hết cho nhead
    if d_model_cfg % nhead_cfg != 0:
        d_model_cfg = (d_model_cfg // nhead_cfg) * nhead_cfg
        
    model = TemporalFusionTransformerModel(
        num_features=num_features,
        d_model=d_model_cfg,
        nhead=nhead_cfg,
        num_layers=num_layers_cfg,
        dropout_rate=0.4
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    send_telegram_alert(tbot, chat_id, (
        f"✅ <b>[QTS-V7] HOÀN THÀNH CHUẨN BỊ DỮ LIỆU {session_name.upper()}</b>\n"
        f"• Dữ liệu Nền tảng xen kẽ (Train 3W/Test 1W): <code>{start_date}</code> -> <code>{foundation_end_str}</code>\n"
    ))
    
    # Xây dựng trước tập Validation để truyền vào hàm huấn luyện (Early Stopping)
    # [NEW] Đã được xây dựng xen kẽ trong tập Foundation. df_val dùng cho backtest Module 3 sẽ trỏ tới df_found_train.
    val_start_str = start_date
    val_end_str = foundation_end_str
    df_val = df_found_train
    
    # Train
    model = train_model(model, X_tr, Y_tr, W_tr, lr_base, epochs_base, batch_size, X_val=X_va, Y_val=Y_va, W_val=W_va)
    
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
        model, X_va, va_times, df_val, tp_pct, sl_pct, follower, max_hold_bars,
        spread_pct=spread_pct, slippage_pct=slippage_pct, min_atr_pct=min_atr_pct
    )
    backtest_res = backtest_data["best_res"]
    all_res = backtest_data["all_res"]
    
    wr = backtest_res["win_rate"]
    pf = backtest_res["profit_factor"]
    
    prob_stats = backtest_data.get("prob_stats", {})
    
    # Gửi tin kết quả Backtest
    report_val_msg = "📊 <b>Báo cáo Đánh giá Sơ bộ tập Validation:</b>\n"
    if prob_stats:
        report_val_msg += f"🧠 <b>Output Bộ Não:</b> BUY[{prob_stats['min_buy']:.4f} -> {prob_stats['max_buy']:.4f}] | SELL[{prob_stats['min_sell']:.4f} -> {prob_stats['max_sell']:.4f}]\n"
    report_val_msg += f"• Ngưỡng tối ưu: <code>{backtest_res.get('threshold', 0.40):.2f}</code> (WR: {backtest_res['win_rate']*100:.1f}%, PF: {backtest_res['profit_factor']:.2f}, Lệnh: {backtest_res['trades']})\n"
    
    report_val_msg += "\n<b>Chi tiết các ngưỡng song song:</b>\n"
    for r in all_res:
        r_pnl = r['pnl'] * 100
        r_pnl_usd = r['pnl_usd']
        report_val_msg += f"  - Mức {r['threshold']:.2f}: Lệnh <code>{r['trades']}</code> (<code>{r.get('trades_per_day', 0):.1f} L/N</code>) | WR <code>{r['win_rate']*100:.1f}%</code> | PF <code>{r['profit_factor']:.2f}</code> | PnL <code>{r_pnl:.2f}%</code> (<b>${r_pnl_usd:.2f}</b>)\n"
        
    # So sánh với ngưỡng (Dựa trên ngưỡng TỐI ƯU NHẤT)
    if backtest_res['trades'] == 0:
        is_passed = False
        report_val_msg += "\n⚠️ <b>Chú ý:</b> Model KHÔNG VÀO LỆNH nào ở Validation."
    else:
        is_passed = (wr >= min_wr) and (pf >= min_pf)
        
    if not is_passed:
        err_msg = f"{report_val_msg}\n\n❌ <b>KHÔNG ĐẠT NGƯỠNG TỐI THIỂU Ở VÒNG 1!</b> (Mức Tối Ưu {backtest_res['threshold']:.2f} có Lệnh {backtest_res['trades']}, WR {wr*100:.1f}%/{min_wr*100:.1f}%, PF {pf:.2f}/{min_pf:.2f}). Thoát chương trình để AI phân tích."
        send_telegram_alert(tbot, chat_id, err_msg)
        print(err_msg)
        raise Exception(f"AI_FEEDBACK_REQUIRED: Vòng 1 không đạt ngưỡng tối thiểu. Yêu cầu AI (Antigravity) phân tích lại cấu hình hoặc thuật toán!\nChi tiết: {backtest_res}")
        
    send_telegram_alert(tbot, chat_id, f"{report_val_msg}\n\n🟢 <b>Hoàn tất Đánh giá Sơ bộ!</b> Chuyển sang Module 4 (Vòng lặp tiến hóa).")
    
    # =====================================================================
    # MODULE 4: WALK-FORWARD CONTINUAL LEARNING LOOP (VÒNG LẶP TIẾN HÓA)
    # =====================================================================
    print("\n[WF] --- BẮT ĐẦU MODUL 4: VÒNG LẶP TIẾN HÓA WALK-FORWARD ---")
    
    # Khởi tạo con trỏ thời gian
    current_val_start = dt_foundation_end - timedelta(days=slide_step_days)
    slide_train_days = 28  # Dùng 4 tuần dữ liệu mới nhất
    step_idx = 1
    cumulative_pnl = backtest_res["pnl"]
    cumulative_pnl_dict = {r['threshold']: r['pnl'] for r in all_res}
    training_history = []  # NEW: Lưu lịch sử đào tạo
    all_steps_metrics = {}
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = "AIzaSyAJlG9q3BVsHLC3XhQWoWTlPNfN3djxro0"
    ai_model = mcfg.get("ai", {}).get("llm_model", "gemini-1.5-flash")
    
    current_ai_config = {
        "timeframe": timeframe,
        "leaders": leaders,
        "learning_rate": lr_finetune,
        "epochs": epochs_finetune,
        "max_lag_steps": max_lag,
        "correlation_threshold": corr_thresh,
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "max_hold_bars": max_hold_bars
    }
    
    consecutive_slide_failures = 0
    
    while True:
        # Tịnh tiến cửa sổ
        current_val_start = current_val_start + timedelta(days=slide_step_days)
        current_val_end = current_val_start + timedelta(days=validation_days)
        current_train_end = current_val_start
        current_train_start = current_train_end - timedelta(days=slide_train_days)
        
        # Điều kiện Dừng: Nếu vượt quá end_date
        if current_val_end > datetime.strptime(end_date, "%Y-%m-%d"):
            print(f"[WF] Validation end date {current_val_end.strftime('%Y-%m-%d')} exceeds total end_date {end_date}. Exiting loop.")
            break
            
        train_start_str = current_train_start.strftime("%Y-%m-%d")
        train_end_str = current_train_end.strftime("%Y-%m-%d")
        val_start_str = current_val_start.strftime("%Y-%m-%d")
        val_end_str = current_val_end.strftime("%Y-%m-%d")
        
        print(f"\n[WF] --- BƯỚC TRƯỢT #{step_idx} ---")
        
        # AI Dynamic Architecture Updates
        if step_idx > 1:
            new_tf = current_ai_config.get("timeframe", timeframe)
            new_ldrs = current_ai_config.get("leaders", leaders)
            if new_tf != timeframe or set(new_ldrs) != set(leaders):
                timeframe = new_tf
                leaders = new_ldrs
                print(f"[RE-FETCH] AI đã yêu cầu đổi cấu trúc dữ liệu! Timeframe: {timeframe}, Leaders: {leaders}")
                df_all = get_synced_data(leaders, follower, timeframe, start_date, end_date, mt5_path)
            
            lr_finetune = current_ai_config.get("learning_rate", lr_finetune)
            epochs_finetune = current_ai_config.get("epochs", epochs_finetune)
            
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
        
        # Xây dựng data train/test chặng mới
        X_tr_step, Y_tr_step, W_tr_step, tr_step_times, step_scaler = build_features_and_labels(
            df_tr_step, leaders, 
            current_ai_config["tp_pct"], current_ai_config["sl_pct"], 
            current_ai_config["max_hold_bars"], seq_len=90,
            spread_pct=spread_pct, slippage_pct=slippage_pct, use_dynamic_atr=True,
            min_atr_pct=min_atr_pct
        )
        X_tr_step, Y_tr_step, W_tr_step, tr_step_times = filter_by_session(X_tr_step, Y_tr_step, W_tr_step, tr_step_times, session_name, session_utc)
        
        X_va_step, Y_va_step, W_va_step, va_step_times, _ = build_features_and_labels(
            df_va_step, leaders, 
            current_ai_config["tp_pct"], current_ai_config["sl_pct"], 
            current_ai_config["max_hold_bars"], seq_len=90,
            spread_pct=spread_pct, slippage_pct=slippage_pct, scaler_dict=step_scaler, use_dynamic_atr=True,
            min_atr_pct=min_atr_pct
        )
        X_va_step, Y_va_step, W_va_step, va_step_times = filter_by_session(X_va_step, Y_va_step, W_va_step, va_step_times, session_name, session_utc)
        
        # Load weights tốt nhất từ chặng trước (hoặc foundation ở bước đầu)
        weight_to_load = found_weight_path if step_idx == 1 else os.path.join(brains_dir, f"aamt_v7_step_{step_idx-1}.pth")
        
        # Tự động thay đổi input dimension nếu AI đổi feature size (Ví dụ thêm/bớt Leader)
        current_num_features = X_tr_step.shape[2]
        if current_num_features != num_features:
            print(f"[WF] Kích thước dữ liệu thay đổi ({num_features} -> {current_num_features}). Tái cấu trúc bộ não...")
            model = TemporalFusionTransformerModel(
                num_features=current_num_features,
                d_model=d_model_cfg,
                nhead=nhead_cfg,
                num_layers=num_layers_cfg,
                dropout_rate=0.4
            )
            model.to(device)
            num_features = current_num_features
            
            # Load the previous state dict but gracefully skip shape mismatches (e.g. input_proj)
            try:
                pretrained_dict = torch.load(weight_to_load, map_location=device)
            except Exception:
                pretrained_dict = torch.load(weight_to_load, map_location=device, weights_only=False)
                
            model_dict = model.state_dict()
            matched_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict and v.shape == model_dict[k].shape}
            model_dict.update(matched_dict)
            model.load_state_dict(model_dict)
            print(f"[WF] Đã tái cấu trúc lớp Input thành công. Đã nạp lại {len(matched_dict)}/{len(model_dict)} tensors.")
        else:
            try:
                model.load_state_dict(torch.load(weight_to_load, map_location=device))
            except Exception:
                model.load_state_dict(torch.load(weight_to_load, map_location=device, weights_only=False))
        
        # Huấn luyện tiếp tục (Finetuning) với LR nhỏ (Cung cấp thêm Validation Set để Early Stopping chuẩn xác)
        model = train_model(model, X_tr_step, Y_tr_step, W_tr_step, lr_finetune, epochs_finetune, batch_size, X_val=X_va_step, Y_val=Y_va_step, W_val=W_va_step)
        
        # Lưu weights bộ não bước trượt
        step_weight_path = os.path.join(brains_dir, f"aamt_v7_step_{step_idx}.pth")
        torch.save(model.state_dict(), step_weight_path)
        
        # Backtest
        step_data = run_backtest_simulation(
            model, X_va_step, va_step_times, df_va_step, 
            current_ai_config["tp_pct"], current_ai_config["sl_pct"],
            follower,
            current_ai_config["max_hold_bars"],
            spread_pct=spread_pct, slippage_pct=slippage_pct
        )
        step_bt = step_data["best_res"]
        all_res_step = step_data["all_res"]
        prob_stats = step_data.get("prob_stats", {})
        
        cumulative_pnl += step_bt["pnl"]
        step_pnl_usd = step_bt["pnl_usd"]
        cumulative_pnl_usd = cumulative_pnl * 10000.0
        
        # Báo cáo kết quả Backtest chặng
        report_step_msg = (
            f"📊 <b>Báo cáo chặng bước trượt #{step_idx} (Tập Test):</b>\n"
            f"• Thời gian: <code>{val_start_str}</code> -> <code>{val_end_str}</code>\n"
        )
        if prob_stats:
            report_step_msg += f"🧠 <b>Output Bộ Não:</b> BUY[{prob_stats['min_buy']:.4f} -> {prob_stats['max_buy']:.4f}] | SELL[{prob_stats['min_sell']:.4f} -> {prob_stats['max_sell']:.4f}]\n"
        report_step_msg += f"• Ngưỡng tối ưu: <code>{step_bt.get('threshold', 0.40):.2f}</code> (WR: {step_bt['win_rate']*100:.1f}%, PF: {step_bt['profit_factor']:.2f}, Lệnh: {step_bt['trades']})\n\n"
        report_step_msg += f"<b>Chi tiết các ngưỡng song song:</b>\n"
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
        
        # Cập nhật lịch sử
        step_history_record = {
            "step": step_idx,
            "train_period": f"{train_start_str} -> {train_end_str}",
            "test_period": f"{val_start_str} -> {val_end_str}",
            "config_used": current_ai_config.copy(),
            "performance": {
                "trades": step_bt['trades'],
                "win_rate": step_bt['win_rate'],
                "profit_factor": step_bt['profit_factor'],
                "pnl_pct": step_bt['pnl']*100
            }
        }
        training_history.append(step_history_record)

        # Cập nhật tiến trình trượt và kiểm tra điều kiện dừng sớm (Early Stopping)
        if step_bt['pnl'] < 0:
            consecutive_slide_failures += 1
        else:
            consecutive_slide_failures = 0
            
        if consecutive_slide_failures >= 3 or step_bt['pnl'] < -0.05:
            stop_msg = (
                f"🛑 <b>DỪNG VÒNG LẶP TIẾN HÓA SỚM!</b>\n"
                f"Vòng trượt #{step_idx} ghi nhận thua lỗ quá mức cho phép.\n"
                f"• PnL chặng này: {step_bt['pnl']*100:.2f}%\n"
                f"• Số lần trượt lỗ liên tiếp: {consecutive_slide_failures}\n"
                f"Hệ thống tự động ngắt để bảo toàn vốn."
            )
            print(stop_msg)
            send_telegram_alert(tbot, chat_id, stop_msg)
            break
                
        # Lưu kết quả chặng vào kết quả results/
        step_result = {
            "step": step_idx,
            "val_start": val_start_str,
            "val_end": val_end_str,
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
