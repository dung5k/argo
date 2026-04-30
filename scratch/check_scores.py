import pandas as pd
import numpy as np
import torch
import json
from src.core_v3.feature_engineering_v3 import LabelingV3
from src.training_v3.model_v3 import AAMT_Model

run_dir = "workspaces/CFG_LTC_LONDON_V3_5/runs/run_20260428_024500_v4_ldn_74"
val_file = f"{run_dir}/dataset/val_v3_ltc_london.parquet"
config_file = f"{run_dir}/config.json"
model_file = f"{run_dir}/brains/best_val_score.pth"

# 1. Load config
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)
brain_cfg = config['TRAINING']
fe_cfg = config['FEATURE_ENGINEERING']

# 2. Load dataset
df_val = pd.read_parquet(val_file)

# The dataset has feature columns (starts with mtf_, rsi_, is_, etc.) and OHLC columns if it's the raw dataframe.
# Wait! Does the validation parquet have raw OHLC columns?
# The upload script usually merges features and labels. Let's check columns.
target_prefix = fe_cfg['TARGET_PREFIX'].lower()
open_col = f"{target_prefix}_open"
high_col = f"{target_prefix}_high"
low_col = f"{target_prefix}_low"

if open_col not in df_val.columns:
    # try lowercase without prefix if it was renamed
    open_col, high_col, low_col = "ltcusdt_open", "ltcusdt_high", "ltcusdt_low"

# 3. Re-calculate Labels with Spread
labeler = LabelingV3(
    tp_pct=0.0035,
    sl_pct=0.0035,
    spread_pct=0.0005, # 0.05% spread
    max_hold_bars=15,
    label_mode='pct'
)

new_labels = labeler.apply_triple_barrier(df_val, open_col, high_col, low_col)
df_val['new_target'] = new_labels

# 4. Load Model
feature_cols = [c for c in df_val.columns if c not in [
    'target_class', 'hit_bars', 'is_clean', 'new_target',
    'ltcusdt_open', 'ltcusdt_high', 'ltcusdt_low', 'ltcusdt_close', 'ltcusdt_volume', 'ltcusdt_tick_volume',
    'btcusdt_open', 'btcusdt_high', 'btcusdt_low', 'btcusdt_close', 'btcusdt_volume', 'btcusdt_tick_volume'
]]

input_dim = len(feature_cols)
window_size = config['WINDOW_SIZE']

# Prepare tensor
features_np = df_val[feature_cols].values
N = len(features_np) - window_size + 1
X_val = np.array([features_np[i:i+window_size] for i in range(N)])
Y_val = df_val['new_target'].values[window_size - 1:]

model = AAMT_Model(input_dim=input_dim, window_size=window_size, **brain_cfg)
model.load_state_dict(torch.load(model_file, map_location='cpu'))
model.eval()

# 5. Predict
with torch.no_grad():
    X_tensor = torch.tensor(X_val, dtype=torch.float32)
    logits = model(X_tensor)
    probs = torch.softmax(logits, dim=1).numpy()

# 6. Evaluate
preds = np.argmax(probs, axis=1)
confidences = np.max(probs, axis=1)

for thresh in [0.55, 0.58, 0.60]:
    mask = confidences >= thresh
    valid_preds = preds[mask]
    valid_targets = Y_val[mask]
    
    # only consider BUY (1) and SELL (0)
    signal_mask = (valid_preds == 0) | (valid_preds == 1)
    final_preds = valid_preds[signal_mask]
    final_targets = valid_targets[signal_mask]
    
    if len(final_preds) > 0:
        win_rate = np.mean(final_preds == final_targets)
        print(f"Threshold {thresh}: Win Rate = {win_rate*100:.2f}% (Signals: {len(final_preds)})")
    else:
        print(f"Threshold {thresh}: No signals")

