import os
import sys
import torch
import pandas as pd
import numpy as np
import json
import joblib

# Setup paths
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.training_v3.model_v3 import AAMT_Model
from src.bot_v3.data_processor_v3 import V3DataProcessor

def test_recent_performance():
    run_id = "run_20260504_192200_v4_hour_lookback"
    workspace = "workspaces/CFG_LTC_ASIAN_V3_5"
    run_dir = os.path.join(workspace, "runs", run_id)
    results_dir = os.path.join(run_dir, "results")
    
    with open(os.path.join(results_dir, "config.json"), 'r') as f:
        config = json.load(f)
    
    scaler_run_path = os.path.join(run_dir, "data", "tensors", f"scaler_{config['CONFIG_ID']}.pkl")
    scaler_bundle = joblib.load(scaler_run_path)
    feature_order = scaler_bundle['column_order']
    
    target_sym = config['TARGET_SYMBOL']
    raw_dir = os.path.join(workspace, "data", "raw")
    df_target = pd.read_parquet(os.path.join(raw_dir, f"{target_sym}_BINANCE_1M_2026.parquet"))
    if df_target.index.name == 'time': df_target.index.name = 'timestamp'
    df_target.index = pd.to_datetime(df_target.index)
    recent_df = df_target.loc['2026-04-20':'2026-04-21'].copy()
    
    target_prefix = config.get('TARGET_PREFIX', 'LTCUSDT')
    full_df = recent_df.rename(columns={col: f"{target_prefix}_{col}" for col in recent_df.columns})
    
    macro_dfs = {}
    for m_sym in config['FEATURE_ENGINEERING']['MACRO_FEATURES'].keys():
        m_file = os.path.join(raw_dir, f"{m_sym}_BINANCE_1M_2026.parquet")
        m_df = pd.read_parquet(m_file)
        if m_df.index.name == 'time': m_df.index.name = 'timestamp'
        m_df.index = pd.to_datetime(m_df.index)
        macro_dfs[m_sym] = m_df
        full_df = full_df.join(m_df.rename(columns={col: f"{m_sym}_{col}" for col in m_df.columns}), how='left')

    full_df = full_df.sort_index().ffill()
    
    processor = V3DataProcessor(scaler_run_path, feature_order, config=config)
    processor._init_fe()
    fe_df = processor.fe.process_features(full_df)
    
    print("FE DF Columns Sample:", list(fe_df.columns)[:10])
    print("Scaler Column Order:", feature_order)
    
    missing = [c for c in feature_order if c not in fe_df.columns]
    print("Missing columns in FE:", missing)
    
    if not missing:
        # Reorder fe_df to match feature_order
        X_test = fe_df[feature_order].values
        print("X_test shape:", X_test.shape)

if __name__ == "__main__":
    test_recent_performance()
