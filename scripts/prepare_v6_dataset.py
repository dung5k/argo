# -*- coding: utf-8 -*-
"""
Script chuẩn bị dữ liệu V6 MTF (Multi-Timeframe Fusion).
Hỗ trợ tạo Tensor đầu vào dạng List [X_tf1, X_tf2, ...] để cho model Dual-Encoder xử lý.
"""
import os
import sys
import json
import pickle
import argparse

import numpy as np
import pandas as pd
from tqdm import tqdm
from huggingface_hub import HfApi

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3, LabelingV3

def abort(msg: str):
    print(f"\n💥 ABORT: {msg}", flush=True)
    sys.exit(1)

def assert_ok(condition: bool, msg: str):
    if not condition:
        abort(msg)

def load_crypto_parquets(raw_dir: str, target_symbol: str, target_prefix: str,
                          macro_features: dict, dataset_suffix: str = "2026"):
    print(f"\n[LOAD] Quét thư mục: {raw_dir}", flush=True)
    all_files = [f for f in os.listdir(raw_dir) if f.endswith(".parquet")]
    assert_ok(len(all_files) > 0, f"Thư mục {raw_dir} không có file parquet nào!")

    required_symbols = {}
    file_sym_to_orig = {}
    
    t_sym = target_symbol.upper()
    file_sym = t_sym[:-1] if t_sym.endswith("M") else t_sym
    file_sym_to_orig[file_sym] = t_sym
    if t_sym.endswith("USDT"):
        required_symbols[file_sym] = "BINANCE"
    else:
        required_symbols[file_sym] = "MT5"
        
    for sym, _ in macro_features.items():
        if sym.startswith("_"): continue
        sym_up = sym.upper()
        file_sym_macro = sym_up[:-1] if sym_up.endswith("M") else sym_up
        file_sym_to_orig[file_sym_macro] = sym_up
        if sym_up.endswith("USDT") or sym_up.endswith("BTC"):
            required_symbols[file_sym_macro] = "BINANCE"
        else:
            required_symbols[file_sym_macro] = "MT5"

    df_list = []
    loaded = set()

    for sym, source in required_symbols.items():
        sym_files = [f for f in all_files if sym in f.upper() and source in f.upper()]
        if not sym_files:
            continue
            
        dfs_for_sym = []
        for fname in sorted(sym_files):
            path = os.path.join(raw_dir, fname)
            dfs_for_sym.append(pd.read_parquet(path))
            
        if dfs_for_sym:
            df_sym = pd.concat(dfs_for_sym)
            if "time" in df_sym.columns:
                df_sym.set_index("time", inplace=True)
            if df_sym.index.tz is None:
                df_sym.index = df_sym.index.tz_localize("UTC")
            
            # Lọc dữ liệu từ 2024 trở đi và bỏ duplicate
            df_sym = df_sym[~df_sym.index.duplicated(keep='first')].sort_index()
            df_sym = df_sym[df_sym.index >= "2024-01-01"]
            
            orig_sym = file_sym_to_orig[sym]
            rename_map = {c: f"{orig_sym}_{c}" for c in df_sym.columns}
            df_sym = df_sym.rename(columns=rename_map)
            df_list.append(df_sym)
            loaded.add(orig_sym)
            print(f"  + {orig_sym}: Đã gộp {len(sym_files)} file → {len(df_sym):,} nến (từ 2024)", flush=True)

    missing = set([file_sym_to_orig[k] for k in required_symbols.keys()]) - loaded
    assert_ok(len(missing) == 0, f"Thiếu dữ liệu cho các symbol: {missing}.")

    df_raw = df_list[0].copy()
    for df_next in df_list[1:]:
        df_raw = df_raw.join(df_next, how="outer")
    df_raw = df_raw.sort_index().ffill(limit=5)
    print(f"  ✅ df_raw tổng hợp: {df_raw.shape[0]:,} dòng × {df_raw.shape[1]} cột", flush=True)
    return df_raw

