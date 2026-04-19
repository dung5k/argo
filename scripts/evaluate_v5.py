import os
import sys
import argparse
import json
import pickle
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.training_v5.xgb_model import SelectiveXGBoost

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    cfg_id = config.get("CONFIG_ID", "CFG_V5_UNKNOWN")
    out_dir = os.path.join("data", cfg_id)
    
    print(f"🔥 BẮT ĐẦU ĐÁNH GIÁ (SELECTIVE PREDICTION) MÔ HÌNH V5: {cfg_id}")
    
    test_file = os.path.join(out_dir, "test_v5.pkl")
    with open(test_file, 'rb') as f:
        test_data = pickle.load(f)
        
    X_test = test_data["X_test"]
    y_test = test_data["y_test"]
    macro_test = test_data["macro_test"]
    
    print(f"  Tập TEST OOT: {X_test.shape} nến")
    
    xgb_params = config.get("V5_XGB_ENGINE", {}).get("XGB_PARAMS", {})
    model = SelectiveXGBoost.from_pretrained(os.path.join(out_dir, "xgb_model.json"), xgb_params)
    
    # Lấy Raw Probabilities
    import xgboost as xgb
    dtest = xgb.DMatrix(X_test)
    probs = model.model.predict(dtest)
    
    print("\n" + "="*80)
    print(f"🔬 BÁO CÁO V5 XGBOOST: TUNING 'SELETIVE PREDICTION THRESHOLD'")
    print("="*80)
    print(f"{'Prob Thresh':<12} | {'Toàn bộ Lệnh':<15} | {'VETO Lọc':<10} | {'Đã Vào Lệnh':<12} | {'Thắng/Thua':<12} | {'Win Rate Thực':<20}")
    print("-" * 80)
    
    # Thử nghiệm với các mức Threshold khắt khe
    thresholds = [0.45, 0.48, 0.50, 0.52, 0.54, 0.55, 0.56, 0.58, 0.60, 0.65]
    
    for t in thresholds:
        buy_signals = probs[:, 1] >= t
        sell_signals = probs[:, 0] >= t
        
        # Macro Veto
        vetoed_buy = buy_signals & (macro_test < 0)
        vetoed_sell = sell_signals & (macro_test > 0)
        
        buy_signals = buy_signals & (macro_test >= 0)
        sell_signals = sell_signals & (macro_test <= 0)
        
        buy_wins = np.sum((buy_signals) & (y_test == 1))
        buy_losses = np.sum((buy_signals) & (y_test == 0))
        sell_wins = np.sum((sell_signals) & (y_test == 0))
        sell_losses = np.sum((sell_signals) & (y_test == 1))
        
        num_vetoed = np.sum(vetoed_buy) + np.sum(vetoed_sell)
        
        raw_signals = np.sum(probs[:, 1] >= t) + np.sum(probs[:, 0] >= t)
        total_trades = np.sum(buy_signals) + np.sum(sell_signals)
        total_wins = buy_wins + sell_wins
        total_losses = buy_losses + sell_losses
        
        win_rate = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0.0
        
        print(f"{t:<12.2f} | {raw_signals:<15} | {num_vetoed:<10} | {total_trades:<12} | {total_wins}/{total_losses:<10.2f} | {win_rate*100:<.2f}%")

if __name__ == "__main__":
    main()
