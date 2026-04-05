import yfinance as yf
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

def fetch_macro_data(ticker, name, start_str='2025-01-01'):
    print(f"Bắt đầu tải dữ liệu Vĩ mô: {name} ({ticker})...")
    
    # yfinance cho phép tải khung 1h lên đến 730 ngày (2 năm).
    # Khung 1 phút (1m) chỉ tải được 7 ngày gần nhất, nên ta dùng 1h rồi lát sau ghép với Crypto
    # và điền khuyết (forward-fill).
    data = yfinance.download(
        tickers=ticker,
        start=start_str,
        interval='1h',
        progress=False
    )
    
    if data.empty:
        print(f"Không tải được dữ liệu cho {name}.")
        return None
        
    print(f"Tải thành công {len(data)} dòng (nến 1 giờ). Đang lưu Parquet...")
    
    # Làm phẳng columns (yfinance format sometimes has multi-index)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
        
    return data

def save_to_parquet(df, path):
    try:
        df.to_parquet(path)
        print(f"Lưu thành công tại {path}\n")
    except Exception as e:
        print(f"Lỗi lưu file: {e}")

if __name__ == "__main__":
    import yfinance  # delayed import just in case
    
    base_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"
    data_path = os.path.join(base_path, "data")
    os.makedirs(data_path, exist_ok=True)
    
    # Danh sách các mã vĩ mô cực kỳ quan trọng ảnh hưởng đến Crypto
    macro_symbols = {
        'DX-Y.NYB': 'DXY_USD_Index',   # Chỉ số sức mạnh đồng Đô la Mỹ
        '^NDX': 'NASDAQ_100',          # Cổ phiếu Công nghệ Mỹ (Crypto rất đồng pha)
        'GC=F': 'GOLD',                # Vàng Thế giới
        '^TNX': 'US_10Y_Yield'         # Lãi suất trái phiếu 10 năm của Mỹ
    }
    
    is_live = (len(sys.argv) > 1 and sys.argv[1] == "live")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d") if is_live else '2025-01-01'
    
    for ticker, name in macro_symbols.items():
        df = fetch_macro_data(ticker, name, start_str=start_date)
        if df is not None:
            # Lưu file dưới dạng Parquet
            file_path = os.path.join(data_path, f"{name.lower()}_1h_2025_2026.parquet")
            save_to_parquet(df, file_path)
