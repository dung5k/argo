import os
import sys
import time
import pandas as pd
import MetaTrader5 as mt5
from mt5_data_manager import MT5DataManager

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
        
        mt5.shutdown()
        if not mt5.initialize(path=path):
            print(f"Lỗi: Không thể khởi tạo MT5 tại {path}")
            continue
            
        continuous_config = manager.config.get("DATA_SOURCE", {}).get("CONTINUOUS_CONTRACTS", {}).get(req_m)
        
        df = None
        
        # Lấy Offset Time chuẩn từ mã đang Active
        selected_hint = mt5.symbol_select(found_sym, True)
        tick = mt5.symbol_info_tick(found_sym) if selected_hint else None
        offset_sec = (tick.time - int(time.time())) if (tick and tick.time > 0) else 0
        offset_hours = round(offset_sec / 3600)
        
        timeframe = mt5.TIMEFRAME_M1
        
        if continuous_config and not continuous_config.get("IS_CFD", False):
            print(f"🔄 Bắt đầu quy trình Cuốn Hợp Đồng (Stitching) cho {req_m} (Prefix: {continuous_config.get('PREFIX')})")
            months = continuous_config.get("CONTRACT_MONTHS", ["H", "M", "U", "Z"])
            prefix = continuous_config.get("PREFIX")
            invert_logic = continuous_config.get("INVERT_LOGIC", False)
            
            all_dfs = []
            for y in [24, 25, 26]:
                for m in months:
                    c_sym = f"{prefix}{m}{y}"
                    if mt5.symbol_select(c_sym, True):
                        rates = mt5.copy_rates_range(c_sym, timeframe, dt_start, dt_end)
                        if rates is not None and len(rates) > 0:
                            c_df = pd.DataFrame(rates)
                            # Nếu đây là Trái phiếu và yêu cầu Nghịch đảo (Tính Yield thủ công từ giá)
                            # Price = 100 - Yield (?) Thực ra Invert Logic chỉ đơn giản là Yield_Log_Ret = -Price_Log_Ret
                            # Nhưng vì chúng ta cần chuẩn dòng dữ liệu thô, tốt nhất cứ đảo ngược giá thô: e.g. 1/Price hoặc Max_Price - Price. 
                            # Tuy nhiên theo tiêu chuẩn ML, Mạng nơ-ron tự học được chiều âm dương. Chỉ cần Invert c_df nếu muốn.
                            # Mặc định cứ giữ nguyên Raw Giá đóng cửa.
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
        # Chỉ lưu các file tối quan trọng cho huấn luyện vào danh sách kéo về của Client
        required_list = [
            f"final_features_{target_prefix}.parquet",
            f"target_direction_{target_prefix}.parquet",
            "scaler.pkl"
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
    for fp in generated_files:
        sym_name = os.path.basename(fp).split("_mt5_")[0].upper()
        try:
            check_df = pd.read_parquet(fp)
            rows = len(check_df)
            cols = list(check_df.columns)
            
            # Kiểm tra khoảng thời gian
            t_min = check_df.index.min()
            t_max = check_df.index.max()
            
            # Kiểm tra giá trị NaN
            null_pct = check_df.isnull().mean().max() * 100
            
            # Kiểm tra real_volume
            rv_col = 'real_volume'
            has_real_vol = rv_col in cols
            real_vol_sum = check_df[rv_col].sum() if has_real_vol else 0
            real_vol_status = (
                f"✅ {int(real_vol_sum):,}" if (has_real_vol and real_vol_sum > 0)
                else (f"⚠️  =0 (Forex CFD - bình thường)" if has_real_vol else "❌ Không có cột")
            )
            
            # Kiểm tra gap lớn (nhiều hơn 60 phút liên tiếp không có nến)
            if len(check_df) > 1:
                time_diffs = check_df.index.to_series().diff().dt.total_seconds() / 60
                max_gap_min = time_diffs.max()
                gap_status = f"⚠️  {max_gap_min:.0f} phút" if max_gap_min > 120 else f"✅ {max_gap_min:.0f} phút"
            else:
                max_gap_min = 0
                gap_status = "❓ Không đủ dữ liệu"
            
            # Tổng trạng thái
            status = "✅ OK" if (rows >= 10000 and null_pct < 20 and max_gap_min < 1440) else "⚠️  CẦN KIỂM TRA"
            if rows < 1000:
                status = "❌ THIẾU DỮ LIỆU NGHIÊM TRỌNG"
                all_ok = False
            
            print(f"\n[{sym_name}] {status}")
            print(f"  📅 Từ: {t_min} → {t_max}")
            print(f"  📈 Số nến M1: {rows:,}")
            print(f"  📊 Cột dữ liệu: {cols}")
            print(f"  🔢 real_volume tổng: {real_vol_status}")
            print(f"  ⏱️  Gap lớn nhất: {gap_status}")
            print(f"  🚫 NaN tối đa: {null_pct:.1f}%")
            
        except Exception as e:
            print(f"\n[{sym_name}] ❌ LỖI ĐỌC FILE: {e}")
            all_ok = False
    
    print("\n" + "="*60)
    print(f"📝 TỔNG KẾT: {'✅ TẤT CẢ DỮ LIỆU HỢP LỆ' if all_ok else '⚠️  CÓ VẤN ĐỀ CẦN XEM XÉT'}")
    print(f"   Tổng số file đã đồng bộ: {len(generated_files)}")
    print("="*60)
    
    # --- BƯỚC UPLOAD LÊN HUGGING FACE ---
    import json
    tg_config_path = os.path.join(base_path, "tg_config.json")
    hf_token = None
    repo_id = None
    if os.path.exists(tg_config_path):
        with open(tg_config_path, "r", encoding="utf-8") as f:
            try:
                tg_config = json.load(f)
                hf_token = tg_config.get("hf_token")
                repo_id = tg_config.get("hf_repo_id")
            except: pass
            
    hf_config = manager.config.get("HF_CLOUD", {})
    if not repo_id:
        repo_id = hf_config.get("DATASET_REPO")
    if not hf_token:
        token_env = hf_config.get("HF_API_TOKEN_ENV_VAR", "HF_TOKEN")
        hf_token = os.environ.get(token_env)
    
    if repo_id:
        if not hf_token:
            print(f"⚠️ Cảnh báo: Đã cấu hình HF_CLOUD nhưng không tìm thấy biến môi trường {token_env}. Bỏ qua bước đẩy lên Cloud.")
        else:
            try:
                from huggingface_hub import HfApi
                print(f"☁️ Tích hợp Hugging Face Hub (Repo: {repo_id})...")
                api = HfApi()
                
                # Check repo format exists
                try:
                    api.repo_info(repo_id=repo_id, repo_type="dataset", token=hf_token)
                except Exception as e:
                    print(f"Tạo mới Dataset Repo {repo_id}...")
                    api.create_repo(repo_id=repo_id, repo_type="dataset", private=True, token=hf_token)
                    
                for f_path in generated_files:
                    f_name = os.path.basename(f_path)
                    print(f" 🚀 Đang tải {f_name} lên Hub...")
                    api.upload_file(
                        path_or_fileobj=f_path,
                        path_in_repo=f"data/{f_name}",
                        repo_id=repo_id,
                        repo_type="dataset",
                        token=hf_token
                    )
                    
                    # (Optional) Xoá file Local sau khi up
                    if not hf_config.get("KEEP_LOCAL_PARQUET", False):
                        try:
                            os.remove(f_path)
                            print(f"    🗑️ Đã xoá file tạm local: {f_name}")
                        except Exception as rm_err:
                            print(f"    ⚠️ Lỗi khi xoá file {f_name}: {rm_err}")
                print("🌟 SUCCESS: Đã đẩy toàn bộ Dataset M1 lên Hugging Face Cloud thành công!")
            except ImportError:
                print("Lỗi: Không tìm thấy thư viện `huggingface_hub`. Vui lòng pip install huggingface-hub")
            except Exception as e:
                print(f"❌ Lỗi trong quá trình upload HF: {e}")
    else:
        print("Trạng thái: Hoạt động chế độ OFFLINE. (Không upload HF).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.argv[1] = sys.argv[1] # Keep it intact for sync_all_history to read
    sync_all_history()
