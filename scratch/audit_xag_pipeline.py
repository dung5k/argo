import os
import sys
import json
import pandas as pd
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.bot_v3.data_processor_v3 import V3DataProcessor

def audit_xag():
    print("=== BẮT ĐẦU KIỂM TRA ĐỘNG LỰC TENSOR XAG ===")
    config_path = os.path.join(_ROOT, "bot_config_xag.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    cfg_id = config.get("CONFIG_ID", "CFG_XAG_NY_V5")
    
    # Fake raw data 100 nến
    print("1. Tạo dữ liệu thô (Fake Data)")
    dates = pd.date_range(start="2026-05-09 00:00:00", periods=100, freq="1T")
    df_raw = pd.DataFrame({'timestamp': dates})
    df_raw.set_index('timestamp', inplace=True)
    
    # Main symbol
    df_raw['XAGUSD_open'] = np.random.uniform(28.0, 28.5, 100)
    df_raw['XAGUSD_high'] = df_raw['XAGUSD_open'] + 0.1
    df_raw['XAGUSD_low'] = df_raw['XAGUSD_open'] - 0.1
    df_raw['XAGUSD_close'] = df_raw['XAGUSD_open'] + np.random.uniform(-0.05, 0.05, 100)
    df_raw['XAGUSD_volume'] = np.random.randint(100, 1000, 100)
    df_raw['XAGUSD_real_volume'] = df_raw['XAGUSD_volume']
    
    # Macro
    df_raw['XAUUSD_open'] = np.random.uniform(2300, 2310, 100)
    df_raw['XAUUSD_high'] = df_raw['XAUUSD_open'] + 5
    df_raw['XAUUSD_low'] = df_raw['XAUUSD_open'] - 5
    df_raw['XAUUSD_close'] = df_raw['XAUUSD_open'] + np.random.uniform(-2, 2, 100)
    df_raw['XAUUSD_volume'] = np.random.randint(100, 1000, 100)
    df_raw['XAUUSD_real_volume'] = df_raw['XAUUSD_volume']
    
    # Time
    df_raw['hour_sin'] = np.sin(2 * np.pi * dates.hour / 24)
    df_raw['hour_cos'] = np.cos(2 * np.pi * dates.hour / 24)
    df_raw['dow_sin'] = np.sin(2 * np.pi * dates.dayofweek / 7)
    df_raw['dow_cos'] = np.cos(2 * np.pi * dates.dayofweek / 7)

    scaler_path = os.path.join(_ROOT, "data", f"scaler_{cfg_id}.pkl")
    
    import pickle
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    if isinstance(scaler, dict):
        print(f"Scaler is dict. Keys: {scaler.keys()}")
        if 'column_order' in scaler:
            dp_feats = scaler['column_order']
            print(f"Scaler expected features ({len(dp_feats)}): {dp_feats}")
        else:
            dp_feats = list(config["FEATURE_ENGINEERING"].get("MACRO_FEATURES", {}).keys()) # Fallback
    else:
        dp_feats = list(scaler.feature_names_in_)
        print(f"Scaler expected features ({len(dp_feats)}): {dp_feats}")
        
    processor = V3DataProcessor(
        scaler_path=scaler_path,
        inference_feats=dp_feats,
        window_size=config["FEATURE_ENGINEERING"]["WINDOW_SIZE"],
        config=config,
        log_callback=print,
        model_input_dim=config["TRAINING"].get("D_MODEL", 64) # Not the exact shape, but let's see
    )
    
    print("\n2. Chạy ingest_and_scale()")
    try:
        tensor = processor.ingest_and_scale(df_raw)
        print(f"✅ Thành công! Tensor shape: {tensor.shape}")
        
        # Access processor internals
        live_cols = processor._last_final_cols if hasattr(processor, '_last_final_cols') else None
        if live_cols is None:
            print("Không thể lấy cột cuối cùng, cần sửa ingest_and_scale() lưu lại.")
    except Exception as e:
        print(f"❌ LỖI TRONG PIPELINE: {e}")

if __name__ == "__main__":
    audit_xag()
