import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

sys.path.insert(0, os.path.join(_ROOT, 'huyen_thoai'))

from src.bot_v6.data_processor_v6 import V6DataProcessor
from src.bot_v6.inference_engine_v6 import V6InferenceEngine
from src.simulator.backtest_vtm import BacktestVirtualTradeManager

def resample_dataframe(df_raw, freq):
    df_raw = df_raw.copy()
    if not isinstance(df_raw.index, pd.DatetimeIndex):
        df_raw.index = pd.to_datetime(df_raw.index)
    freq_lower = freq.lower()
    if freq_lower in ['1m', '1t', '1min', 'm1']:
        return df_raw
        
    if freq_lower == '5min':
        freq = '5T'
    elif freq_lower == '15min':
        freq = '15T'
    elif freq_lower == '30min':
        freq = '30T'
    elif freq_lower == '1h' or freq_lower == '60m':
        freq = '1H'
    elif freq_lower == '4h':
        freq = '4H'
        
    agg_dict = {}
    for col in df_raw.columns:
        if col.endswith('_open') or col == 'open':
            agg_dict[col] = 'first'
        elif col.endswith('_high') or col == 'high':
            agg_dict[col] = 'max'
        elif col.endswith('_low') or col == 'low':
            agg_dict[col] = 'min'
        elif col.endswith('_close') or col == 'close':
            agg_dict[col] = 'last'
        elif col.endswith('_volume') or col.endswith('_tick_volume') or col == 'volume' or col == 'tick_volume':
            agg_dict[col] = 'sum'
        else:
            agg_dict[col] = 'last'
    df_res = df_raw.resample(freq).agg(agg_dict)
    df_res = df_res.dropna(subset=['close'])
    return df_res

def _load_parquet(path):
    df = pd.read_parquet(path)
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    elif df.index.name != 'time':
        df.index = pd.to_datetime(df.index)
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    return df

