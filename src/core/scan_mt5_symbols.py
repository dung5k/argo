"""
scan_mt5_symbols.py
===================
Tự động kết nối từng MT5 terminal, quét toàn bộ mã giao dịch,
phân loại theo nhóm, trích xuất giờ giao dịch và lưu vào symbol_catalog.json
"""

import MetaTrader5 as mt5
import json
import os
from datetime import datetime, timezone

MT5_TERMINALS = {
    "EXNESS":   r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
    "DEFAULT":  r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "MT5_2":    r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe",
    "MTRADING": r"C:\Program Files\Mtrading MetaTrader 5\terminal64.exe",
    "ICMARKETS": r"C:\Program Files\MetaTrader 5 - ICMarkets\terminal64.exe",
}

# Map CALC_MODE -> loại tài sản dễ đọc
CALC_MODE_MAP = {
    0:  "forex",
    1:  "forex_no_leverage",
    2:  "futures",
    3:  "cfd",
    4:  "cfd_index",
    5:  "cfd_leverage",
    6:  "forex_exchange",
    32: "futures_forts",
    33: "stocks",   # exchange_stocks
    34: "stocks_moex",
    35: "crypto",
}

def classify_symbol(sym_name: str, calc_mode: int, sym_path: str) -> str:
    """Phân loại mã theo tên, calc_mode và path."""
    name = sym_name.upper()
    path_l = sym_path.lower()

    # Dựa theo calc_mode trước
    if calc_mode == 33 or calc_mode == 34:
        return "stocks"
    if calc_mode == 35:
        return "crypto"
    if calc_mode in (2, 32):
        return "futures"

    # Dựa theo tên
    if any(x in name for x in ["BTC", "ETH", "XRP", "LTC", "ADA", "SOL", "BNB", "DOGE", "DOT", "AVAX"]):
        return "crypto"
    if any(x in name for x in ["XAU", "GOLD", "XAG", "SILVER", "XPT", "PLATINUM", "XPD", "PALLADIUM", "XCU", "COPPER"]):
        return "precious_metals"
    if any(x in name for x in ["OIL", "BRENT", "WTI", "UKOIL", "USOIL", "NGAS", "XNG", "NATGAS"]):
        return "energy"
    if any(x in name for x in ["US30", "US500", "USTEC", "UK100", "GER", "DE30", "DE40", "JP225", "AUS200", "HK50", "SP500", "NAS", "DAX", "FTSE"]):
        return "indices"
    if any(x in name for x in ["VIX", "VIXY"]):
        return "volatility"
    if any(x in name for x in ["Z10Y", "ZN", "ZB", "TBOND", "TNOTE", "YIELD"]):
        return "bonds_futures"

    # Standard 6-char forex pairs
    clean = name.replace("M", "").replace(".A", "").replace("+", "").replace(".", "")
    currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK", "SGD", "HKD", "MXN", "ZAR", "TRY", "PLN", "HUF", "CZK", "CNH", "CNY"]
    is_forex = any(clean.startswith(c) for c in currencies) and any(clean.endswith(c) for c in currencies)
    if is_forex:
        return "forex"

    return "other"


def get_trading_sessions(sym_info) -> dict:
    """Trích xuất giờ giao dịch từ symbol_info."""
    sessions = {}
    DAY_NAMES = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    for day_idx, day_name in enumerate(DAY_NAMES):
        day_sessions = []
        for s_idx in range(8):  # MT5 cho phép tối đa 8 phiên/ngày
            try:
                res = mt5.symbol_info_session_trade(sym_info.name, day_idx, s_idx)
                if res and res.check:
                    if res.from_ms < res.to_ms:
                        from_h = res.from_ms // 3600000
                        from_m = (res.from_ms % 3600000) // 60000
                        to_h   = res.to_ms   // 3600000
                        to_m   = (res.to_ms   % 3600000) // 60000
                        day_sessions.append(f"{from_h:02d}:{from_m:02d}-{to_h:02d}:{to_m:02d}")
            except Exception:
                break
        if day_sessions:
            sessions[day_name] = day_sessions
    return sessions


def scan_terminal(alias: str, path: str) -> dict:
    """Kết nối MT5 terminal, quét toàn bộ mã, trả về dict kết quả."""
    print(f"\n{'='*60}")
    print(f"[SCAN] {alias}: {path}")
    mt5.shutdown()
    result = {"path": path, "connected": False, "symbols": {}}

    if not os.path.exists(path):
        print(f"  ⚠ File không tồn tại, bỏ qua.")
        return result

    if not mt5.initialize(path=path):
        err = mt5.last_error()
        print(f"  ✗ Không thể kết nối: {err}")
        return result

    info = mt5.terminal_info()
    version = mt5.version()
    result["connected"] = True
    result["terminal_name"] = info.name if info else alias
    result["version"] = list(version) if version else None
    print(f"  ✓ Kết nối thành công: {info.name if info else alias}")

    symbols = mt5.symbols_get()
    if not symbols:
        print(f"  ⚠ Không lấy được danh sách mã.")
        mt5.shutdown()
        return result

    print(f"  → Tổng số mã: {len(symbols)}")

    groups: dict[str, list] = {}
    for sym in symbols:
        try:
            calc_mode = sym.trade_calc_mode
            category  = classify_symbol(sym.name, calc_mode, sym.path)

            sessions = get_trading_sessions(sym)

            entry = {
                "name":        sym.name,
                "description": sym.description,
                "currency_base":   sym.currency_base,
                "currency_profit": sym.currency_profit,
                "digits":      sym.digits,
                "category":    category,
                "calc_mode":   CALC_MODE_MAP.get(calc_mode, f"unknown_{calc_mode}"),
                "contract_size": sym.trade_contract_size,
                "tick_size":   sym.trade_tick_size,
                "tick_value":  sym.trade_tick_value,
                "trading_sessions_utc": sessions,
            }
            groups.setdefault(category, []).append(entry)
        except Exception as exc:
            print(f"    ⚠ Lỗi xử lý {sym.name}: {exc}")

    result["symbols"] = groups
    counts = {k: len(v) for k, v in groups.items()}
    print(f"  → Phân loại: {counts}")
    mt5.shutdown()
    return result


def main():
    catalog = {
        "_description": "Danh mục đầy đủ tất cả mã giao dịch từ 4 nguồn MT5. Tự động sinh bởi scan_mt5_symbols.py",
        "_generated_at": datetime.now(timezone.utc).isoformat(),
        "brokers": {}
    }

    for alias, path in MT5_TERMINALS.items():
        catalog["brokers"][alias] = scan_terminal(alias, path)

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "mt5_symbol_catalog.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Đã lưu danh mục vào: {out_path}")
    total = sum(
        sum(len(v) for v in b.get("symbols", {}).values())
        for b in catalog["brokers"].values()
    )
    print(f"📊 Tổng số mã đã ghi: {total}")


if __name__ == "__main__":
    main()