def resample_dataframe(df_raw, freq):
    if not freq or freq in ['1m', '1T', 'M1']:
        return df_raw.copy()
    
    agg_dict = {}
    for col in df_raw.columns:
        if col.endswith('_open'):
            agg_dict[col] = 'first'
        elif col.endswith('_high'):
            agg_dict[col] = 'max'
        elif col.endswith('_low'):
            agg_dict[col] = 'min'
        elif col.endswith('_close'):
            agg_dict[col] = 'last'
        elif col.endswith('_volume') or col.endswith('_tick_volume'):
            agg_dict[col] = 'sum'
        else:
            agg_dict[col] = 'last'
            
    df_resampled = df_raw.resample(freq).agg(agg_dict).dropna()
    return df_resampled

def align_mtf_windows(target_time, i, target_idx, tf_times, tf_vals, window_sizes):
    """
    Trích xuất list các window tensor cho target_time.
    Trả về (windows_list, has_nan).
    """
    windows = []
    has_nan = False
    
    for tf_i in range(len(window_sizes)):
        win_size = window_sizes[tf_i]
        if tf_i == 0:
            # Base TF (khung thấp nhất), lấy window theo index
            win = tf_vals[0][i : target_idx + 1]
        else:
            # HTF: tìm nến gần nhất tính đến target_time
            loc = tf_times[tf_i].get_indexer([target_time], method='pad')[0]
            if loc < win_size - 1:
                has_nan = True
                break
            win = tf_vals[tf_i][loc - win_size + 1 : loc + 1]
            
        if len(win) != win_size or np.isnan(win).any():
            has_nan = True
            break
        windows.append(win)
        
    return windows, has_nan

def get_split_class(target_time, target_idx, base_timestamps, monthly_split, month_val_start, weekend_split=False):
    """
    Xác định tập Train (0), Val (1), hay Embargo (-1).
    """
def get_split_class(target_time, target_idx, base_timestamps, split_time=None, embargo_time=None, weekly_split=False):
    if weekly_split:
        import datetime
        delta_days = (target_time.date() - datetime.date(2024, 1, 1)).days
        week_index = delta_days // 7
        cycle = week_index % 5
        if cycle < 3:
            return 0 # Train
        else:
            return 1 # Val (Khoảng trống cuối tuần 2 ngày tự nhiên làm Embargo Gap)
            
    if split_time is not None and embargo_time is not None:
        if target_time < split_time:
            return 0
        elif target_time < embargo_time:
            return -1
        else:
            return 1
            
    return 0

