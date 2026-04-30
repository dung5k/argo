# -*- coding: utf-8 -*-
"""
crawl_crypto_v3.py - Cào dữ liệu Crypto từ Binance (ccxt) và NASDAQ từ MT5
Dùng cho config V3 Crypto (ETH/USDT target + BTC/USDT + ETH/BTC + USTECm)

Naming convention: {SYM}_MT5_1M_2026.parquet (tương thích với pipeline V3 hiện có)
"""
import os
import sys
import json
import time
import argparse
import pandas as pd
import ccxt
import concurrent.futures
from datetime import datetime, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ==============================================================
# PHẦN 1: Cào từ Binance
# ==============================================================
def fetch_binance(symbol: str, timeframe: str, since_str: str) -> tuple[str, pd.DataFrame]:
    """Cào OHLCV từ Binance cho 1 symbol (Hỗ trợ Taker Buy Volume và Funding Rate)."""
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since_ts = exchange.parse8601(since_str)
    now_ts   = exchange.milliseconds()
    all_ohlcv = []
    limit = 1000
    
    binance_sym = symbol.replace('/', '')

    log(f"  → Cào Binance Futures: {symbol} ({timeframe}) từ {since_str}")
    while since_ts < now_ts:
        try:
            # Dùng fapi để lấy Taker Buy Volume
            ohlcv = exchange.fapiPublicGetKlines({
                'symbol': binance_sym,
                'interval': timeframe,
                'startTime': since_ts,
                'limit': limit
            })
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since_ts = int(ohlcv[-1][0]) + (60_000 if timeframe == '1m' else 300_000)
        except ccxt.NetworkError as e:
            log(f"    [WARN] NetworkError {symbol}: {e}. Retry sau 3s...")
            time.sleep(3)
        except Exception as e:
            log(f"    [ERROR] {symbol}: {e}")
            break

    if not all_ohlcv:
        log(f"  ❌ KHÔNG CÓ DỮ LIỆU CHO {symbol}!")
        return symbol, pd.DataFrame()

    # Parse columns từ Binance klines
    # [0: Open time, 1: Open, 2: High, 3: Low, 4: Close, 5: Volume, 6: Close time, 7: Quote vol, 8: Trades, 9: Taker buy base vol, 10: Taker buy quote vol]
    df = pd.DataFrame(all_ohlcv)
    df = df.iloc[:, [0, 1, 2, 3, 4, 5, 9]]
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_volume']
    
    # Ép kiểu dữ liệu
    for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_volume']:
        df[col] = df[col].astype(float)
        
    df['time'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.set_index('time', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume', 'taker_buy_volume']]
    
    df['real_volume'] = df['volume']
    df['spread'] = 0
    
    # ------------------------------------------------------------------
    # Lấy Funding Rate
    # ------------------------------------------------------------------
    log(f"  → Cào Funding Rate cho {symbol}...")
    fr_since_ts = exchange.parse8601(since_str)
    all_fr = []
    while fr_since_ts < now_ts:
        try:
            fr_data = exchange.fetch_funding_rate_history(symbol + ':USDT', since=fr_since_ts, limit=500)
            if not fr_data:
                break
            all_fr.extend(fr_data)
            fr_since_ts = fr_data[-1]['timestamp'] + 1000
        except Exception as e:
            log(f"    [WARN] Lỗi kéo Funding Rate {symbol}: {e}")
            break
            
    if all_fr:
        fr_df = pd.DataFrame(all_fr)
        fr_df['time'] = pd.to_datetime(fr_df['timestamp'], unit='ms', utc=True)
        fr_df.set_index('time', inplace=True)
        fr_df = fr_df[['fundingRate']]
        
        # Merge Funding Rate vào df chính (sử dụng forward fill vì FR 8 tiếng mới có 1 lần)
        df = df.join(fr_df, how='left')
        df['fundingRate'] = df['fundingRate'].ffill().fillna(0) # Fill NaN bằng 0 hoặc ffill
    else:
        df['fundingRate'] = 0.0

    log(f"  ✔️ {symbol}: {len(df)} nến. Latest={df.index[-1]}")
    return symbol, df


def binance_sym_to_filename(symbol: str) -> str:
    """ETH/USDT → ETHUSDT, ETH/BTC → ETHBTC"""
    return symbol.replace('/', '').upper()


# ==============================================================
# PHẦN 2: Cào NASDAQ từ MT5
# ==============================================================
def fetch_mt5_symbol(mt5_sym: str, mt5_path: str, start_str: str, end_str: str) -> pd.DataFrame:
    """Cào 1 symbol từ MT5. Trả về DataFrame."""
    import MetaTrader5 as mt5
    import pytz
    from datetime import datetime as dt

    tz = pytz.UTC
    start_dt = tz.localize(dt.strptime(f"{start_str} 00:00:00", "%Y-%m-%d %H:%M:%S"))
    end_dt   = tz.localize(dt.strptime(f"{end_str} 23:59:59",  "%Y-%m-%d %H:%M:%S"))

    if not mt5.initialize(mt5_path):
        log(f"  ❌ Không thể khởi động MT5 tại: {mt5_path}")
        return pd.DataFrame()

    rates = mt5.copy_rates_range(mt5_sym, mt5.TIMEFRAME_M1,
                                  int(start_dt.timestamp()), int(end_dt.timestamp()))
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        log(f"  ❌ MT5 không trả dữ liệu cho {mt5_sym}")
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume', 'real_volume', 'spread']]


# ==============================================================
# MAIN
# ==============================================================
def main(config_file: str):
    log(f"🚀 BẮT ĐẦU CÀO DỮ LIỆU CRYPTO V3 TỪ CONFIG: {config_file}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    train_cfg    = config.get("TRAINING", {})
    binance_cfg  = config.get("DATA_SOURCE", {}).get("CRYPTO_BINANCE", {})
    since_str    = binance_cfg.get("SINCE", train_cfg.get("TRAIN_START", "2024-01-01") + "T00:00:00Z")
    end_str      = train_cfg.get("VAL_END",    "2026-04-18")
    config_id = config.get("CONFIG_ID", "CFG_UNKNOWN")
    history_dir = os.path.join("workspaces", config_id, "data", "raw")
    binance_cfg  = config.get("DATA_SOURCE", {}).get("CRYPTO_BINANCE", {})
    brokers      = config.get("DATA_SOURCE", {}).get("BROKERS", {})
    routing      = config.get("DATA_SOURCE", {}).get("ROUTING", {})
    timeframe    = binance_cfg.get("TIMEFRAME", "1m")
    symbols_bn   = binance_cfg.get("SYMBOLS", [])

    os.makedirs(history_dir, exist_ok=True)
    missing = []

    # --- Binance symbols ---
    log(f"[1/2] Cào {len(symbols_bn)} mã từ Binance...")
    def _fetch(sym):
        return fetch_binance(sym, timeframe, since_str)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as exe:
        futures = {exe.submit(_fetch, sym): sym for sym in symbols_bn}
        for fut in concurrent.futures.as_completed(futures):
            sym, df = fut.result()
            if df.empty:
                missing.append(sym)
                continue
            fname = binance_sym_to_filename(sym)
            out_path = os.path.join(history_dir, f"{fname}_BINANCE_1M_2026.parquet")
            df.to_parquet(out_path)
            log(f"  💾 Đã lưu: {out_path} ({len(df)} nến)")

    # --- MT5 symbols (USTEC, ...) ---
    log(f"[2/2] Cào {len(routing)} mã từ MT5...")
    import MetaTrader5 as mt5_module
    broker_groups = {}
    for sym, brk in routing.items():
        if brk in ["BINANCE", "YFINANCE"]:
            continue
        path = brokers.get(brk, brokers.get("DEFAULT"))
        broker_groups.setdefault(path, []).append(sym)

    for mt5_path, sym_list in broker_groups.items():
        import MetaTrader5 as mt5
        log(f"  → MT5: {mt5_path}")
        if not mt5.initialize(mt5_path):
            log(f"  ❌ Khởi động MT5 thất bại! Error: {mt5.last_error()}")
            missing.extend(sym_list)
            continue

        import pytz
        from datetime import datetime as dt
        tz = pytz.UTC
        # Ưu tiên lấy TRAIN_START từ TRAINING dict, nếu không có thì trích xuất từ SINCE của BINANCE
        raw_since = binance_cfg.get("SINCE", "2024-01-01T00:00:00Z").split('T')[0]
        start_date = train_cfg.get('TRAIN_START', raw_since)
        start_dt = tz.localize(dt.strptime(f"{start_date} 00:00:00", "%Y-%m-%d %H:%M:%S"))
        end_dt   = tz.localize(dt.strptime(f"{end_str} 23:59:59", "%Y-%m-%d %H:%M:%S"))

        continuous = config.get("DATA_SOURCE", {}).get("CONTINUOUS_CONTRACTS", {})
        
        for sym in sym_list:
            # Resolve tên symbol thực trên MT5 (hỗ trợ CONTINUOUS_CONTRACTS)
            actual_mt5_sym = sym
            if sym in continuous:
                prefix = continuous[sym].get("PREFIX", sym)
                # Tìm symbol thực trên MT5 bằng prefix
                all_syms = mt5.symbols_get()
                matches = [s.name for s in all_syms if s.name.startswith(prefix)] if all_syms else []
                if matches:
                    actual_mt5_sym = matches[0]
                    log(f"  📌 Resolve {sym} → {actual_mt5_sym} (prefix={prefix})")
                else:
                    log(f"  ❌ Không tìm thấy symbol prefix={prefix} trên MT5!")
                    missing.append(sym)
                    continue
            
            rates = mt5.copy_rates_range(actual_mt5_sym, mt5.TIMEFRAME_M1,
                                          int(start_dt.timestamp()), int(end_dt.timestamp()))
            if rates is None or len(rates) == 0:
                log(f"  ⚠️ copy_rates_range thất bại, thử copy_rates_from_pos...")
                rates = mt5.copy_rates_from_pos(actual_mt5_sym, mt5.TIMEFRAME_M1, 0, 50000)
            if rates is None or len(rates) == 0:
                log(f"  ❌ Không có dữ liệu MT5 cho {actual_mt5_sym} ({sym})!")
                missing.append(sym)
                continue

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
            df.set_index('time', inplace=True)
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
            df_save = df[['open', 'high', 'low', 'close', 'volume', 'real_volume', 'spread']].copy()

            # Loại bỏ suffix 'm' để tạo filename chuẩn — dùng tên config (không phải actual MT5 sym)
            sym_clean = sym.upper().rstrip('M') if sym.upper().endswith('M') else sym.upper()
            out_path = os.path.join(history_dir, f"{sym_clean}_MT5_1M_2026.parquet")
            df_save.to_parquet(out_path)
            log(f"  ✔️ MT5 {actual_mt5_sym} → {sym_clean}: {len(df_save)} nến → {out_path}")

        mt5.shutdown()

    log(f"\n🎉 HOÀN TẤT. Tổng nến đã cào xong.")

    # --- YFINANCE symbols ---
    log(f"[3/3] Cào mã từ YFINANCE...")
    try:
        import yfinance as yf
        for sym, brk in routing.items():
            if brk == "YFINANCE":
                log(f"  → YFINANCE: {sym}")
                # yf.download(symbol, start=..., interval="1m")
                # Note: yfinance 1m data is only available for the last 7 days!
                # If we need history back to 2024, we might need a higher timeframe like 5m or 1h, 
                # or we just use MT5 for historical data.
                pass
    except Exception as e:
        log(f"  [ERROR] YFINANCE: {e}")

    if missing:
        log("\n" + "="*50)
        log(f"💥 LỖI NGHIÊM TRỌNG: Các mã sau bị THIẾU: {missing}")
        log("❌ HỆ THỐNG HUỶ VÌ THIẾU TÀI NGUYÊN BẮT BUỘC!")
        log("="*50)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", default="data/bot_config_eth_crypto_v3.json")
    args = parser.parse_args()
    main(args.config)
