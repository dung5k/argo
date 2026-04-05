import MetaTrader5 as mt5
import pandas as pd
import os
import sys
import time

# =========================================================================================
# 🔴 [YÊU CẦU ĐIỀN THÔNG TIN] 🔴
# SẾP HÃY THAY ĐỔI 2 BIẾN DƯỚI ĐÂY CHO ĐÚNG VỚI PHẦN MỀM MT5 THỨ 2 MÀ SẾP VỪA CÀI ĐẶT
# =========================================================================================

# 1. ĐƯỜNG DẪN TỚI FILE EXE CỦA SÀN MT5 THỨ 2 (EXNESS)
MT5_ALT_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

# Định dạng: "Tên_Symbol_Của_Sàn": "Tạo_Ra_File_Tên_Giống_Hệt_Binance"
SYMBOL_MAP = {
    # 1. Target Chính
    "LTCUSDm": "ltc_usd_mt5_1m_2026",
    "USOILm": "usoil_usd_mt5_1m_2026",
    
    # 2. Crypto inputs
    "BTCUSDm": "btc_usd_mt5_1m_2026",
    "ETHUSDm": "eth_usd_mt5_1m_2026",
    "SOLUSDm": "sol_usd_mt5_1m_2026",
    "BNBUSDm": "bnb_usd_mt5_1m_2026",
    "XRPUSDm": "xrp_usd_mt5_1m_2026",
    "BCHUSDm": "bch_usd_mt5_1m_2026",
    "ADAUSDm": "ada_usd_mt5_1m_2026",
    
    # 3. Macro inputs (Vĩ Mô)
    "DXYm": "dxy_mt5_1m_2026",
    "US30m": "us30_mt5_1m_2026",
    "US500m": "us500_mt5_1m_2026",
    "USTECm": "ustec_mt5_1m_2026",
    "JP225m": "jp225_mt5_1m_2026",
    
    # (AVAX không có trên sàn này, bỏ qua)
}

# =========================================================================================

def print_log(msg):
    """In ra Terminal mà không bị giữ Buffer"""
    print(msg, flush=True)

def fetch_historical_rates(symbol, timeframe, limit=1000):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)
    if rates is None or len(rates) == 0:
        return None
        
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
    
    print_log(f"Đang khởi động kết nối vào MT5 EXNESS tại: {MT5_ALT_PATH}")
    
    if not mt5.initialize(path=MT5_ALT_PATH):
        print_log("Lỗi: Khởi tạo thư viện MetaTrader5 thất bại!")
        print_log(f"Error code: {mt5.last_error()}")
        return
        
    print_log("Khởi tạo MT5 thành công. Phiên bản Terminal: " + str(mt5.version()))
    
    is_live = (len(sys.argv) > 1 and sys.argv[1] == "live")
    bars = 1440 if is_live else 500000 
    
    for mt5_symbol, file_suffix in SYMBOL_MAP.items():
        print_log(f"\n=> 🔄 Kéo lệnh tải nến 1 phút (M1) cho {mt5_symbol}...")
        
        selected = mt5.symbol_select(mt5_symbol, True)
        if not selected:
            print_log(f" ⚠️ CẢNH BÁO: Không tìm thấy mã {mt5_symbol} trong MT5 Exness.")
            print_log("  -> Bạn phải Bật mã này trong Market Watch (Ctrl+U) trước!")
            continue
            
        df = fetch_historical_rates(mt5_symbol, mt5.TIMEFRAME_M1, bars)
        
        if df is None:
            print_log(f" ❌ Lỗi: Không tải được lịch sử giá cho {mt5_symbol}.")
            continue
            
        print_log(f" ✔️ Tải xong: {len(df):,} nến. Bắt đầu lưu trữ...")
        
        output_file = os.path.join(data_path, f"{file_suffix}.parquet")
        
        if is_live and os.path.exists(output_file):
            try:
                existing_df = pd.read_parquet(output_file)
                combined_df = pd.concat([existing_df, df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df = combined_df.sort_index()
                combined_df.to_parquet(output_file)
                print_log(f" 💾 Đã ghép nối File: {output_file} (Tổng: {len(combined_df):,} nến)")
            except:
                df.to_parquet(output_file)
                print_log(f" 💾 Đã lưu File Đè: {output_file}")
        else:
            df.to_parquet(output_file)
            print_log(f" 💾 Đã lưu File Gốc: {output_file}")
        
    mt5.shutdown()
    print_log("\n HOÀN TẤT SAO LƯU TOÀN BỘ 21 MÃ TỪ EXNESS!")

if __name__ == "__main__":
    main()