def build_tensor_mtf(df_feats_list, labels_series, clean_mask, session_start, session_end, session_days,
                     window_sizes, step_size=1, weekly_split=False, split_time=None, embargo_time=None):
    """
    Tạo list các Tensors X_tf1, X_tf2 cho V6 MTF.
    """
    print(f"\n[DEBUG] Bắt đầu ráp Tensor MTF với window_sizes={window_sizes}, step_size={step_size}, weekly_split={weekly_split}")
    try:
        sh, sm = map(int, session_start.split(":"))
        eh, em = map(int, session_end.split(":"))
        start_min = sh * 60 + sm
        end_min   = eh * 60 + em
    except Exception:
        start_min, end_min = 0, 1439

    base_timestamps = labels_series.index
    
    # Weekly Split: 3 tuần Train / 2 tuần Test -> Embargo qua cuối tuần

    # Chuẩn bị truy xuất nhanh cho các TF cao hơn
    tf_times = [df.index for df in df_feats_list]
    tf_vals  = [df.values for df in df_feats_list]

    X_lists = [[] for _ in range(len(window_sizes))]
    Y_list, split_list = [], []

    max_idx = len(base_timestamps) - window_sizes[0]
    n_skip = {'session': 0, 'clean': 0, 'nan': 0, 'embargo': 0}
    print(f"[DEBUG] max_idx (số lượng nến Base có thể dùng): {max_idx}")

    for i in tqdm(range(0, max_idx, step_size), desc="Ráp Tensor MTF"):
        target_idx  = i + window_sizes[0] - 1
        target_time = base_timestamps[target_idx]

        # 1. Lọc Session
        tim = target_time.hour * 60 + target_time.minute
        in_session = (start_min <= tim <= end_min) if start_min <= end_min else (tim >= start_min or tim <= end_min)
        
        if session_days is not None:
            if target_time.dayofweek not in session_days:
                in_session = False
                
        if not in_session:
            n_skip['session'] += 1; continue

        # 2. Lọc Clean Mask
        if not clean_mask.iloc[target_idx]:
            n_skip['clean'] += 1; continue

        # 3. Gom Data đa khung
        target_label = labels_series.iloc[target_idx]
        if np.isnan(target_label):
            n_skip['nan'] += 1; continue
            
        windows, has_nan = align_mtf_windows(target_time, i, target_idx, tf_times, tf_vals, window_sizes)
            
        if has_nan:
            n_skip['nan'] += 1; continue

        # 4. Weekly Split / Embargo
        split_class = get_split_class(target_time, target_idx, base_timestamps, split_time, embargo_time, weekly_split)
            
        if split_class == -1:
            n_skip['embargo'] += 1; continue
            
        for tf_i in range(len(window_sizes)):
            X_lists[tf_i].append(windows[tf_i])
        Y_list.append(target_label)
        split_list.append(split_class)

    print(f"  Bỏ qua (ngoài session): {n_skip['session']:,}", flush=True)
    print(f"  Bỏ qua (clean mask):    {n_skip['clean']:,}", flush=True)
    print(f"  Bỏ qua (NaN):           {n_skip['nan']:,}", flush=True)
    print(f"  Bỏ qua (Embargo):       {n_skip['embargo']:,}", flush=True)
    print(f"  Giữ lại (Valid Samples):{len(Y_list):,}", flush=True)

    if len(Y_list) == 0:
        print("[FATAL] KHÔNG CÓ SAMPLE NÀO ĐƯỢC TẠO RA! Hãy kiểm tra lại Clean Mask hoặc Nan values.", flush=True)

    X_tensors = [np.array(xl, dtype=np.float32) for xl in X_lists]
    Y = np.array(Y_list, dtype=np.int64)
    S = np.array(split_list, dtype=np.int8)

    return X_tensors, Y, S

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="bot_config_v6_ltc_asian.json")
    parser.add_argument("--fast-hit-bars", type=int, default=3)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument('--weekly-split', action='store_true', help="Dùng phân tách Train/Test chu kỳ tuần 3/2")
    args = parser.parse_args()

    assert_ok(os.path.exists(args.config), f"File config không tồn tại: {args.config}")
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    cfg_id        = config.get("CONFIG_ID", "V6_UNKNOWN")
    target_sym    = config.get("TARGET_SYMBOL", "LTCUSDT")
    target_prefix = config.get("TARGET_PREFIX", "LTC")
    fe_cfg        = config["FEATURE_ENGINEERING"]
    session_start = config.get("SESSION_UTC", {}).get("START", "00:00")
    session_end   = config.get("SESSION_UTC", {}).get("END",   "23:59")
    session_days  = config.get("SESSION_UTC", {}).get("DAYS", None)
    
    mtf_inputs = fe_cfg.get("MTF_INPUTS", [])
    if not mtf_inputs:
        # Fallback for old config
        mtf_inputs = [{"SYMBOL": target_sym, "TIMEFRAME": "1m", "WINDOW_SIZE": fe_cfg.get("WINDOW_SIZE", 60), "FEATURES": ["close"]}]
        
    raw_dir       = os.path.join("workspaces", cfg_id, "data", "raw")
    out_dir       = os.path.join("workspaces", cfg_id, "data", "tensors")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*70}", flush=True)
    print(f"🔥 CHUẨN BỊ DỮ LIỆU V6 MTF HETEROGENEOUS: {cfg_id}", flush=True)
    print(f"{'='*70}", flush=True)

    # 1. Load all required symbols
    unique_symbols = {inp["SYMBOL"]: [] for inp in mtf_inputs}
    unique_symbols[target_sym] = []
    
    df_raw_1m = load_crypto_parquets(
        raw_dir, target_sym, target_prefix, unique_symbols,
        dataset_suffix=config.get("DATA_SOURCE", {}).get("DATASET_SUFFIX", "2026")
    )

    sym_up = target_sym.upper()
    actual_open = f"{sym_up}_open"
    actual_high = f"{sym_up}_high"
    actual_low  = f"{sym_up}_low"
    actual_close = f"{sym_up}_close"

    # 2. GẮN NHÃN TRÊN KHUNG BASE (1m của TARGET_SYMBOL)
    print(f"\n[1] Gắn nhãn Triple-Barrier trên khung Base (1m) cho {target_sym}...", flush=True)
    labeler = LabelingV3(
        max_hold_bars=fe_cfg["MAX_HOLD_BARS"],
        label_mode=fe_cfg.get("LABEL_MODE", "pct"),
        tp_pct=fe_cfg.get("TP_PCT", 0.003),
        sl_pct=fe_cfg.get("SL_PCT", 0.003),
        spread_pct=fe_cfg.get("SPREAD_PCT", 0.0005)
    )

    label_df = labeler.apply_triple_barrier_fast_hit(df_raw_1m, actual_open, actual_high, actual_low)
    clean_mask = labeler.get_clean_mask(label_df, fast_hit_bars=args.fast_hit_bars, include_sideway=True)

    # Xác định mốc thời gian chia Train/Val (80/20) và Embargo (2880 nến 1m)
    split_idx_time = int(len(label_df) * 0.8)
    split_time = label_df.index[split_idx_time]
    embargo_idx = min(len(label_df) - 1, split_idx_time + 2880)
    embargo_time = label_df.index[embargo_idx]
    
    # Cập nhật get_split_class cho hàm gọi build_tensor_mtf
    # Lưu biến globals hoặc partial function? Sẽ truyền thêm params.
    
    # Downsample Class 2 (CHỈ TRÊN TẬP TRAIN)
    if 2 in label_df["target_class"].values:
        train_mask = label_df.index < split_time
        idx_c0 = label_df.index[(label_df["target_class"] == 0) & clean_mask & train_mask]
        idx_c1 = label_df.index[(label_df["target_class"] == 1) & clean_mask & train_mask]
        idx_c2 = label_df.index[(label_df["target_class"] == 2) & clean_mask & train_mask]
        
        max_decisive = max(len(idx_c0), len(idx_c1))
        keep_n = min(len(idx_c2), max_decisive)
        if keep_n < len(idx_c2):
            drop_indices = np.random.choice(idx_c2, size=len(idx_c2) - keep_n, replace=False)
            clean_mask.loc[drop_indices] = False

    targets = label_df["target_class"]
    print(f"  Phân bố TRAIN sau Downsample: {label_df.loc[clean_mask & (label_df.index < split_time), 'target_class'].value_counts().to_dict()}")
    print(f"  Phân bố TEST (Giữ nguyên thực tế): {label_df.loc[clean_mask & (label_df.index >= embargo_time), 'target_class'].value_counts().to_dict()}")

    # 3. XỬ LÝ FEATURE ENGINEERING CHO TỪNG NHÁNH MTF_INPUTS
    print(f"\n[2] Feature Engineering Độc Lập Cho Từng MTF_INPUTS...", flush=True)
    df_feats_scaled = []
    scalers = []
    column_orders = []
    window_sizes = []
    dfs_mtf = []

    for i, inp in enumerate(mtf_inputs):
        sym = inp["SYMBOL"]
        freq = inp["TIMEFRAME"]
        w = inp["WINDOW_SIZE"]
        feats = inp["FEATURES"]
        print(f"  -> Nhánh {i}: {sym} | {freq} | Window {w}", flush=True)
        
        # 3.1 Cắt dataframe chỉ chứa cột của Symbol hiện tại (và Target Symbol close để tính correlation nếu cần)
        sym_cols = [c for c in df_raw_1m.columns if c.startswith(sym.upper() + "_")]
        # Luôn kèm theo TARGET_close và TARGET_open để FeatureEngineering không bị lỗi khi tìm kiếm
        required_cols = list(set(sym_cols + [actual_close, actual_open]))
        df_sym_raw = df_raw_1m[required_cols].copy()
        
        # 3.2 Resample theo Timeframe
        df_tf = resample_dataframe(df_sym_raw, freq)
        dfs_mtf.append(df_tf)
        window_sizes.append(w)
        
        # 3.3 Gọi FeatureEngineeringV3
        # Trick: Đặt target_prefix thành sym để nó tính toán các chỉ báo nội tại của sym.
        # Đặt macro_features = {TARGET_SYMBOL: ["log_ret", "corr_60"]} để nó tính tương quan với TARGET_SYMBOL.
        fe = FeatureEngineeringV3(
            target_prefix=sym,
            macro_features={target_sym: ["log_ret", "corr_60"]} if sym != target_sym else {},
            crypto_mode=fe_cfg.get("CRYPTO_MODE", False),
            order_flow=fe_cfg.get("ORDER_FLOW", False),
            vol_regime=fe_cfg.get("VOL_REGIME", False)
        )
        df_f = fe.process_features(df_tf)
        
        # Sửa tên cột correlation nếu có
        # FeatureEngineeringV3 sẽ tạo ra cột {TARGET_SYMBOL}_target_corr_60
        corr_col_name = f"{target_sym}_target_corr_60"
        if corr_col_name in df_f.columns:
            df_f = df_f.rename(columns={corr_col_name: f"corr_60_{target_sym}"})
            
        # 3.4 Lọc chỉ lấy các Features được cấu hình trong JSON
        available_feats = list(df_f.columns)
        final_cols = []
        for f_req in feats:
            if f_req in available_feats:
                final_cols.append(f_req)
            else:
                print(f"     [Cảnh báo] Feature '{f_req}' không tồn tại. Bỏ qua.")
        
        if not final_cols:
            print(f"     [FATAL] Không có feature nào hợp lệ cho nhánh {i}!")
            final_cols = available_feats[:1] # Dự phòng
            
        df_f = df_f[final_cols]
        print(f"     Đã lọc {len(final_cols)} features: {final_cols[:3]}...")
        
        # 3.5 Fit scaler (trên 80% thời gian đầu)
        train_idx = int(len(df_f) * 0.8)
        train_mask = np.zeros(len(df_f), dtype=bool)
        train_mask[:train_idx] = True
        
        fe.fit_transform_scaler(df_f[train_mask])
        df_sc = fe.transform_scaler(df_f)
        
        df_feats_scaled.append(df_sc)
        scalers.append(fe.scaler)
        column_orders.append(list(df_sc.columns))

    # [4] RÁP TENSOR
    # dfs_mtf là mảng chứa dataframe gốc (OHLC) của mỗi nhánh, chỉ dùng để lấy index datetime trong align_mtf_windows.
    # df_feats_scaled là mảng chứa data đã features + scaled.
    X_tensors, Y, S = build_tensor_mtf(
        df_feats_scaled, targets, clean_mask,
        session_start, session_end, session_days,
        window_sizes, step_size=fe_cfg.get("STEP_SIZE", 1),
        weekly_split=args.weekly_split,
        split_time=split_time,
        embargo_time=embargo_time
    )

    print(f"\n👉 KẾT QUẢ: Y={Y.shape}")
    for i, xt in enumerate(X_tensors):
        print(f"  X_tf{i} ({mtf_inputs[i]['SYMBOL']}-{mtf_inputs[i]['TIMEFRAME']}): {xt.shape}")

    # [5] LƯU CỤC BỘ
    y_path = os.path.join(out_dir, f"Y_tensor_{cfg_id}.npy")
    np.save(y_path, Y)
    
    s_path = os.path.join(out_dir, f"S_tensor_{cfg_id}.npy")
    np.save(s_path, S)
    
    for i, xt in enumerate(X_tensors):
        x_path = os.path.join(out_dir, f"X_tensor_{cfg_id}_tf{i}.npy")
        np.save(x_path, xt)

    scaler_bundle = {
        "scalers": scalers,
        "column_orders": column_orders,
        "mtf_inputs": mtf_inputs
    }
    import pickle
    with open(os.path.join(out_dir, f"scaler_{cfg_id}.pkl"), "wb") as f:
        pickle.dump(scaler_bundle, f)

    print(f"\n✅ Đã lưu tensor MTF Heterogeneous cục bộ tại: {out_dir}/", flush=True)

if __name__ == "__main__":
    main()
