import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import os
import sys
import time

def fetch_mt5_data(symbol="XAUUSD", timeframe=mt5.TIMEFRAME_M1):
    print("Đang khởi động kết nối vào MT5 đang mở...")
    MT5_MAIN_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    
    if not mt5.initialize(path=MT5_MAIN_PATH):
        print("Lỗi: Khởi tạo thư viện MetaTrader5 thất bại!")
        print(f"Error code: {mt5.last_error()}")
        return None
        
    print("Khởi tạo MT5 thành công. Phiên bản Terminal:", mt5.version())
    
    # Kiểm tra mã giao dịch có tồn tại không
    selected = mt5.symbol_select(symbol, True)
    if not selected:
        print(f"Lỗi: Không tìm thấy mã {symbol} trong MT5.")
        print("Cách sửa: Mở phần mềm MT5 -> Bấm Ctrl+U (Symbols) -> Tìm XAUUSD -> Nhấp đúp cho hiện vàng -> Thử lại.")
        mt5.shutdown()
        return None
        
    print(f"Bắt đầu tải nến 1 phút (M1) gần nhất cho {symbol}...")
    
    is_live = (len(sys.argv) > 1 and sys.argv[1] == "live")
    bars = 1440 if is_live else 1000000 # Cào siêu sâu 1 triệu nến để đảm bảo phủ kín năm ngoái
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    
    if rates is None or len(rates) == 0:
        print(f"Lỗi: Không tải được lịch sử giá. Có thể sàn Demo chưa có đủ data (Error: {mt5.last_error()})")
        mt5.shutdown()
        return None
        
    print(f"Tải HOÀN TẤT: Rút thành công {len(rates):,} nến từ MT5.")
    
    # --- THUẬT TOÁN ĐỒNG BỘ MÚI GIỜ MT5 VỀ UTC CHUẨN ---
    tick = mt5.symbol_info_tick(symbol)
    offset_sec = (tick.time - int(time.time())) if (tick and tick.time > 0) else 0
    offset_hours = round(offset_sec / 3600)
    
    df = pd.DataFrame(rates)
    df['time'] = df['time'] - (offset_hours * 3600) # Ép phẳng về UTC 0
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('datetime', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    # Lọc lại đúng mốc từ 2025-01-01 (Bỏ qua lọc nếu đang chạy Live cho nhẹ)
    if not is_live:
        df = df[df.index >= pd.to_datetime("2025-01-01")]
        print(f"Đã lọc dữ liệu từ 2025-01-01, còn lại {len(df):,} nến.")
    
    mt5.shutdown()
    return df

def save_to_parquet(df, path):
    try:
        df.to_parquet(path)
        print(f"Đã lưu Parquet thành công tại {path}\n")
    except Exception as e:
        print(f"Lỗi lưu file: {e}")

if __name__ == "__main__":
    base_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"
    data_path = os.path.join(base_path, "data")
    os.makedirs(data_path, exist_ok=True)
    
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "XAGUSD", "VIXY"]
    
    for symbol in symbols:
        print(f"\n{'='*40}")
        df = fetch_mt5_data(symbol)
        
        if df is not None and not df.empty:
            file_path = os.path.join(data_path, f"{symbol.lower()}_1m_2025_2026.parquet")
            save_to_parquet(df, file_path)
            
    print(f"\nHoàn tất cào dữ liệu từ MT5! Thư mục lưu: {data_path}")
