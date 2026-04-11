"""
crawl_mt5.py - Cào dữ liệu M1 từ MT5 theo cấu hình ROUTING trong bot_config.

Hỗ trợ:
- Nhiều MT5 instance (EXNESS, DEFAULT, MT5_2...)
- Continuous contracts (USTECm*, Z10Y* — tự ghép từng tháng)
- 100% nguồn MT5, không dùng yfinance
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import os, sys, json, time
from pathlib import Path


def _mt5_path_for_broker(brokers: dict, broker_key: str) -> str:
    path = brokers.get(broker_key, brokers.get("DEFAULT", ""))
    if path == "LOCAL":
        return brokers.get("DEFAULT", "")
    return path


def _init_mt5(mt5_path: str) -> bool:
    """Khởi động MT5 instance tại đường dẫn chỉ định."""
    if not mt5.initialize(path=mt5_path):
        print(f"  [MT5] Lỗi khởi tạo: {mt5_path} | Error: {mt5.last_error()}")
        return False
    print(f"  [MT5] Kết nối thành công: {Path(mt5_path).parent.name} | Ver: {mt5.version()}")
    return True


def _utc_offset_hours() -> int:
    """Tính offset giờ của MT5 server so với UTC."""
    try:
        tick_time = mt5.symbol_info_tick("EURUSD")
        if tick_time and tick_time.time > 0:
            offset_sec = tick_time.time - int(time.time())
            return round(offset_sec / 3600)
    except Exception:
        pass
    return 0


def fetch_symbol(symbol: str, mt5_path: str, from_date: str = "2025-01-01") -> pd.DataFrame | None:
    """Cào M1 cho 1 symbol từ 1 MT5 instance cụ thể."""
    if not _init_mt5(mt5_path):
        return None

    if not mt5.symbol_select(symbol, True):
        print(f"  [MT5] Không tìm thấy mã {symbol}. Bỏ qua.")
        mt5.shutdown()
        return None

    print(f"  [MT5] Đang cào {symbol} (M1)...")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1_000_000)
    if rates is None or len(rates) == 0:
        print(f"  [MT5] Không lấy được data {symbol}: {mt5.last_error()}")
        mt5.shutdown()
        return None

    offset_h = _utc_offset_hours()
    df = pd.DataFrame(rates)
    df['time'] = df['time'] - offset_h * 3600
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('datetime', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)

    df = df[df.index >= pd.to_datetime(from_date)]
    print(f"  [MT5] {symbol}: {len(df):,} nến từ {from_date}")
    mt5.shutdown()
    return df


def fetch_continuous_contract(prefix: str, mt5_path: str,
                              contract_months: list = None,
                              from_date: str = "2025-01-01") -> pd.DataFrame | None:
    """
    Ghép Continuous Contract từ nhiều contract theo tháng.
    Ví dụ: Z10Y prefix → Z10YJ, Z10YK, Z10YM, Z10YU, Z10YZ, Z10YH (theo năm 2024-2026)
    """
    if not _init_mt5(mt5_path):
        return None

    years = ["24", "25", "26"]
    months = contract_months or ["H", "M", "U", "Z"]
    candidates = [f"{prefix}{m}{y}" for y in years for m in months]

    print(f"  [MT5] Continuous Contract {prefix}*: thử {len(candidates)} candidates...")
    frames = []
    for sym in candidates:
        if not mt5.symbol_select(sym, True):
            continue
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 1_000_000)
        if rates is None or len(rates) == 0:
            continue
        offset_h = _utc_offset_hours()
        df = pd.DataFrame(rates)
        df['time'] = df['time'] - offset_h * 3600
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        df = df[df.index >= pd.to_datetime(from_date)]
        if not df.empty:
            frames.append(df)
            print(f"    + {sym}: {len(df):,} nến")

    mt5.shutdown()
    if not frames:
        print(f"  [MT5] Không lấy được continuous contract {prefix}*")
        return None

    # Ghép, ưu tiên nến mới nhất khi trùng timestamp
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep='last')].sort_index()
    print(f"  [MT5] {prefix}* ghép: {len(merged):,} nến sau khi dedup")
    return merged


def crawl_all(config_path: str) -> None:
    """Entry point chính: đọc config, cào tất cả symbols theo ROUTING."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    data_source = cfg.get("DATA_SOURCE", {})
    brokers = data_source.get("BROKERS", {})
    routing = data_source.get("ROUTING", {})
    continuous = data_source.get("CONTINUOUS_CONTRACTS", {})
    suffix = data_source.get("DATASET_SUFFIX", "2025_2026")
    from_date = "2025-01-01"
    if "-" in suffix and suffix.count("-") == 0:
        pass  # dùng mặc định

    base_dir = Path(config_path).resolve().parent.parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"CRAWL MT5 - Config: {Path(config_path).name}")
    print(f"Data dir: {data_dir}")
    print(f"Suffix  : {suffix}")
    print(f"{'='*60}\n")

    # 1. Cào từng symbol thông thường theo ROUTING
    for symbol_key, broker_key in routing.items():
        # Các symbol là Continuous Contract xử lý riêng bên dưới
        if symbol_key in continuous:
            continue

        mt5_path = _mt5_path_for_broker(brokers, broker_key)
        if not mt5_path or mt5_path == "LOCAL":
            print(f"[SKIP] {symbol_key}: broker '{broker_key}' không có đường dẫn MT5.")
            continue

        # Loại bỏ suffix 'm' để lấy tên file chuẩn (XAUUSDm → xauusd)
        file_stem = symbol_key.lower().replace("m", "", 1) if symbol_key.endswith("m") else symbol_key.lower()
        out_file = data_dir / f"{file_stem}_1m_{suffix}.parquet"

        print(f"\n>>> Symbol: {symbol_key} | Broker: {broker_key}")
        df = fetch_symbol(symbol_key, mt5_path, from_date=from_date)
        if df is not None and not df.empty:
            df.to_parquet(out_file)
            print(f"  [SAVE] {out_file.name}")

    # 2. Cào Continuous Contracts (NASDAQ_100, US_10Y_YIELD...)
    for cc_key, cc_cfg in continuous.items():
        prefix = cc_cfg.get("PREFIX", "")
        broker_key = cc_cfg.get("BROKER", "DEFAULT")
        months = cc_cfg.get("CONTRACT_MONTHS", ["H", "M", "U", "Z"])
        mt5_path = _mt5_path_for_broker(brokers, broker_key)

        if not mt5_path:
            print(f"[SKIP] {cc_key}: không có đường dẫn MT5 broker '{broker_key}'.")
            continue

        out_file = data_dir / f"{cc_key.lower()}_1m_{suffix}.parquet"
        print(f"\n>>> Continuous: {cc_key} | Prefix: {prefix}* | Broker: {broker_key}")
        df = fetch_continuous_contract(prefix, mt5_path, contract_months=months, from_date=from_date)
        if df is not None and not df.empty:
            df.to_parquet(out_file)
            print(f"  [SAVE] {out_file.name}")

    print(f"\n{'='*60}")
    print("Hoàn tất cào dữ liệu từ MT5!")
    print(f"{'='*60}")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not config_path:
        # Tìm config mặc định
        default_dirs = [
            Path(__file__).resolve().parent.parent.parent / "data",
            Path("C:/argo/data"),
        ]
        for d in default_dirs:
            for name in ["bot_config_xau_ny_v1_5.json", "bot_config_xau.json", "bot_config.json"]:
                p = d / name
                if p.exists():
                    config_path = str(p)
                    break
            if config_path:
                break

    if not config_path or not Path(config_path).exists():
        print(f"[LỖI] Không tìm thấy file config. Truyền đường dẫn làm tham số đầu tiên.")
        sys.exit(1)

    crawl_all(config_path)
