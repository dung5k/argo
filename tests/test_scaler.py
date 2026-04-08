import joblib, sys, os
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')

scaler = joblib.load(r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\scaler.pkl')
feats = list(scaler.feature_names_in_)
print(f"Scaler expects: {len(feats)} features")
print("First 20:", feats[:20])
print("XAUUSD cols:", [f for f in feats if 'XAUUSD' in f])
print("is_imputed in scaler:", 'is_imputed_flag' in feats)
