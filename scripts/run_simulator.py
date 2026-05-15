"""
Script CLI chạy Historical Brain Simulator.

Usage:
    python scripts/run_simulator.py --config data/bot_config_xag_asian_v5.json --date 2026-05-14 --session asian

Options:
    --config   : Đường dẫn config JSON của brain cần test
    --date     : Ngày cần chạy giả lập (YYYY-MM-DD)
    --session  : Phiên giao dịch: asian | london | ny | all (default: asian)
    --output   : File CSV lưu kết quả chi tiết (optional)
    --fetch    : Nếu có flag này, sẽ cào data mới từ MT5 trước khi chạy
    --verbose  : Hiển thị log chi tiết pipeline FE
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.simulator.historical_simulator import HistoricalSimulator


def fetch_fresh_data(config: dict, days: int = 7):
    """
    Cào dữ liệu M1 mới từ MT5 và lưu vào workspace/data/raw/.
    Chỉ chạy khi có flag --fetch và MT5 đang mở.
    """
    print("[FETCH] Đang cào dữ liệu mới từ MT5...")
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[FETCH] ❌ MetaTrader5 package không có! Không thể cào data.")
        return False

    mt5_path = config.get("MT5_PATH", r"D:\mt5\MetaTrader 5 EXNESS\terminal64.exe")
    if not mt5.initialize(path=mt5_path):
        # Thử không có path
        if not mt5.initialize():
            print("[FETCH] ❌ Không thể kết nối MT5. Hãy chắc chắn MT5 đang chạy!")
            return False

    config_id = config.get("CONFIG_ID", "CFG_UNKNOWN")
    raw_dir = os.path.join(_ROOT, "workspaces", config_id, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)

    routing = config.get("DATA_SOURCE", {}).get("ROUTING", {})
    symbols = list(routing.keys())
    if not symbols:
        print("[FETCH] ⚠️ Không có symbols nào trong ROUTING config!")
        return False

    now = datetime.now(timezone.utc)
    date_from = now - timedelta(days=days + 2)

    success_count = 0
    for sym_m in symbols:
        sym_key = sym_m.replace("m", "").replace("M", "")
        parquet_path = os.path.join(raw_dir, f"{sym_key}_MT5_1M_2026.parquet")

        # Nếu đã có file, chỉ lấy thêm phần mới
        existing_end = None
        if os.path.exists(parquet_path):
            try:
                import pandas as pd
                existing_df = pd.read_parquet(parquet_path)
                if not isinstance(existing_df.index, pd.DatetimeIndex):
                    pass
                else:
                    existing_end = existing_df.index.max().to_pydatetime()
                    if existing_end.tzinfo is None:
                        import pytz
                        existing_end = existing_end.replace(tzinfo=timezone.utc)
                    print(f"[FETCH] {sym_key}: Cập nhật từ {existing_end.strftime('%Y-%m-%d %H:%M')} → now")
            except Exception as e:
                print(f"[FETCH] ⚠️ Không đọc được file cũ {sym_key}: {e}")

        fetch_from = existing_end if existing_end else date_from

        # Tìm tên symbol trên MT5
        mt5_sym = None
        candidates = [sym_m, sym_key, sym_key + "m", sym_key + ".a"]
        syms_avail = mt5.symbols_get()
        avail_names = {s.name for s in syms_avail} if syms_avail else set()
        for c in candidates:
            if c in avail_names:
                mt5_sym = c
                break

        if mt5_sym is None:
            print(f"[FETCH] ⚠️ Không tìm thấy {sym_m} trên MT5! Bỏ qua.")
            continue

        try:
            rates = mt5.copy_rates_range(
                mt5_sym,
                mt5.TIMEFRAME_M1,
                fetch_from,
                now,
            )
            if rates is None or len(rates) == 0:
                print(f"[FETCH] ⚠️ MT5 trả về rỗng cho {mt5_sym}")
                continue

            import pandas as pd
            df_new = pd.DataFrame(rates)
            df_new["datetime"] = pd.to_datetime(df_new["time"], unit="s", utc=True)
            df_new.set_index("datetime", inplace=True)
            df_new.drop(columns=["time"], errors="ignore", inplace=True)
            df_new.rename(columns={"tick_volume": "volume"}, inplace=True)

            # Merge với data cũ nếu có
            if os.path.exists(parquet_path):
                df_old = pd.read_parquet(parquet_path)
                if not isinstance(df_old.index, pd.DatetimeIndex):
                    df_old["datetime2"] = pd.to_datetime(df_old.index, unit="s", utc=True)
                    df_old.set_index("datetime2", inplace=True)
                if df_old.index.tz is None:
                    df_old.index = df_old.index.tz_localize("UTC")
                df_combined = pd.concat([df_old, df_new])
                df_combined = df_combined[~df_combined.index.duplicated(keep="last")]
                df_combined.sort_index(inplace=True)
            else:
                df_combined = df_new

            df_combined.to_parquet(parquet_path)
            print(f"[FETCH] ✅ {sym_key}: {len(df_new):,} nến mới | Total={len(df_combined):,} | Saved → {parquet_path}")
            success_count += 1

        except Exception as e:
            print(f"[FETCH] ❌ Lỗi cào {mt5_sym}: {e}")
            import traceback
            traceback.print_exc()

    mt5.shutdown()
    print(f"[FETCH] Hoàn tất: {success_count}/{len(symbols)} symbols")
    return success_count > 0


def main():
    parser = argparse.ArgumentParser(description="Historical Brain Simulator for XAG Bot")
    parser.add_argument("--config", required=True, help="Đường dẫn config JSON")
    parser.add_argument("--date", required=True, help="Ngày giả lập YYYY-MM-DD")
    parser.add_argument("--session", default="asian", help="Phiên: asian|london|ny|all")
    parser.add_argument("--output", default=None, help="File CSV lưu kết quả")
    parser.add_argument("--fetch", action="store_true", help="Cào dữ liệu mới từ MT5 trước")
    parser.add_argument("--verbose", action="store_true", help="Log chi tiết pipeline")
    parser.add_argument("--window", type=int, default=1500, help="Rolling window (nến, default=1500)")
    args = parser.parse_args()

    import json, logging

    # Cấu hình logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load config
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(_ROOT, config_path)

    if not os.path.exists(config_path):
        print(f"❌ Không tìm thấy config: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Tùy chọn cào data mới
    if args.fetch:
        ok = fetch_fresh_data(config, days=7)
        if not ok:
            print("⚠️ Cào data thất bại. Thử dùng data cũ có sẵn...")

    # Chạy simulator
    sim = HistoricalSimulator(
        config_path=config_path,
        window_size=args.window,
    )

    result_df = sim.run(
        date_str=args.date,
        session=args.session,
    )

    # Lưu CSV nếu có --output
    if args.output and not result_df.empty:
        out_path = args.output
        if not os.path.isabs(out_path):
            out_path = os.path.join(_ROOT, out_path)
        result_df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\n✅ Đã lưu kết quả: {out_path}")

    # In bảng tín hiệu chi tiết
    if not result_df.empty:
        signals = result_df[result_df["action"].str.contains("OPEN|WIN|LOSS", na=False)]
        if not signals.empty:
            print("\n📋 CHI TIẾT TÍN HIỆU:")
            print("─" * 70)
            for _, row in signals.iterrows():
                t = row["time"].strftime("%H:%M") if hasattr(row["time"], "strftime") else str(row["time"])
                buy_p = f"{row['buy_prob']:.2f}" if row["buy_prob"] is not None else " N/A "
                sell_p = f"{row['sell_prob']:.2f}" if row["sell_prob"] is not None else " N/A "
                print(f"  {t} | {str(row['action']):<25} | Close={row['close']:.4f} | B={buy_p} S={sell_p} | PnL={row['pnl']:+.4f}")
            print("─" * 70)

    return result_df


if __name__ == "__main__":
    main()
