import MetaTrader5 as mt5
import pandas as pd
import os
import sys
from datetime import datetime

# =========================================================================================
# 🔴 [YÊU CẦU ĐIỀN THÔNG TIN] 🔴
# SẾP HÃY THAY ĐỔI 2 BIẾN DƯỚI ĐÂY CHO ĐÚNG VỚI PHẦN MỀM MT5 THỨ 2 MÀ SẾP VỪA CÀI ĐẶT
# =========================================================================================

# 1. ĐƯỜNG DẪN TỚI FILE EXE CỦA SÀN MT5 THỨ 2 (Mặc định để Exness, Sếp trỏ đúng vào máy Sếp nhé)
MT5_ALT_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

# 2. CHỈNH SỬA TÊN MÃ (SYMBOL) ĐÚNG VỚI HẬU TỐ TRÊN TÀI KHOẢN CỦA SẾP (VÍ DỤ CÓ CHỮ 'm' HAY CHỮ 'c' Ở CUỐI)
# Định dạng: "Tên_Symbol_Của_Sàn": "Tạo_Ra_File_Tên_Giống_Hệt_Binance"
SYMBOL_MAP = {
    # Nhóm Crypto
    "BTCUSDm": "btc_usdt_1m_2025_2026",
    "ETHUSDm": "eth_usdt_1m_2025_2026",
    "SOLUSDm": "sol_usdt_1m_2025_2026",
    "BNBUSDm": "bnb_usdt_1m_2025_2026",
    "XRPUSDm": "xrp_usdt_1m_2025_2026",
    "ADAUSDm": "ada_usdt_1m_2025_2026",
    "DOGEUSDm": "doge_usdt_1m_2025_2026",
    "LINKUSDm": "link_usdt_1m_2025_2026",
    "DOTUSDm": "dot_usdt_1m_2025_2026",
    
}

# =========================================================================================

def print_log(msg):
    """In ra Terminal mà không bị giữ Buffer"""
    print(msg, flush=True)

def fetch_historical_rates(symbol, timeframe, limit=1000):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)
    if rates is None or len(rates) == 0:
        return None
        
    import time
    tick = mt5.symbol_info_tick(symbol)
    offset_sec = tick.time - int(time.time()) if tick else 0
    offset_hours = round(offset_sec / 3600)
    
    df = pd.DataFrame(rates)
    df['time'] = df['time'] - (offset_hours * 3600) # Ép phẳng về UTC 0 chuẩn
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('datetime', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'tick_volume']]
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    return df

def main():
    base_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"
    data_path = os.path.join(base_path, "data")
    os.makedirs(data_path, exist_ok=True)
    
    is_live = (len(sys.argv) > 1 and sys.argv[1] == "live")
    candles_count = 1000 if is_live else 500000
    
    print_log(f"Đang kích hoạt Mạch Đọc RAM MT5 Thứ 2 (Alt Data)...")
    
    # Kết nối MT5 vào thư mục Chỉ định của Sàn Thứ 2
    if not mt5.initialize(path=MT5_ALT_PATH):
        print_log(f"LỖI CHÍNH TỬ: Không thể khởi chạy MT5 tại đường dẫn: {MT5_ALT_PATH}")
        print_log("Sếp vui lòng check lại Biến MT5_ALT_PATH trong Code nhé!")
        mt5.shutdown()
        return

    print_log(f"KẾT NỐI IPC THÀNH CÔNG VỚI MT5 THỨ 2! Phiên bản: {mt5.version()}")
    
    success_count = 0
    fail_count = 0
    
    for mt5_symbol, binance_file_name in SYMBOL_MAP.items():
        file_path = os.path.join(data_path, f"{binance_file_name}.parquet")
        
        # Bỏ qua Bulk Download nếu file đã có sẵn ở chế độ khởi chạy lần đầu
        if not is_live and os.path.exists(file_path):
            success_count += 1
            continue
            
        print_log(f"Đang Vắt sữa (IPC): {mt5_symbol} -> {binance_file_name}.parquet")
        
        # Xác định khung Thời gian (H1 cho DXY Vĩ mô, M1 cho Crypto)
        timeframe = mt5.TIMEFRAME_H1 if "dxy" in binance_file_name else mt5.TIMEFRAME_M1
        
        df = fetch_historical_rates(mt5_symbol, timeframe, limit=candles_count)
        
        if df is not None and not df.empty:
            df.to_parquet(file_path)
            print_log(f" ✅ LƯU XONG: {mt5_symbol} ({len(df)} nến).")
            success_count += 1
        else:
            print_log(f" ❌ MẤT TÍN HIỆU: Không tìm thấy Symbol {mt5_symbol} trên sàn. Sai hậu tố 'm'?")
            fail_count += 1
            
    mt5.shutdown()
    print_log(f"HOÀN TẤT VÒNG CÀO IPC! Thành công: {success_count} | Thất bại: {fail_count}")

if __name__ == "__main__":
    main()
