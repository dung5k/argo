import joblib, json, glob, os
import sys

sys.stdout.reconfigure(encoding='utf-8')

data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'
scaler = joblib.load(os.path.join(data_dir, 'scaler.pkl'))
scaler_feats = list(scaler.feature_names_in_)
print(f"=== SCALER ({len(scaler_feats)} features) ===")
print("First 10:", scaler_feats[:10])
xau_in_scaler = [f for f in scaler_feats if 'XAUUSD' in f]
print(f"XAUUSD in scaler ({len(xau_in_scaler)}): {xau_in_scaler}")
print()

# What does training_metrix show  
runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
xau_metrix = sorted([m for m in glob.glob(os.path.join(runs_dir, '**', 'training_metrix.json'), recursive=True)
              if 'xauusd' in m.lower()])

print(f"=== TRAINING METRIX ({len(xau_metrix)} files) ===")  
for mf in xau_metrix:
    with open(mf, encoding='utf-8') as f:
        m = json.load(f)
    feats = m.get('training_metadata', {}).get('data_features', [])
    print(f"\n[{os.path.basename(os.path.dirname(mf))}]: {len(feats)} features")
    if feats:
        print("First 10:", feats[:10])
        print("Same as scaler?", set(feats) == set(scaler_feats))
        missing_from_scaler = [f for f in feats if f not in scaler_feats]
        extra_in_scaler = [f for f in scaler_feats if f not in feats]
        print(f"missing from scaler: {missing_from_scaler[:5]}")
        print(f"extra in scaler: {extra_in_scaler[:5]}")