def run_simulation(start_date: str, end_date: str, config_path: str, model_path: str, scaler_path: str):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    print(f"[SIMULATOR V6] Bắt đầu backtest từ {start_date} đến {end_date}")
    
    # 1. Init Data Processor & Inference Engine
    dp = V6DataProcessor(scaler_path=scaler_path, config=config)
    engine = V6InferenceEngine()
    
    # Extract model topology from config
    t_cfg = config.get('TRAINING', {})
    
    # ---------------------------------------------------------
    # TỰ ĐỘNG TÌM NGƯỠNG TỐI ƯU TỪ TRAINING METRICS
    # ---------------------------------------------------------
    metrics_file = os.path.join(os.path.dirname(os.path.dirname(model_path)), "results", "training_metrics_v3.json")
    opt_thresh = config.get('LIVE_BOT', {}).get('MIN_PROBABILITY_THRESH', 0.55)
    
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file, 'r', encoding='utf-8') as mf:
                mdata = json.load(mf)
                
            for sess_name, sess_data in mdata.get("sessions", {}).items():
                if "BEST_VLOSS" in sess_data:
                    metrics_list = sess_data["BEST_VLOSS"].get("threshold_metrics", [])
                    best_wr = -1
                    for m in metrics_list:
                        if m.get("total_signals", 0) >= 5 and m.get("win_rate", 0) > best_wr:
                            best_wr = m.get("win_rate", 0)
                            opt_thresh = m.get("threshold", opt_thresh)
        except Exception as e:
            print(f"[SIMULATOR V6] Lỗi đọc metrics: {e}")
            
    # Use predict_probs instead of prob_threshold
    thresholds_to_test = [0.50, 0.52, 0.53, 0.54, 0.55, 0.56, 0.60]
    # ---------------------------------------------------------
    
    # We must load dummy scalers to get the exact input dims for model loading
    if not dp._init_engines():
        print("Lỗi khởi tạo DataProcessor")
        return
        
    valid_tf_count = len(dp.scalers)
    print(f"[SIMULATOR V6] Cần {valid_tf_count} TFs cho Model.")
    
    # We will assume seq_lens = WINDOW_SIZE
    input_dims = []
    seq_lens = []
    
    for i in range(valid_tf_count):
        input_dims.append(len(dp.column_orders[i]))
        seq_lens.append(dp.tf_configs[i].get('WINDOW_SIZE', 60))
        
    # Load Model
    if not engine.load_weights(
        model_path=model_path,
        input_dims=input_dims,
        seq_lens=seq_lens,
        d_model=t_cfg.get('D_MODEL', 128),
        nhead=t_cfg.get('N_HEAD', 8),
        num_attn_layers=t_cfg.get('NUM_LAYERS', 4),
        pooling=t_cfg.get('POOLING', 'mean'),
        cls_head=t_cfg.get('CLS_HEAD', 'simple')
    ):
        print("[SIMULATOR V6] Lỗi load model")
        return
        
    # 2. Delete existing virtual state files first to prevent state leakage
    import glob
    state_pattern = os.path.join(_ROOT, 'huyen_thoai', 'data', "virtual_state_*.json")
    for state_f in glob.glob(state_pattern):
        try:
            os.remove(state_f)
        except:
            pass

    # 3. Init Virtual Trade Managers
    sim_symbol = f"SIM_{config['TARGET_SYMBOL']}"
    vtms = {th: BacktestVirtualTradeManager(sim_symbol, config=config) for th in thresholds_to_test}
    for vtm in vtms.values():
        vtm.virtual_balance = 10000.0
        vtm.active_trade_loggers = {}
        vtm.history_deals = []
        vtm.last_close_time = 0
    
    # 4. Load Datasets
    raw_dir = os.path.join(_ROOT, config['DATA_SOURCE']['RAW_LOCAL_DIR'])
    target_symbol = config['TARGET_SYMBOL']
    print("[SIMULATOR V6] Loading datasets...")
    
    df_target_1m = _load_parquet(os.path.join(raw_dir, f"{target_symbol.replace('USDT', 'USDT')}_BINANCE_1M_2026.parquet"))
    target_prefix_lower = config.get('TARGET_PREFIX', target_symbol).lower()
    
    # We must load dummy scalers to get the exact input dims for model loading
    if not dp._init_engines():
        print("Lỗi khởi tạo DataProcessor")
        return
        
    valid_tf_count = len(dp.scalers)
    print(f"[SIMULATOR V6] Sử dụng {valid_tf_count} TFs hợp lệ.")
    
    # Build aligned df_raw_all containing all prefixed datasets for vectorized FE
    df_raw_all = df_target_1m.copy()
    
    for tf_cfg in dp.tf_configs:
        sym = tf_cfg['SYMBOL']
        if sym == target_symbol:
            continue
        pq_path = os.path.join(raw_dir, f"{sym}_BINANCE_1M_2026.parquet")
        if os.path.exists(pq_path):
            df_sym = _load_parquet(pq_path)
            rename_map = {c: f"{sym.lower()}_{c}" for c in df_sym.columns}
            df_sym = df_sym.rename(columns=rename_map)
            # Align by left join
            df_raw_all = df_raw_all.join(df_sym[~df_sym.index.duplicated(keep='last')], how='left', rsuffix='_dup')
            print(f"  Joined {sym} into df_raw_all")
            
    # Process vectorized feature engineering once
    print("[SIMULATOR V6] Running vectorized feature engineering...")
    ok, scaled_dfs = dp.process_vectorized(df_raw_all)
    if not ok or not scaled_dfs:
        print("[SIMULATOR V6] Lỗi vectorized feature engineering")
        return
    print("[SIMULATOR V6] Vectorized feature engineering done!")

    # Filter Date Range
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    if df_target_1m.index.tz is not None:
        start_dt = start_dt.tz_localize('UTC')
        end_dt = end_dt.tz_localize('UTC')
    
    target_times = df_target_1m[(df_target_1m.index >= start_dt) & (df_target_1m.index <= end_dt)].index
    print(f"[SIMULATOR V6] Số lượng nến 1M cần xử lý (Target Time): {len(target_times)}")
    
    total_ticks = len(target_times)
    
    # Theo dõi xác suất tối đa và ngày chạy được
    max_p_buy = 0.0
    max_p_sell = 0.0
    last_date = None
    
    for i, t in enumerate(target_times):
        # Bỏ qua ngày cuối tuần (Thứ 7 & Chủ nhật) theo yêu cầu của Sếp Lê
        if t.weekday() >= 5: # 5 = Saturday, 6 = Sunday
            continue
            
        # 1. Update Open Positions (SL, TP, Close signal)
        tick_data = df_target_1m.loc[t]
        spread_val = tick_data.get('spread', 0.0)
        if pd.isna(spread_val):
            spread_val = 0.0
            
        for vtm in vtms.values():
            vtm.sim_clock = t.timestamp()
            vtm.update_virtual_positions_ohlc(
                open_p=tick_data['open'],
                high_p=tick_data['high'],
                low_p=tick_data['low'],
                close_p=tick_data['close'],
                point=0.01,
                spread_pips=spread_val,
                slippage_pips=1.0
            )
        
        # Báo cáo tiến độ Telegram sau mỗi ngày chạy được
        curr_date = t.date()
        if last_date is None:
            last_date = curr_date
            
        if curr_date != last_date:
            msg = f"📅 [SIMULATOR V6] Hoàn tất ngày: {last_date.strftime('%d/%m/%Y')}\n"
            for th, vtm in vtms.items():
                deals = vtm.history_deals
                day_deals = [d for d in deals if d.get("close_time") and pd.to_datetime(d["close_time"]).date() == last_date]
                n_win = sum(1 for d in day_deals if d.get("profit", 0) > 0)
                n_loss = sum(1 for d in day_deals if d.get("profit", 0) <= 0)
                tt = n_win + n_loss
                wr = (n_win / tt * 100) if tt > 0 else 0
                day_pnl = sum(d.get("profit", 0) for d in day_deals)
                total_deals_so_far = len(deals)
                total_pnl_so_far = sum(d.get("profit", 0) for d in deals)
                msg += f"  - Thresh {th:.2f}: Hôm nay {tt} lệnh (WR: {wr:.1f}%, PnL: {day_pnl:+.2f}) | Lũy kế: {total_deals_so_far} lệnh (PnL: {total_pnl_so_far:+.2f})\n"
            
            # Print daily progress in console
            print(f"[SIMULATOR V6] Completed day: {last_date.strftime('%Y-%m-%d')} | " + ", ".join([f"Thresh {th:.2f}: {sum(1 for d in vtm.history_deals if d.get('close_time') and pd.to_datetime(d['close_time']).date() == last_date)} deals" for th, vtm in vtms.items()]), flush=True)
            
            import subprocess
            try:
                subprocess.Popen([sys.executable, '.agent/send_to_tele.py', msg.strip(), '--channel', '1816854047'])
            except Exception as e:
                print(f"[Warning] Failed to send Telegram: {e}", flush=True)
            last_date = curr_date
        
        # Dynamically predict based on the base timeframe from config
        base_tf = dp.tf_configs[0]['TIMEFRAME'].lower()
        if '5m' in base_tf or '5min' in base_tf:
            if t.minute % 5 != 0:
                continue
        elif '15m' in base_tf or '15min' in base_tf:
            if t.minute % 15 != 0:
                continue
        elif '30m' in base_tf or '30min' in base_tf:
            if t.minute % 30 != 0:
                continue
        elif '1h' in base_tf:
            if t.minute != 0:
                continue
            
        # Prepare window tensors from pre-calculated scaled_dfs
        x_tensors = []
        skip = False
        for i, df_scaled in enumerate(scaled_dfs):
            win_size = dp.tf_configs[i].get('WINDOW_SIZE', 60)
            df_slice = df_scaled.loc[:t]
            if len(df_slice) < win_size:
                skip = True
                break
            window = df_slice.iloc[-win_size:].values
            x_tensors.append(np.expand_dims(window, axis=0))
            
        if skip:
            continue
            
        # Predict Probs
        probs = engine.predict_probs(x_tensors)
        if probs is None:
            continue
        p_sell, p_hold, p_buy = probs
        
        max_p_buy = max(max_p_buy, p_buy)
        max_p_sell = max(max_p_sell, p_sell)
        
        for th, vtm in vtms.items():
            if p_buy >= th:
                vtm.execute_trade('BUY', {}, 0.0, tick_data['close'], tick_data['close']+spread_val*0.01, 0.01)
            elif p_sell >= th:
                vtm.execute_trade('SELL', {}, 0.0, tick_data['close'], tick_data['close']+spread_val*0.01, 0.01)

    # Evaluate
    print(f"\n[KẾT QUẢ SIMULATOR THÁNG 5]")
    print(f"[DEBUG PROBS] Out-of-sample Max Probs: Max Buy Prob = {max_p_buy:.4f} | Max Sell Prob = {max_p_sell:.4f}")
    for th, vtm in vtms.items():
        print(f"\n--- KẾT QUẢ VỚI NGƯỠNG {th:.2f} ---")
        deals = vtm.history_deals
        n_win = sum(1 for d in deals if d.get("profit", 0) > 0)
        n_loss = sum(1 for d in deals if d.get("profit", 0) <= 0)
        total_trades = n_win + n_loss
        win_rate = (n_win / total_trades * 100) if total_trades > 0 else 0
        pnl = sum(d.get("profit", 0) for d in deals)
        
        print(f"Tổng giao dịch: {total_trades}")
        days = max((end_dt - start_dt).total_seconds() / 86400.0, 1.0)
        print(f"Trung bình: {total_trades/days:.1f} lệnh/ngày")
        print(f"Thắng: {n_win} | Thua: {n_loss} | WinRate: {win_rate:.2f}%")
        print(f"Tổng PnL: {pnl:+.4f}")
        print(f"Số dư hiện tại: {vtm.virtual_balance:.2f} (Start: 10000.0)")
        
        # Đóng các lệnh còn mở để chốt PnL
        active_trades = list(vtm.active_trade_loggers.keys())
        for tr in active_trades:
            final_close = df_target_1m.loc[end_dt, 'close'] if end_dt in df_target_1m.index else df_target_1m.iloc[-1]['close']
            vtm._close_position_internal(tr, final_close, "End of Simulation")
            
        print(f"Số dư sau khi thanh lý lệnh cuối: {vtm.virtual_balance:.2f}")

if __name__ == '__main__':
    cfg = r'D:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260529_173506_v6_asian\config.json'
    mdl = r'D:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260529_173506_v6_asian\brains\aamt_v3_CFG_LTC_ASIAN_V6_final.pth'
    scl = r'D:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260529_173506_v6_asian\brains\scaler_CFG_LTC_ASIAN_V6.pkl'
    run_simulation('2026-05-01', '2026-05-30', cfg, mdl, scl)
