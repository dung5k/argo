import sys, os, joblib
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')

from src.core.mt5_data_manager import MT5DataManager
import src.core.feature_engineering as fe
import numpy as np

manager = MT5DataManager(log_callback=lambda x: None, target_sym='XAUUSD')
merged_df, sym_data, err = manager.get_live_merged_data_in_memory(window=120)
print(f"merged_df shape={merged_df.shape}")

df, _ = fe.create_stationary_features(merged_df, is_live=True)
print(f"FE output shape={df.shape}")
print(f"Columns: {list(df.columns[:10])}")

scaler = joblib.load(r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\scaler.pkl')
expected = list(scaler.feature_names_in_)
actual = list(df.columns)

missing = [c for c in expected if c not in actual]
extra = [c for c in actual if c not in expected]
print(f"\nScaler expects: {len(expected)} | FE produces: {len(actual)}")
print(f"MISSING from live ({len(missing)}): {missing[:10]}")
print(f"EXTRA in live ({len(extra)}): {extra[:10]}")

last60 = df.iloc[-60:].values
print(f"\nTensor shape: {last60.shape}")
print(f"Has NaN: {np.isnan(last60).any()}")

if last60.shape[1] == 100:  # model expects 86 features
    print("WARNING: Tensor has 100 features but model expects 86!")
    print(f"Missing from FE: is_imputed_flag?", 'is_imputed_flag' in actual)
