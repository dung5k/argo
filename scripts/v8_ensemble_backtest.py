import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import argparse
import pandas as pd
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs='+', required=True, help="List of model .pt files")
    parser.add_argument("--data", type=str, default="data/v8_test_2026.parquet", help="Path to data parquet")
    return parser.parse_args()

def main():
    args = get_args()
    
    print(f"=== ENSEMBLE V8 BACKTEST RUNNER ===")
    print(f"Loading {len(args.models)} Models:")
    for m in args.models:
        print(f"  - {m}")
    print(f"Loading Data: {args.data}")
    
    config_path = "v8_configs/v8_training_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    if not os.path.exists(args.data):
        print("Data file not found!")
        return
        
    full_df = pd.read_parquet(args.data)
    full_df = full_df[~full_df.index.duplicated(keep='first')].sort_index()
    
    df_test = full_df
    if 'tick_volume' in df_test.columns and 'volume' not in df_test.columns:
        df_test = df_test.rename(columns={'tick_volume': 'volume'})
    df_test_h1 = df_test.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df_test_h4 = df_test.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    
    print("Building features...")
    test_dataset = V8DatasetBuilder(config, df_test, df_test_h1, df_test_h4)
    test_loader = DataLoader(test_dataset, batch_size=1024, shuffle=False)
    
    ensemble_s2 = []
    ensemble_b2 = []
    
    for i, model_path in enumerate(args.models):
        print(f"[{i+1}/{len(args.models)}] Running predictions for {os.path.basename(model_path)}...")
        state_dict = torch.load(model_path, map_location=device, weights_only=False)
        layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
        num_layers = max(layer_indices) + 1 if layer_indices else 3
        
        config['transformer_params']['num_layers'] = num_layers
        
        model = V8TransformerModel(config)
        model.load_state_dict(state_dict)
        model.to(device)
        model.eval()
        
        all_probs = []
        with torch.no_grad():
            for x_m15, x_h1, x_h4, cont_x, y in test_loader:
                x_m15, x_h1, x_h4, cont_x = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device)
                out = model(x_m15, x_h1, x_h4, cont_x)
                probs = torch.softmax(out, dim=1)
                all_probs.append(probs.cpu())
                
        all_probs = torch.cat(all_probs, dim=0)
        prob_s2 = all_probs[:, 0]
        prob_b2 = all_probs[:, 4]
        
        ensemble_s2.append(prob_s2)
        ensemble_b2.append(prob_b2)
        
        # Cleanup memory
        del model, state_dict, all_probs
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # Aggregate ensemble predictions
    print("Aggregating Ensemble Predictions (Taking MAX across models)...")
    ensemble_s2 = torch.stack(ensemble_s2, dim=0).max(dim=0)[0]
    ensemble_b2 = torch.stack(ensemble_b2, dim=0).max(dim=0)[0]
    
    max_trade_probs, trade_dirs = torch.max(torch.stack([ensemble_s2, ensemble_b2], dim=1), dim=1)
    
    valid_df = test_dataset.valid_df
    n_samples = len(valid_df)
    
    spread = 0.3
    tp_mult = 3.0
    sl_mult = 1.5
    max_hold = 12
    cooldown = 4
    
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70]
    
    total_active_days = len(set(valid_df.index.date))
    
    print("\n" + "="*90)
    print(f"{'Thr':<6} | {'Trades':<8} | {'Win%':<7} | {'PnL(pip)':<10} | {'MaxDD':<8} | {'PF':<6} | {'T/Day':<8} | {'Cov(%)':<6}")
    print("-" * 90)
    
    for threshold_sim in thresholds:
        signal_mask_sim = max_trade_probs >= threshold_sim
        
        wins = 0
        losses = 0
        total_pnl = 0.0
        peak = 0.0
        max_dd = 0.0
        
        gross_profit = 0.0
        gross_loss = 0.0
        
        active_days = set()
        
        i = 0
        while i < n_samples:
            if not signal_mask_sim[i]:
                i += 1
                continue
                
            entry_idx = valid_df.index[i]
            active_days.add(entry_idx.date())
            
            entry_price = valid_df['close'].iloc[i]
            atr = valid_df['atr'].iloc[i]
            
            tp_dist = atr * tp_mult
            sl_dist = atr * sl_mult
            
            direction = trade_dirs[i].item() # 0 = S2, 1 = B2
            
            trade_pnl = 0.0
            
            for j in range(i + 1, min(i + 1 + max_hold, n_samples)):
                curr_high = valid_df['high'].iloc[j]
                curr_low = valid_df['low'].iloc[j]
                curr_close = valid_df['close'].iloc[j]
                
                if direction == 1: # Buy
                    entry_with_spread = entry_price + spread
                    if curr_low <= entry_price - sl_dist:
                        trade_pnl = -(sl_dist + spread)
                        break
                    elif curr_high >= entry_price + tp_dist:
                        trade_pnl = (tp_dist - spread)
                        break
                else: # Sell
                    entry_with_spread = entry_price - spread
                    if curr_high >= entry_price + sl_dist:
                        trade_pnl = -(sl_dist + spread)
                        break
                    elif curr_low <= entry_price - tp_dist:
                        trade_pnl = (tp_dist - spread)
                        break
                        
            if trade_pnl == 0.0:
                end_idx = min(i + max_hold, n_samples - 1)
                exit_price = valid_df['close'].iloc[end_idx]
                if direction == 1:
                    trade_pnl = exit_price - (entry_price + spread)
                else:
                    trade_pnl = (entry_price - spread) - exit_price
                    
            if trade_pnl > 0:
                wins += 1
                gross_profit += trade_pnl
            else:
                losses += 1
                gross_loss += abs(trade_pnl)
                
            total_pnl += trade_pnl
            
            if total_pnl > peak:
                peak = total_pnl
            dd = peak - total_pnl
            if dd > max_dd:
                max_dd = dd
                
            i += cooldown
            
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        pf = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        t_per_day = total_trades / total_active_days if total_active_days > 0 else 0
        cov_pct = (len(active_days) / total_active_days * 100) if total_active_days > 0 else 0
        
        print(f"{threshold_sim:<6.2f} | {total_trades:<8} | {win_rate:>5.1f}% | {total_pnl:>+8.1f}   | {max_dd:>6.1f}   | {pf:<6.2f} | {t_per_day:<8.1f} | {cov_pct:>5.1f}%")
        
    print("==========================================================================================")

if __name__ == "__main__":
    main()
