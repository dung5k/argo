import os
import sys
import json
import torch
import pandas as pd
import numpy as np
import itertools
from datetime import datetime, timedelta

# Fix path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from v7_walk_forward import (
    get_synced_data, 
    estimate_dynamic_lag, 
    build_features_and_labels, 
    train_model, 
    run_backtest_simulation,
    filter_by_session
)
from v7_transformer import CrossAssetTransformerModel

def run_grid_search(config_path="d:\\DungLA\\client1\\bot_config_v7.json"):
    print("🚀 BẮT ĐẦU VÉT CẠN GRID SEARCH (V7)")
    
    with open(config_path, "r", encoding="utf-8") as f:
        mcfg = json.load(f)
        
    mt5_path = mcfg.get("mt5_path", "C:\\Program Files\\MetaTrader 5\\terminal64.exe")
    leaders = mcfg.get("leaders", ["BTCUSD", "ETHUSD"])
    follower = mcfg.get("follower", "LTCUSD")
    start_date = "2025-06-01" # Chọn 1 tháng làm Train Data cho nhanh
    
    # === GRID DEFINITIONS ===
    grid = {
        "timeframe": ["M5", "M15"],
        "seq_len": [30, 60],
        "tp_sl_strategy": ["fixed_tight", "fixed_wide", "dynamic_atr"]
    }
    
    keys = list(grid.keys())
    combinations = list(itertools.product(*(grid[k] for k in keys)))
    total_cases = len(combinations)
    
    results = []
    
    for idx, combo in enumerate(combinations):
        case_cfg = dict(zip(keys, combo))
        tf = case_cfg["timeframe"]
        seq_len = case_cfg["seq_len"]
        tp_sl_mode = case_cfg["tp_sl_strategy"]
        
        print(f"\n[{idx+1}/{total_cases}] Chạy Test: TF={tf}, Seq={seq_len}, Mode={tp_sl_mode}")
        
        # Parse mode
        use_atr = False
        tp_pct = 0.005
        sl_pct = 0.0025
        atr_tp_mult = 1.5
        atr_sl_mult = 1.0
        
        if tp_sl_mode == "fixed_tight":
            tp_pct, sl_pct = 0.003, 0.0015
        elif tp_sl_mode == "fixed_wide":
            tp_pct, sl_pct = 0.006, 0.003
        elif tp_sl_mode == "dynamic_atr":
            use_atr = True
            
        # 1. Fetch Data
        # Train 1 tháng, Val 1 tuần
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_train_end = dt_start + timedelta(days=30)
        dt_val_end = dt_train_end + timedelta(days=7)
        end_date = dt_val_end.strftime("%Y-%m-%d")
        
        df_all = get_synced_data(leaders, follower, tf, start_date, end_date, mt5_path)
        if df_all is None or len(df_all) < 100:
            print("  ❌ Không đủ data.")
            continue
            
        train_end_str = dt_train_end.strftime("%Y-%m-%d")
        df_tr = df_all[(df_all.index >= dt_start) & (df_all.index < dt_train_end)]
        df_va = df_all[(df_all.index >= dt_train_end) & (df_all.index < dt_val_end)]
        
        # 2. Xây dựng Features & Labels
        found_lags = {sym: 1 for sym in leaders} # Fake lag
        try:
            X_tr, Y_tr, tr_times, train_scaler = build_features_and_labels(
                df_tr, leaders, found_lags, tp_pct, sl_pct, max_hold_bars=30, seq_len=seq_len,
                use_dynamic_atr=use_atr, atr_tp_mult=atr_tp_mult, atr_sl_mult=atr_sl_mult
            )
            X_va, Y_va, va_times, _ = build_features_and_labels(
                df_va, leaders, found_lags, tp_pct, sl_pct, max_hold_bars=30, seq_len=seq_len,
                scaler_dict=train_scaler, use_dynamic_atr=use_atr, atr_tp_mult=atr_tp_mult, atr_sl_mult=atr_sl_mult
            )
        except Exception as e:
            print(f"  ❌ Lỗi build features: {e}")
            continue
            
        if len(Y_tr) == 0 or len(Y_va) == 0:
            print("  ❌ Dữ liệu rỗng sau khi build features.")
            continue
            
        unique_tr, counts_tr = np.unique(Y_tr, return_counts=True)
        print(f"  ✅ Nhãn Train: {dict(zip(unique_tr, counts_tr))}")
        
        # 3. Khởi tạo & Train Model (Train cực nhanh 20 Epochs)
        model = CrossAssetTransformerModel(num_features=X_tr.shape[2], d_model=64, nhead=4, num_layers=2)
        try:
            model = train_model(model, X_tr, Y_tr, lr=1e-4, epochs=20, batch_size=128, X_val=X_va, Y_val=Y_va)
        except Exception as e:
            print(f"  ❌ Lỗi train: {e}")
            continue
            
        if model is None:
             print("  ❌ Model training returned None.")
             continue
             
        # 4. Đánh giá Val (Backtest giả lập)
        print("  ⏳ Đang chạy Validation Backtest...")
        backtest_data = run_backtest_simulation(model, X_va, va_times, df_va, tp_pct, sl_pct, max_hold_bars=30)
        
        best_res = backtest_data.get("best_res", {})
        if best_res:
             res_record = {
                 "Timeframe": tf,
                 "Seq_Len": seq_len,
                 "TP_SL_Mode": tp_sl_mode,
                 "Trades": best_res.get('trades', 0),
                 "WinRate": best_res.get('win_rate', 0.0),
                 "ProfitFactor": best_res.get('profit_factor', 0.0),
                 "PnL": best_res.get('pnl', 0.0) * 100
             }
             results.append(res_record)
             print(f"  🏆 Kết quả: {res_record['Trades']} lệnh, WR: {res_record['WinRate']*100:.1f}%, PF: {res_record['ProfitFactor']:.2f}, PnL: {res_record['PnL']:.2f}%")
        else:
             print("  ❌ Không có lệnh nào được khớp.")
             
    # Lưu CSV
    if results:
        df_res = pd.DataFrame(results)
        csv_path = os.path.join(os.path.dirname(__file__), "grid_search_results.csv")
        df_res.to_csv(csv_path, index=False)
        print(f"\n🎉 HOÀN THÀNH. Đã lưu kết quả tại: {csv_path}")
    else:
        print("\n❌ Hoàn thành, nhưng không có mô hình nào khớp lệnh.")

if __name__ == "__main__":
    run_grid_search()
