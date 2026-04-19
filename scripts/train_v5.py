import os
import sys
import argparse
import json
import pickle
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.training_v5.preprocessor_v5 import PreprocessorV5
from src.training_v5.xgb_model import SelectiveXGBoost
from src.core_v3.feature_engineering_v3 import LabelingV3
from sklearn.model_selection import train_test_split

def load_parquet_crypto(raw_dir: str, target_sym: str, target_source: str, leader_assets: dict):
    df_list = []
    loaded_syms = set()
    
    def _read_asset(sym, source):
        if sym in loaded_syms: return None
        for fname in os.listdir(raw_dir):
            if not fname.endswith('.parquet'): continue
            if fname.startswith(sym) and source.upper() in fname:
                df_sym = pd.read_parquet(os.path.join(raw_dir, fname))
                if 'time' in df_sym.columns:
                    df_sym.set_index('time', inplace=True)
                if df_sym.index.tz is None:
                    df_sym.index = df_sym.index.tz_localize('UTC')
                    
                rename_map = {c: f"{sym}_{c}" for c in df_sym.columns}
                df_sym = df_sym.rename(columns=rename_map)
                print(f"  + Đọc: {fname} -> Nguồn: {source} ({len(df_sym)} nến)")
                loaded_syms.add(sym)
                return df_sym
        print(f"  ❌ CẢNH BÁO: Không tìm thấy data cho {sym} từ {source}")
        return None

    df_tgt = _read_asset(target_sym, target_source)
    if df_tgt is not None: df_list.append(df_tgt)
    
    for sym, cfg in leader_assets.items():
        df_macro = _read_asset(sym, cfg.get("source", "MT5"))
        if df_macro is not None: df_list.append(df_macro)
        
    if not df_list:
        raise FileNotFoundError(f"Không load được Parquet Data tại {raw_dir}")
        
    df_raw = df_list[0].copy()
    for df_next in df_list[1:]:
        df_raw = df_raw.join(df_next, how='outer')
        
    df_raw = df_raw.sort_index().ffill(limit=5)
    return df_raw

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    cfg_id = config.get("CONFIG_ID", "CFG_V5_UNKNOWN")
    out_dir = os.path.join("data", cfg_id)
    os.makedirs(out_dir, exist_ok=True)
    
    raw_dir = config.get("DATA_SOURCE", {}).get("RAW_LOCAL_DIR", "data/history")
    target_prefix = config.get("TARGET_PREFIX", "LTC")
    target_symbol = config.get("TARGET_SYMBOL", "LTCUSDT")
    target_source = config.get("TARGET_SOURCE", "BINANCE")
    
    engine_cfg = config.get("V5_XGB_ENGINE", {})
    leader_assets = engine_cfg.get("LEADER_ASSETS", {})
    
    print(f"🔥 BẮT ĐẦU XÂY DỰNG MODULE SELECTIVE V5 CHO: {cfg_id}")
    
    print("\n[1] Đọc dữ liệu lịch sử...")
    df_raw = load_parquet_crypto(raw_dir, target_symbol, target_source, leader_assets)
    print(f"  ✅ df_raw: {df_raw.shape}")
    
    # Chuẩn bị Macro Veto (Test Phase)
    close_col = f"{target_symbol}_close"
    if engine_cfg.get("MACRO_VETO", False) and close_col in df_raw.columns:
        ema_12000 = df_raw[close_col].ewm(span=12000, adjust=False, min_periods=1200).mean()
        macro_dist = ((df_raw[close_col] - ema_12000) / ema_12000) * 100.0
    else:
        macro_dist = pd.Series(0, index=df_raw.index)
    
    print("\n[2] Tiền xử lý (PreprocessorV5: Flatten Window)...")
    prep = PreprocessorV5(config)
    X_features, valid_indices = prep.fit_transform(df_raw)
    print(f"  ✅ X_features shape: {X_features.shape}")
    
    with open(os.path.join(out_dir, "preprocessor.pkl"), "wb") as f:
        pickle.dump(prep, f)
        
    print("\n[3] Gắn nhãn Triple Barrier...")
    live_cfg = config.get("LIVE_BOT", {})
    labeler = LabelingV3(
        max_hold_bars=live_cfg.get("MAX_HOLD_BARS", 10),
        label_mode=live_cfg.get("LABEL_MODE", "pct"),
        tp_pct=live_cfg.get("TP_PCT", 0.005),
        sl_pct=live_cfg.get("SL_PCT", 0.005),
        pip_size=live_cfg.get("PIP_SIZE", 0.01)
    )
    
    actual_open = f"{target_symbol}_open" if f"{target_symbol}_open" in df_raw.columns else f"{target_prefix}USDT_open"
    actual_high = f"{target_symbol}_high" if f"{target_symbol}_high" in df_raw.columns else f"{target_prefix}USDT_high"
    actual_low = f"{target_symbol}_low" if f"{target_symbol}_low" in df_raw.columns else f"{target_prefix}USDT_low"
    
    targets_all = labeler.apply_triple_barrier(df_raw, actual_open, actual_high, actual_low)
    labels = targets_all.loc[valid_indices].values
    macros = macro_dist.loc[valid_indices].values
    
    # Tách Test Set theo Chronological
    # 80% train, 20% test (OOT)
    train_size = int(len(X_features) * 0.8)
    X_train, X_test = X_features[:train_size], X_features[train_size:]
    y_train, y_test = labels[:train_size], labels[train_size:]
    indices_test = valid_indices[train_size:]
    macro_test = macros[train_size:]
    
    print(f"  Dữ liệu Train: {X_train.shape[0]} nến")
    print(f"  Dữ liệu Test : {X_test.shape[0]} nến")
    
    # Tách Validation cho XGB Early Stopping (10% của Train)
    X_t, X_v, y_t, y_v = train_test_split(X_train, y_train, test_size=0.1, random_state=42)
    
    print("\n[4] Huấn luyện Cây quyết định (XGBoost)...")
    xgb_params = engine_cfg.get("XGB_PARAMS", {})
    model = SelectiveXGBoost(xgb_params)
    model.fit(X_t, y_t, X_v, y_v)
    
    model.save(os.path.join(out_dir, "xgb_model.json"))
    print("  ✅ Lưu Model XGBoost System!")
    
    test_file = os.path.join(out_dir, "test_v5.pkl")
    with open(test_file, 'wb') as f:
        pickle.dump({
            "X_test": X_test,
            "y_test": y_test,
            "indices_test": indices_test,
            "macro_test": macro_test
        }, f)
    print(f"  Lưu Test set -> {test_file}")
    print("\n🎉 Hoàn thành Train Pipeline V5!")

if __name__ == "__main__":
    main()
