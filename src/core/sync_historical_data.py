import os
import sys
import time
import pandas as pd
from src.core.data_adapters import BinanceAdapter
import MetaTrader5 as mt5
from src.core.mt5_data_manager import MT5DataManager

def sync_all_history():
    print("🚀 BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU LỊCH SỬ TỪ CẤU HÌNH LIVE (UNIFIED CONFIG) 🚀")
    
    config_file = "data/bot_config_xau.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        
    # 1. Khởi tạo Data Manager để lấy Router Map chuẩn gốc
    manager = MT5DataManager(log_callback=print, target_sym="XAUUSD", config_path=config_file)
    manager.scan_terminals_and_map()
    
    if not manager.GLOBAL_MT5_ROUTER_MAP:
        print("❌ Lỗi: Không thể map được bất kỳ mã nào từ cấu hình MT5!")
        return
        
    manager.scan_terminals_and_map()
    # Lấy map MT5 Paths để query config. json
    router = manager.GLOBAL_MT5_ROUTER_MAP
    hints = manager.IN_MEMORY_SYMBOL_HINT
    
    t_config = manager.config.get("TRAINING", {})
    t_start_str = t_config.get("TRAIN_START", "2025-01-01")
    v_end_str = t_config.get("VAL_END", "2026-12-31")
    
    from datetime import datetime, timedelta
    dt_start = datetime.strptime(t_start_str, "%Y-%m-%d") - timedelta(days=2)
    dt_end = datetime.strptime(v_end_str, "%Y-%m-%d") + timedelta(days=2)
    date_suffix = f"{t_start_str.replace('-','')}_to_{v_end_str.replace('-','')}"
    
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_path, "data")
    os.makedirs(data_path, exist_ok=True)
    
    generated_files = []
    
    for req_m, path in router.items():
        found_sym = hints.get(req_m, req_m)
        print(f"\n{'-'*50}")
        print(f"📥 Đang lấy lịch sử mã: {req_m} (Khớp trên sàn: {found_sym}) từ {path}...")
        
        # --- XỬ LÝ SONG NGUỒN BINANCE ---
        if path == "BINANCE" or "BINANCE" in path:
            adapter = BinanceAdapter(log_callback=print)
            df = adapter.fetch_historical_data(found_sym, 'M1', t_start_str, v_end_str)
            if df is not None and not df.empty:
                clean_req = req_m.replace('m', '').lower()
                file_path = os.path.join(data_path, f"{clean_req}_mt5_1m_{date_suffix}.parquet")
                # Giữ nguyên suffix _mt5_ để FeatureEngineering có thể nhận dạng chuẩn
                df.to_parquet(file_path)
                print(f"💾 Đã lưu Parquet (BINANCE) thành công tại {file_path}")
                generated_files.append(file_path)
            else:
                print(f"⚠️ Lỗi: Không kéo được data cho {req_m} từ BINANCE")
            continue
            
        # --- XỬ LÝ KHỐI MT5 NHƯ DEFAULT ---
        mt5.shutdown()
        if not mt5.initialize(path=path):
            print(f"Lỗi: Không thể khởi tạo MT5 tại {path}")
            continue
            
        continuous_config = manager.config.get("DATA_SOURCE", {}).get("CONTINUOUS_CONTRACTS", {}).get(req_m)
        
        df = None
        
        # Lấy Offset Time chuẩn từ mã đang Active
        # Thử lần lượt: mã chính → EURUSD → USDJPY → mặc định 0
        _candidates_offset = [found_sym, "EURUSDm", "EURUSD", "USDJPYm", "USDJPY"]
        offset_hours = 0
        for _cand in _candidates_offset:
            if mt5.symbol_select(_cand, True):
                _tick = mt5.symbol_info_tick(_cand)
                if _tick and _tick.time > 0:
                    _diff = _tick.time - int(time.time())
                    if abs(_diff) < 14 * 3600:
                        offset_hours = round(_diff / 3600)
                        break
        
        timeframe = mt5.TIMEFRAME_M1
        
        if continuous_config and not continuous_config.get("IS_CFD", False):
            print(f"🔄 Bắt đầu quy trình Cuốn Hợp Đồng (Stitching) cho {req_m} (Prefix: {continuous_config.get('PREFIX')})")
            months = continuous_config.get("CONTRACT_MONTHS", ["H", "M", "U", "Z"])
            prefix = continuous_config.get("PREFIX")
            invert_logic = continuous_config.get("INVERT_LOGIC", False)
            
            all_dfs = []
            delta_days = (dt_end - dt_start).days + 3
            max_bars = delta_days * 24 * 60  # ~1440 nến M1/ngày
            for y in [24, 25, 26]:
                for m in months:
                    c_sym = f"{prefix}{m}{y}"
                    if mt5.symbol_select(c_sym, True):
                        # Dùng from_pos thay range để tránh lỗi timezone của MT5 server
                        rates = mt5.copy_rates_from_pos(c_sym, timeframe, 0, max_bars)
                        if rates is not None and len(rates) > 0:
                            c_df = pd.DataFrame(rates)
                            # Lọc theo khoảng thời gian sau khi chuẩn hoá về UTC
                            c_df['_dt'] = pd.to_datetime(c_df['time'] - offset_hours * 3600, unit='s')
                            c_df = c_df[(c_df['_dt'] >= pd.to_datetime(dt_start)) &
                                        (c_df['_dt'] <= pd.to_datetime(dt_end))]
                            if len(c_df) > 0:
                                c_df = c_df.drop(columns=['_dt'])
                                all_dfs.append(c_df)
                                print(f"  => Tải được {len(c_df):,} nến từ hợp đồng {c_sym}")
                            
            if all_dfs:
                df = pd.concat(all_dfs)
                df = df.sort_values(by='time').drop_duplicates(subset=['time'], keep='last')
                print(f"🔗 Ghép nối thành công tổ hợp đồng Tương lai. Tổng số nến: {len(df):,}")
            else:
                print(f"⚠️ Lỗi: Không thể kéo bất kỳ mảnh dữ liệu nào của {req_m}")
                continue
        else:
            selected = mt5.symbol_select(found_sym, True)
            if not selected:
                print(f"Lỗi: Không tìm thấy mã {found_sym} trong MT5 này.")
                continue
                
            rates = mt5.copy_rates_range(found_sym, timeframe, dt_start, dt_end)
            
            if rates is None or len(rates) == 0:
                print(f"⚠️ Lỗi: Không kéo được data cho {found_sym} (Terminal chưa load đủ dữ liệu?)")
                continue
                
            print(f"✅ Rút thành công {len(rates):,} nến (M1) cho {req_m}")
            df = pd.DataFrame(rates)
        
        # --- ĐỒNG BỘ MÚI GIỜ CHUẨN XÁC Y HỆT LIVE ---
        df['time'] = df['time'] - (offset_hours * 3600) # Ép phẳng về UTC 0
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        # === TRAINING-SERVING SYNC: Drop y hệt Live (mt5_data_manager.py) ===
        # - 'time': đã chuyển thành Index, time_log_ret vô nghĩa
        # - 'spread': không tin cậy trong parquet lịch sử, Live cũng không dùng
        # - 'real_volume': GIỮ LẠI vì GOLD/VIXY/Futures có real_volume thực sự có ý nghĩa
        df.drop(columns=['spread', 'time'], inplace=True, errors='ignore')
        
        # Lọc bớt dư thừa nếu quá dài
        df = df[(df.index >= pd.to_datetime(t_start_str)) & (df.index <= pd.to_datetime(v_end_str) + pd.Timedelta(days=1))]
        
        clean_req = req_m.replace('m', '').lower()
        file_path = os.path.join(data_path, f"{clean_req}_mt5_1m_{date_suffix}.parquet")
        
        df.to_parquet(file_path)
        print(f"💾 Đã lưu Parquet thành công tại {file_path}")
        generated_files.append(file_path)
        
    mt5.shutdown()
    
    # Ghi đè cấu hình Dataset Suffix vào bot_config tương ứng để module Train dùng
    config_path = os.path.join(base_path, config_file)
    if os.path.exists(config_path):
        import json
        with open(config_path, "r", encoding="utf-8") as f:
            cfg_data = json.load(f)
        
        if "DATA_SOURCE" not in cfg_data:
            cfg_data["DATA_SOURCE"] = {}
        cfg_data["DATA_SOURCE"]["DATASET_SUFFIX"] = date_suffix
        
        # Lưu Tên các File Parquet đã cào thành công để Client biết và không kéo rác
        if "HF_CLOUD" not in cfg_data:
            cfg_data["HF_CLOUD"] = {}
        
        target_prefix = cfg_data.get("TARGET_PREFIX", "XAUUSD").upper()
        config_id = cfg_data.get("CONFIG_ID", target_prefix)
        
        # Chỉ lưu các file tối quan trọng cho huấn luyện vào danh sách kéo về của Client
        required_list = [
            f"final_features_{config_id}.parquet",
            f"target_direction_{config_id}.parquet",
            f"scaler_{config_id}.pkl"
        ]
        
        cfg_data["HF_CLOUD"]["REQUIRED_PARQUETS"] = required_list
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, indent=4, ensure_ascii=False)
        print(f"🔧 Đã cập nhật DATASET_SUFFIX='{date_suffix}' và {len(required_list)} REQUIRED_PARQUETS (Bao gồm RAW & Final Features) vào {config_file}")

    print("\n🎉 HOÀN TẤT ĐỒNG BỘ TOÀN BỘ KHO LỊCH SỬ LOCAL.")

    # ============================================================
    # BÁO CÁO KIỂM TRA CHẤT LƯỢNG DỮ LIỆU SAU ĐỒNG BỘ
    # ============================================================
    print("\n" + "="*60)
    print("📊 BÁO CÁO KIỂM TRA CHẤT LƯỢNG DỮ LIỆU")
    print("="*60)
    
    all_ok = True
    
    # Phân loại báo cáo
    categories = {
        "KIM LOẠI (Metals)": ["XAUUSD", "XAGUSD", "XCUUSD", "XPTUSD", "XPDUSD"],
        "NGOẠI HỐI (Forex)": ["EURUSD", "USDJPY", "USDCAD", "USDCHF", "GBPUSD", "AUDUSD", "DXY"],
        "CHỨNG KHOÁN (Indices)": ["NASDAQ", "US500", "US30", "VIXY", "USTEC", "NASDAQ_100"],
        "NĂNG LƯỢNG (Energy)": ["USOIL", "XNGUSD", "UKOIL", "BRENT"],
        "TRÁI PHIẾU (Bonds)": ["US_10Y_YIELD", "Z10Y"],
        "TIỀN MÃ HÓA (Crypto)": ["BTCUSD", "ETHUSD"]
    }
    grouped_reports = {k: [] for k in categories}
    grouped_reports["KHÁC (Others)"] = []
    
    for fp in generated_files:
        sym_name = os.path.basename(fp).split("_mt5_")[0].upper()
        if sym_name == "NASDAQ": sym_name = "NASDAQ_100"
        
        # Determine category
        cat_found = "KHÁC (Others)"
        for cat, keywords in categories.items():
            if any(k in sym_name for k in keywords):
                cat_found = cat
                break
                
        try:
            check_df = pd.read_parquet(fp)
            rows = len(check_df)
            cols = list(check_df.columns)
            
            t_min = check_df.index.min()
            t_max = check_df.index.max()
            null_pct = check_df.isnull().mean().max() * 100
            
            rv_col = 'real_volume'
            has_real_vol = rv_col in cols
            real_vol_sum = check_df[rv_col].sum() if has_real_vol else 0
            real_vol_status = f"✅ {int(real_vol_sum):,}" if (has_real_vol and real_vol_sum > 0) else (f"⚠️ =0 (Forex CFD)" if has_real_vol else "❌ Không có")
            
            if len(check_df) > 1:
                time_diffs = check_df.index.to_series().diff().dt.total_seconds() / 60
                max_gap_min = time_diffs.max()
                gap_status = f"⚠️ {max_gap_min:.0f}p" if max_gap_min > 120 else f"✅ {max_gap_min:.0f}p"
            else:
                max_gap_min = 0
                gap_status = "❓ Thiếu data"
                
            status = "✅ OK" if (rows >= 10000 and null_pct < 20 and max_gap_min < 1440) else "⚠️ CẨN THẬN"
            if rows < 1000:
                status = "❌ THIẾU NGHIÊM TRỌNG"
                all_ok = False
                
            report_str = f"  [{sym_name:12s}] {status:15s} | Nến: {rows:<7,} | GapMax: {gap_status:8s} | T: {t_min.strftime('%m/%d')}->{t_max.strftime('%m/%d')} | Vol: {real_vol_status}"
            grouped_reports[cat_found].append(report_str)
            
        except Exception as e:
            grouped_reports[cat_found].append(f"  [{sym_name:12s}] ❌ LỖI ĐỌC FILE: {e}")
            all_ok = False
            
    for cat, reports in grouped_reports.items():
        if reports:
            print(f"\n[{cat}]")
            for r in reports:
                print(r)
    
    print("\n" + "="*60)
    print(f"📝 TỔNG KẾT: {'✅ TẤT CẢ DỮ LIỆU HỢP LỆ' if all_ok else '⚠️  CÓ VẤN ĐỀ CẦN XEM XÉT'}")
    print(f"   Tổng số file đã đồng bộ: {len(generated_files)}")
    print("="*60)
    
    # --- LƯU Ý UPLOAD CHUYỂN SANG GIAI ĐOẠN SAU ---
    print("\nLưu ý: Bạn cần chạy tiếp Feature Engineering để tạo file tổng hợp, sau đó dùng hf_sync.py push để tải lên đám mây!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.argv[1] = sys.argv[1] # Keep it intact for sync_all_history to read
    sync_all_history()
