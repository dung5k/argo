import os
import sys
import json
import pandas as pd
import yfinance as yf
import time

def run_yfinance_crawl(config_path):
    print(f"🚀 Kích hoạt siêu năng lực YFinance Crawler cho Macro Leaders...")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    raw_dir = config.get("DATA_SOURCE", {}).get("RAW_LOCAL_DIR", "workspaces/CFG_XAG_LDN_V3_5/data/raw")
    os.makedirs(raw_dir, exist_ok=True)
    
    # 1. Tìm file XAGUSDm để lấy index chuẩn
    target_file = None
    for f in os.listdir(raw_dir):
        if "XAG" in f and f.endswith(".parquet"):
            target_file = os.path.join(raw_dir, f)
            break
            
    if not target_file:
        raise FileNotFoundError("Không tìm thấy file XAGUSDm để đồng bộ Index!")
        
    print(f"✔️ Đọc index chuẩn từ: {target_file}")
    df_target = pd.read_parquet(target_file)
    master_index = df_target.index
    
    start_date = master_index.min().strftime('%Y-%m-%d')
    end_date = (master_index.max() + pd.Timedelta(days=5)).strftime('%Y-%m-%d')
    
    symbols_to_download = {
        "VIXm": "^VIX",
        "US10Ym": "^TNX"
    }
    
    for local_sym, yf_sym in symbols_to_download.items():
        print(f"⬇️ Đang tải {yf_sym} ({local_sym}) từ Yahoo Finance (Daily)...")
        # Tải dữ liệu daily
        df_yf = yf.download(yf_sym, start=start_date, end=end_date, interval="1d")
        if df_yf.empty:
            print(f"⚠️ Lỗi: Không tải được dữ liệu cho {yf_sym}")
            continue
            
        # Xử lý MultiIndex column nếu có (yfinance >= 0.2.x)
        if isinstance(df_yf.columns, pd.MultiIndex):
            df_yf.columns = df_yf.columns.droplevel(1)
            
        # Đổi tên cột cho giống nguyên bản MT5 (không có prefix)
        df_yf = df_yf.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })
        
        # Vì đây là dữ liệu Daily, thời gian của index đang là 00:00:00 của ngày hôm đó
        # Để tránh look-ahead bias (biết giá đóng cửa của ngày hôm nay vào lúc 00:00 sáng nay),
        # ta phải DỊCH (shift) dữ liệu xuống 1 ngày.
        # Nghĩa là: Suốt ngày hôm nay (từ 00:00 đến 23:59), ta chỉ được nhìn thấy giá đóng cửa của NGÀY HÔM QUA.
        df_yf = df_yf.shift(1)
        
        # Đảm bảo index timezone-naive để có thể merge
        df_yf.index = df_yf.index.tz_localize(None)
        
        # 2. Reindex và Forward Fill lên khung M1
        # Tạo DataFrame rỗng với master_index
        df_m1 = pd.DataFrame(index=master_index)
        
        # Đảm bảo index timezone-naive
        df_yf.index = df_yf.index.tz_localize(None).normalize()
        
        # Chuyển master_index sang ngày để map với dữ liệu daily
        df_m1['date_only'] = df_m1.index.tz_localize(None).normalize()
        
        # Merge
        df_merged = pd.merge(df_m1, df_yf, left_on='date_only', right_index=True, how='left')
        df_merged = df_merged.drop(columns=['date_only'])
        
        # Forward fill những chỗ còn thiếu (cuối tuần, nghỉ lễ)
        df_merged = df_merged.ffill()
        
        # Điền NaN ở đầu bằng bfill (nếu có)
        df_merged = df_merged.bfill()
        
        # Thêm các cột bắt buộc của MT5
        df_merged["spread"] = 0
        df_merged["real_volume"] = 0
        
        # Đổi tên file cho phù hợp quy ước
        out_filename = f"{local_sym.replace('m','')}_MT5_1M_2026.parquet"
        out_path = os.path.join(raw_dir, out_filename)
        
        df_merged.to_parquet(out_path)
        print(f"✅ Đã lưu {local_sym} ({len(df_merged)} rows) -> {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crawl_yfinance_v3.py <config_path>")
        sys.exit(1)
    run_yfinance_crawl(sys.argv[1])
