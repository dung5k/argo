import os
import sys
import time
import pandas as pd
import MetaTrader5 as mt5
from mt5_data_manager import MT5DataManager

def sync_all_history():
    print("🚀 BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU LỊCH SỬ TỪ CẤU HÌNH LIVE (UNIFIED CONFIG) 🚀")
    
    # 1. Khởi tạo Data Manager để lấy Router Map chuẩn gốc
    manager = MT5DataManager(log_callback=print, target_sym="XAUUSD")
    manager.scan_terminals_and_map()
    
    if not manager.GLOBAL_MT5_ROUTER_MAP:
        print("❌ Lỗi: Không thể map được bất kỳ mã nào từ cấu hình MT5!")
        return
        
    router = manager.GLOBAL_MT5_ROUTER_MAP
    hints = manager.IN_MEMORY_SYMBOL_HINT
    
    bars = 1000000
    
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_path, "data")
    os.makedirs(data_path, exist_ok=True)
    
    for req_m, path in router.items():
        found_sym = hints.get(req_m, req_m)
        print(f"\n{'-'*50}")
        print(f"📥 Đang lấy lịch sử mã: {req_m} (Khớp trên sàn: {found_sym}) từ {path}...")
        
        mt5.shutdown()
        if not mt5.initialize(path=path):
            print(f"Lỗi: Không thể khởi tạo MT5 tại {path}")
            continue
            
        selected = mt5.symbol_select(found_sym, True)
        if not selected:
            print(f"Lỗi: Không tìm thấy mã {found_sym} trong MT5 này.")
            continue
            
        timeframe = mt5.TIMEFRAME_M1
        rates = mt5.copy_rates_from_pos(found_sym, timeframe, 0, bars)
        
        if rates is None or len(rates) == 0:
            print(f"⚠️ Lỗi: Không kéo được data cho {found_sym} (Terminal chưa load đủ dữ liệu?)")
            continue
            
        print(f"✅ Rút thành công {len(rates):,} nến (M1) cho {req_m}")
        
        # --- ĐỒNG BỘ MÚI GIỜ CHUẨN XÁC Y HỆT LIVE ---
        tick = mt5.symbol_info_tick(found_sym)
        offset_sec = (tick.time - int(time.time())) if (tick and tick.time > 0) else 0
        offset_hours = round(offset_sec / 3600)
        
        df = pd.DataFrame(rates)
        df['time'] = df['time'] - (offset_hours * 3600) # Ép phẳng về UTC 0
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        
        # Lọc bớt dư thừa nếu quá dài
        df = df[df.index >= pd.to_datetime("2025-01-01")]
        
        clean_req = req_m.replace('m', '').lower()
        file_path = os.path.join(data_path, f"{clean_req}_mt5_1m_2026.parquet")
        
        df.to_parquet(file_path)
        print(f"💾 Đã lưu Parquet thành công tại {file_path}")
        
    mt5.shutdown()
    print("\n🎉 HOÀN TẤT ĐỒNG BỘ TOÀN BỘ KHO LỊCH SỬ. SOURCE OF TRUTH LÀ ĐỒNG NHẤT!")

if __name__ == "__main__":
    sync_all_history()
