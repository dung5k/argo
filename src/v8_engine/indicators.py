import pandas as pd
import numpy as np

def compute_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)  # default to 50
    return rsi

def compute_macd(df, fast=12, slow=26, signal=9):
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    return macd_line.fillna(0), signal_line.fillna(0), macd_hist.fillna(0)

def compute_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(period).mean()
    return atr.fillna(0.1) # small epsilon

def compute_ema(df, period):
    return df['close'].ewm(span=period, adjust=False).mean()

def add_all_indicators(df):
    """
    In-place computation of all required features.
    """
    df_out = df.copy()
    
    # Momentum
    df_out['rsi'] = compute_rsi(df_out)
    macd_l, macd_s, macd_h = compute_macd(df_out)
    df_out['macd'] = macd_l
    df_out['macd_signal'] = macd_s
    df_out['macd_hist'] = macd_h
    
    # Volatility
    df_out['atr'] = compute_atr(df_out)
    
    # Trend (Normalized distance to EMA)
    ema50 = compute_ema(df_out, 50)
    ema200 = compute_ema(df_out, 200)
    df_out['dist_ema50'] = (df_out['close'] - ema50) / df_out['atr']
    df_out['dist_ema200'] = (df_out['close'] - ema200) / df_out['atr']
    
    # Price Action
    df_out['body_size'] = np.abs(df_out['close'] - df_out['open']) / df_out['atr']
    df_out['upper_wick'] = (df_out['high'] - np.maximum(df_out['close'], df_out['open'])) / df_out['atr']
    df_out['lower_wick'] = (np.minimum(df_out['close'], df_out['open']) - df_out['low']) / df_out['atr']
    
    # Fix NaNs resulting from 0 ATR
    df_out.replace([np.inf, -np.inf], 0.0, inplace=True)
    df_out.fillna(0.0, inplace=True)
    
    return df_out
