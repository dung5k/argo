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
    if not os.path.exists(scaler_run_path):
        scaler_run_path = os.path.join(workspace, "data", "tensors", f"scaler_{config['CONFIG_ID']}.pkl")
        
    scaler_bundle = joblib.load(scaler_run_path)
    feature_names = scaler_bundle['column_order']
    input_dim = len(feature_names)
    scaler = scaler_bundle['scaler']
    
    # Load Model
    model_path = os.path.join(run_dir, "brains", f"aamt_v3_{config['CONFIG_ID']}_final.pth")
    checkpoint = torch.load(model_path, map_location='cpu')
    state_dict = checkpoint.get('model_state_dict', checkpoint)
    
    model = AAMT_Model(
        input_dim=input_dim,
        d_model=config['TRAINING'].get('D_MODEL', 128),
        nhead=config['TRAINING'].get('N_HEAD', 8),
        num_layers=config['TRAINING'].get('NUM_LAYERS', 4),
        pooling=checkpoint.get('pooling', config['TRAINING'].get('POOLING', 'mean')),
        cls_head=checkpoint.get('cls_head', config['TRAINING'].get('CLS_HEAD', 'simple')),
        layer_drop=0.0
    )
    model.load_state_dict(state_dict)
    model.eval()
    
    # Data
    raw_dir = os.path.join(workspace, "data", "raw")
    target_sym = config['TARGET_SYMBOL']
    target_prefix = config.get('TARGET_PREFIX', 'LTCUSDT')
    df_target = pd.read_parquet(os.path.join(raw_dir, f"{target_sym}_BINANCE_1M_2026.parquet"))
    if df_target.index.name == 'time': df_target.index.name = 'timestamp'
    df_target.index = pd.to_datetime(df_target.index)
    recent_df = df_target.loc['2026-04-20':'2026-05-05'].copy()
    
    macro_dfs = {}
    for m_sym in config['FEATURE_ENGINEERING']['MACRO_FEATURES'].keys():
        m_file = os.path.join(raw_dir, f"{m_sym}_BINANCE_1M_2026.parquet")
        m_df = pd.read_parquet(m_file)
        if m_df.index.name == 'time': m_df.index.name = 'timestamp'
        m_df.index = pd.to_datetime(m_df.index)
        macro_dfs[m_sym] = m_df

    full_df = recent_df.rename(columns={col: f"{target_prefix}_{col}" for col in recent_df.columns})
    for m_sym, m_df in macro_dfs.items():
        m_cols = {col: f"{m_sym}_{col}" for col in m_df.columns}
        full_df = full_df.join(m_df.rename(columns=m_cols), how='left')
    full_df = full_df.sort_index().ffill()
    
    processor = V3DataProcessor(scaler_run_path, feature_names, config=config)
    processor._init_fe()
    fe_df = processor.fe.process_features(full_df)
    
    # Manual Labels
    tp, sl = config['FEATURE_ENGINEERING']['TP_PCT'], config['FEATURE_ENGINEERING']['SL_PCT']
    hold = config['FEATURE_ENGINEERING']['MAX_HOLD_BARS']
    close_prices = full_df[f"{target_prefix}_close"].values
    labels = []
    for i in range(len(full_df)):
        label = 2
        price = close_prices[i]
        for j in range(1, hold + 1):
            if i + j >= len(close_prices): break
            future_price = close_prices[i+j]
            ret = (future_price - price) / price
            if ret >= tp: label = 1; break
            elif ret <= -sl: label = 0; break
        labels.append(label)
    fe_df['target_label'] = labels

    fe_df['hour'] = fe_df.index.hour
    asian_df = fe_df[(fe_df['hour'] >= 0) & (fe_df['hour'] < 7)]
    asian_df = asian_df[asian_df.index >= '2026-04-21']
    if config['FEATURE_ENGINEERING'].get('CLEAN_DATA_DIET', False):
        asian_df = asian_df[asian_df['target_label'] != 2]

    print(f"Test samples (Asian session): {len(asian_df)}")
    print(f"Label distribution:\n{asian_df['target_label'].value_counts()}")

    X_raw = fe_df[feature_names].values
    X_scaled = np.zeros_like(X_raw)
    n_scale = scaler.n_features_in_
    X_scaled[:, :n_scale] = scaler.transform(X_raw[:, :n_scale])
    X_scaled[:, n_scale:] = X_raw[:, n_scale:]
    
    X_windows, Y_labels = [], []
    window_size = config['FEATURE_ENGINEERING']['WINDOW_SIZE']
    for idx_label in asian_df.index:
        fe_idx = fe_df.index.get_loc(idx_label)
        if fe_idx < window_size: continue
        X_windows.append(X_scaled[fe_idx - window_size + 1 : fe_idx + 1])
        Y_labels.append(fe_df.at[idx_label, 'target_label'])

    if not X_windows: return
    X_tensor = torch.tensor(np.array(X_windows)).float()
    Y_tensor = torch.tensor(np.array(Y_labels)).long()
    
    with torch.no_grad():
        _, logits, _ = model(X_tensor)
        probs = torch.softmax(logits, dim=1)
        
    print(f"Max Prob Buy: {probs[:, 1].max().item():.4f}, Max Prob Sell: {probs[:, 0].max().item():.4f}")
    
    thresholds = [0.5, 0.51, 0.53, 0.54, 0.55]
    print("\n--- PERFORMANCE REPORT (2026-04-21 to 2026-05-04) ---")
    for t in thresholds:
        buy_mask = probs[:, 1] > t
        sell_mask = probs[:, 0] > t
        n_buy, n_sell = buy_mask.sum().item(), sell_mask.sum().item()
        n_total = n_buy + n_sell
        if n_total == 0: continue
        correct_buy = (Y_tensor[buy_mask] == 1).sum().item()
        correct_sell = (Y_tensor[sell_mask] == 0).sum().item()
        wr = (correct_buy + correct_sell) / n_total
        print(f"Threshold {t*100:.1f}%: WR={wr*100:.2f}% | Total={n_total} (Buy={n_buy}, Sell={n_sell})")

if __name__ == "__main__":
    test_recent_performance()
