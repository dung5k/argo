import os
import sys
import numpy as np
import pandas as pd
import json

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.bot_v3.data_processor_v3 import V3DataProcessor
from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3

def test_data_integrity():
    print("🚀 BẮT ĐẦU KIỂM TRA ĐỘ TOÀN VẸN DỮ LIỆU (DATA INTEGRITY TEST)")
    
    cfg_id = "CFG_LTC_ASIAN_V3_5"
    config_path = os.path.join(_ROOT, "workspaces", "CFG_LTC_ASIAN_V3_5", "base_config.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    scaler_path = os.path.join(_ROOT, "workspaces", "CFG_LTC_ASIAN_V3_5", "runs", "run_20260422_143008_v3", "brains", "scaler_CFG_LTC_ASIAN_V3_5.pkl")
    if not os.path.exists(scaler_path):
         # Try global data folder
         scaler_path = os.path.join(_ROOT, "data", "scaler_CFG_LTC_ASIAN_V3_5.pkl")
        
    print(f"Sử dụng Config: {cfg_id}")
    print(f"Scaler path: {scaler_path}")
    
    # Giả lập đọc 1500 nến cuối cùng của dữ liệu Raw
    raw_dir = config.get('DATA_SOURCE', {}).get('RAW_LOCAL_DIR', 'data/history')
    if not os.path.exists(os.path.join(_ROOT, raw_dir)):
        print(f"⚠️ Thư mục raw_dir ({raw_dir}) không tồn tại, fallback về data/history")
        raw_dir = 'data/history'
        
    df_raw = None
    try:
        if config.get("FEATURE_ENGINEERING", {}).get("CRYPTO_MODE", False):
            fe_cfg = config.get("FEATURE_ENGINEERING", {})
            all_syms = {config.get('TARGET_SYMBOL', '').upper().replace('M', '')}
            all_syms.add(config.get('TARGET_SYMBOL', '').upper())
            for sym in fe_cfg.get('MACRO_FEATURES', {}).keys():
                all_syms.add(sym.upper())
                
            df_list = []
            for fname in os.listdir(os.path.join(_ROOT, raw_dir)):
                if not fname.endswith('.parquet'): continue
                if '_MT5_' in fname: sym_raw = fname.split('_MT5_')[0].upper()
                elif '_BINANCE_' in fname: sym_raw = fname.split('_BINANCE_')[0].upper()
                else: sym_raw = fname.split('_')[0].upper()
                
                matched = any(sym_raw == s.upper() or sym_raw == s.upper().rstrip('M') for s in all_syms)
                if not matched: continue
                
                df_sym = pd.read_parquet(os.path.join(_ROOT, raw_dir, fname))
                if 'time' in df_sym.columns: df_sym.set_index('time', inplace=True)
                if df_sym.index.tz is None: df_sym.index = df_sym.index.tz_localize('UTC')
                
                rename_map = {c: f"{sym_raw}_{c}" for c in df_sym.columns}
                df_sym = df_sym.rename(columns=rename_map)
                df_list.append(df_sym)
                print(f"Đọc: {fname} -> prefix={sym_raw}")
                
            if df_list:
                df_raw = df_list[0].copy()
                for df_next in df_list[1:]:
                    df_raw = df_raw.join(df_next, how='outer')
                df_raw = df_raw.sort_index()
                df_raw = df_raw.ffill(limit=5)
        else:
            from src.core.feature_engineering import load_and_align_data
            df_raw = load_and_align_data(os.path.join(_ROOT, raw_dir))
    except Exception as e:
        print(f"❌ Không tải được raw data: {e}")
        return
        
    if df_raw is None or len(df_raw) < 1500:
        print("❌ Dữ liệu raw không đủ.")
        return
        
    if 'time' in df_raw.columns:
        df_raw.set_index('time', inplace=True)
        
    # Chọn 1500 nến của một ngày (vd: 08/05/2026)
    df_raw = df_raw.loc[:'2026-05-08 15:00:00']
    
    if len(df_raw) < 1500:
        print("❌ Dữ liệu raw không đủ mốc thời gian.")
        return
        
    df_live_input = df_raw.iloc[-1500:].copy()
    target_time = df_live_input.index[-1]
    print(f"Target Time (Mốc thời gian so khớp): {target_time}")
    
    # Load scaler trước để lấy col_order
    import pickle
    with open(scaler_path, "rb") as f:
        scaler_data = pickle.load(f)
    if isinstance(scaler_data, dict):
        col_order = scaler_data.get("column_order", ["mock_str"])
    else:
        # Fallback to feature_names_in_ if it's a raw scaler
        col_order = list(scaler_data.feature_names_in_) if hasattr(scaler_data, "feature_names_in_") else ["mock_str"]
    
    # 1. Chạy luồng LIVE
    processor = V3DataProcessor(
        scaler_path=scaler_path,
        inference_feats=col_order,
        window_size=config['FEATURE_ENGINEERING'].get('WINDOW_SIZE', 60),
        config=config,
        log_callback=lambda x: None
    )
    
    tensor_live, err = processor.ingest_and_scale(df_live_input)
    if err:
        print(f"❌ Lỗi Live Pipeline: {err}")
        return
        
    # 2. Chạy luồng TRAIN (trên toàn bộ df_raw để mô phỏng lúc train)
    fe = FeatureEngineeringV3(
        target_prefix=config['TARGET_PREFIX'],
        macro_features=config['FEATURE_ENGINEERING'].get('MACRO_FEATURES', {}),
        crypto_mode=config['FEATURE_ENGINEERING'].get('CRYPTO_MODE', False)
    )
    
    df_features_train = fe.process_features(df_raw)
    
    # Dùng scaler cũ transform
    import pickle
    with open(scaler_path, "rb") as f:
        scaler_data = pickle.load(f)
    
    if isinstance(scaler_data, dict):
        fe.scaler = scaler_data["scaler"]
    else:
        fe.scaler = scaler_data
        
    fe.is_fitted = True
    
    print("\n--- DEBUG SCALER PARAMS ---")
    print(f"Train Scaler id: {id(fe.scaler)}")
    print(f"Live Scaler id: {id(processor.fe.scaler)}")
    print(f"Train Scaler center_[0:5]: {fe.scaler.center_[:5]}")
    print(f"Live Scaler center_[0:5]: {processor.fe.scaler.center_[:5]}")
    print(f"Train Scaler scale_[0:5]: {fe.scaler.scale_[:5]}")
    print(f"Live Scaler scale_[0:5]: {processor.fe.scaler.scale_[:5]}")
    print("---------------------------\n")
    
    df_scaled_train = fe.transform_scaler(df_features_train)
    
    # 3. Lấy Raw Feature của Live
    df_features_live = processor.fe.process_features(df_live_input)
    
    # Lấy row cuối cùng tương ứng với mốc thời gian
    row_live = df_live_input.iloc[[-1]]
    
    try:
        row_train = df_scaled_train.loc[target_time]
    except KeyError:
        print("❌ Không tìm thấy target_time trong tập train.")
        return
        
    # Kiểm tra Column Order của Live
    # final_cols trong DataProcessorV3 chính là thứ tự của tensor_live!
    # Vì tensor_live được tạo ra từ final_df.values
    # final_df = scaled_df[final_cols]
    
    # Để chắc chắn, ta xem lại logic DataProcessorV3: nếu saved_column_order là None
    # thì final_cols = list(scaled_df.columns). 
    # Ta lấy scaled_df.columns từ processor.
    live_cols = list(df_features_live.columns)
    if "volume" not in live_cols:
        vol_cols = [c for c in live_cols if 'volume' in c.lower()]
        if vol_cols: live_cols.append("volume")
        if "spread" not in live_cols: live_cols.append("spread")
        
    print(f"\nLive Cols Length: {len(live_cols)}")
    print(f"Col Order Length: {len(col_order)}")
    print(f"tensor_live.shape: {tensor_live.shape}")
    print(f"Col Order == Live Cols? {col_order == live_cols}")
    if col_order != live_cols:
        print("SỰ SAI LỆCH THỨ TỰ CỘT:")
        for i in range(min(len(col_order), len(live_cols))):
            if col_order[i] != live_cols[i]:
                print(f"Idx {i}: col_order={col_order[i]} vs live_cols={live_cols[i]}")
                break

    # Trích xuất dữ liệu tensor
    live_vals = tensor_live[0, -1, :].numpy()
    
    # Sử dụng col_order đã lấy từ trên thay vì lấy lại
    if not col_order or col_order == ["mock_str"]:
        col_order = list(df_scaled_train.columns)
        
    train_vals = []
    for col in col_order:
        if col in df_scaled_train.columns:
            train_vals.append(df_scaled_train.loc[target_time, col])
        else:
            train_vals.append(0.0)
            
    train_vals = np.array(train_vals)

    
    print("\n📊 BẢNG SO KHỚP CÁC TÍNH NĂNG (FEATURE DIFF):")
    print(f"{'Feature Name':<30} | {'Live Raw':<12} | {'Train Raw':<12} | {'Live Scaled':<12} | {'Train Scaled':<12} | {'Scaled Diff'}")
    print("-" * 100)
    
    diff_count = 0
    max_diff = 0
    for idx, col in enumerate(col_order):
        l_v = live_vals[idx] if idx < len(live_vals) else 0.0
        t_v = train_vals[idx] if idx < len(train_vals) else 0.0
        
        l_raw = df_features_live.loc[target_time, col] if col in df_features_live.columns else 0.0
        t_raw = df_features_train.loc[target_time, col] if col in df_features_train.columns else 0.0
        
        diff = abs(l_v - t_v)
        if diff > max_diff: max_diff = diff
            
        if diff > 0.001 or abs(l_raw - t_raw) > 0.001:
            diff_count += 1
            print(f"{col:<30} | {l_raw:>12.6f} | {t_raw:>12.6f} | {l_v:>12.6f} | {t_v:>12.6f} | {diff:>10.6f} ⚠️")
            
    print("-" * 100)
    print(f"Kết quả: TÌM THẤY {diff_count} CỘT LỆCH PHA! (Max Diff: {max_diff:.6f})")

if __name__ == "__main__":
    test_data_integrity()
