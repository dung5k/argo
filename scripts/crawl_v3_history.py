import os
import sys
import json
import time
from datetime import datetime
import pytz
import traceback
import pandas as pd
import MetaTrader5 as mt5

def print_log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def fetch_historical_rates(symbol, tf_str, start_dt, end_dt):
    """
    Kéo lịch sử MT5 dựa theo khoảng thời gian thực với Múi giờ chuẩn (UTC).
    """
    mt5_tf = mt5.TIMEFRAME_M1
    if tf_str == "M5": mt5_tf = mt5.TIMEFRAME_M5
    elif tf_str == "M15": mt5_tf = mt5.TIMEFRAME_M15
    elif tf_str == "H1": mt5_tf = mt5.TIMEFRAME_H1
    
    start_utc = int(start_dt.timestamp())
    end_utc = int(end_dt.timestamp())
    
    rates = mt5.copy_rates_range(symbol, mt5_tf, start_utc, end_utc)
    if rates is None or len(rates) == 0:
        # Nhượng bộ, thử tìm bằng symbol cắm cờ
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df.set_index('time', inplace=True)
    return df

def get_actual_mt5_symbol(symbol, cont_contracts):
    if symbol in cont_contracts:
        prefix = cont_contracts[symbol].get("PREFIX", "")
        if "VIX" in prefix:
            syms = mt5.symbols_get()
            vix = [s.name for s in syms if "VIX" in s.name] if syms else []
            return vix[0] if vix else "VIX_K6"
        if "UST10Y" in prefix:
            syms = mt5.symbols_get()
            ust = [s.name for s in syms if "UST10Y" in s.name] if syms else []
            return ust[0] if ust else "UST10Y_M6"
        if cont_contracts[symbol].get("IS_CFD"):
            return prefix
    return symbol

def main(config_file):
    print_log(f"🚀 BẮT ĐẦU CÀO DỮ LIỆU MT5 CHO V3 TỪ CONFIG: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    train_cfg = config.get("TRAINING", {})
    start_date = train_cfg.get("TRAIN_START", "2026-02-01")
    end_date = train_cfg.get("VAL_END", "2026-04-10")
    
    # Ép kiểu datetime (UTC)
    timezone = pytz.UTC
    start_dt = timezone.localize(datetime.strptime(f"{start_date} 00:00:00", "%Y-%m-%d %H:%M:%S"))
    end_dt = timezone.localize(datetime.strptime(f"{end_date} 23:59:59", "%Y-%m-%d %H:%M:%S"))
    
    # Extract config
    data_src = config.get("DATA_SOURCE", {})
    routing = data_src.get("ROUTING", {})
    brokers_map = data_src.get("BROKERS", {})
    cont_contracts = data_src.get("CONTINUOUS_CONTRACTS", {})
    required_macros = config.get("FEATURE_ENGINEERING", {}).get("MACRO_FEATURES", {})
    
    if not routing:
        routing = {config.get("TARGET_SYMBOL"): "EXNESS"}
        
    history_dir = os.path.join("data", "history")
    os.makedirs(history_dir, exist_ok=True)
    
    # Nhóm mã theo broker
    broker_syms = {}
    for sym, brk in routing.items():
        # Kiểm tra nếu mã là bắt buộc trong MACRO_FEATURES hoặc là TARGET
        sym_clean = sym.replace('m', '').upper()
        if sym_clean not in [k.replace('m', '').upper() for k in required_macros.keys()] and "XAUUSD" not in sym_clean:
            continue
            
        brk_path = brokers_map.get(brk, brokers_map.get("DEFAULT"))
        if brk_path not in broker_syms: broker_syms[brk_path] = []
        broker_syms[brk_path].append(sym)

    total_candles = 0
    missing_critical = []

    # Quét từng broker
    for path, sym_list in broker_syms.items():
        print_log(f"--- Đang khởi động MT5 tại: {path} ---")
        if not mt5.initialize(path):
            print_log(f"❌ Lỗi: Khởi tạo MT5 thất bại tại {path}! Error: {mt5.last_error()}")
            # MT5 không bật được, auto fail toàn bộ của sàn đó
            missing_critical.extend(sym_list)
            continue
            
        print_log("✅ Khởi tạo MT5 thành công. Bắt đầu phiên kéo dữ liệu...")
        for symbol in sym_list:
            mt5_target = get_actual_mt5_symbol(symbol, cont_contracts)
            print_log(f"=> 🔄 Đang cào M1 cho {symbol} (MT5 Name: {mt5_target})...")
            
            df = fetch_historical_rates(mt5_target, "M1", start_dt, end_dt)
            if df is not None and not df.empty:
                # Format dataframe chuẩn cho V2/V3 loader
                df.rename(columns={'tick_volume': 'volume'}, inplace=True)
                df_save = df[['open', 'high', 'low', 'close', 'volume', 'real_volume', 'spread']].copy()
                
                # Lưu file chuẩn hóa: VD "USDCHF_MT5_1M_2026.parquet"
                sym_clean_filename = symbol.upper().replace('M', '')
                out_path = os.path.join(history_dir, f"{sym_clean_filename}_MT5_1M_2026.parquet")
                
                df_save.to_parquet(out_path)
                total_candles += len(df)
                print_log(f"  ✔️ Tải xong: {len(df)} nến. 💾 Đã lưu: {out_path}")
            else:
                print_log(f"  ❌ MT5 KHÔNG TRẢ VỀ DỮ LIỆU NÀO CHO {symbol}!")
                missing_critical.append(symbol)
                
        mt5.shutdown()
        
    print_log(f"🎉 HOÀN TẤT VÒNG QUÉT. TỔNG SỐ NẾN LẤY VỀ: {total_candles}")
    
    if missing_critical:
        print_log("\n" + "="*50)
        print_log("💥 LỖI NGHIÊM TRỌNG TỪ QUY ƯỚC STRICT WARNING 💥")
        print_log(f"Các mã Vĩ mô bắt buộc sau bị THIẾU TOÀN BỘ: {missing_critical}")
        print_log("❌ HỆ THỐNG HUỶ TOÀN BỘ TIẾN TRÌNH VÌ THIẾU TÀI NGUYÊN BẮT BUỘC!")
        print_log("="*50 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main("data/bot_config_xau_ny_v3.json")
