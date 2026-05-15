import os
import re

def refactor_prepare():
    path = "scripts/prepare_v6_dataset.py"
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # Replace the main() function completely
    old_main = re.search(r"def main\(\):.*", code, re.DOTALL).group(0)
    
    new_main = """def main():
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

    print(f"\\n{'='*70}", flush=True)
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
    print(f"\\n[1] Gắn nhãn Triple-Barrier trên khung Base (1m) cho {target_sym}...", flush=True)
    labeler = LabelingV3(
        max_hold_bars=fe_cfg["MAX_HOLD_BARS"],
        label_mode=fe_cfg.get("LABEL_MODE", "pct"),
        tp_pct=fe_cfg.get("TP_PCT", 0.003),
        sl_pct=fe_cfg.get("SL_PCT", 0.003),
        spread_pct=fe_cfg.get("SPREAD_PCT", 0.0005)
    )

    label_df = labeler.apply_triple_barrier_fast_hit(df_raw_1m, actual_open, actual_high, actual_low)
    clean_mask = labeler.get_clean_mask(label_df, fast_hit_bars=args.fast_hit_bars, include_sideway=True)

    # Downsample Class 2
    if 2 in label_df["target_class"].values:
        idx_c0 = label_df.index[(label_df["target_class"] == 0) & clean_mask]
        idx_c1 = label_df.index[(label_df["target_class"] == 1) & clean_mask]
        idx_c2 = label_df.index[(label_df["target_class"] == 2) & clean_mask]
        
        max_decisive = max(len(idx_c0), len(idx_c1))
        keep_n = min(len(idx_c2), max_decisive)
        if keep_n < len(idx_c2):
            drop_indices = np.random.choice(idx_c2, size=len(idx_c2) - keep_n, replace=False)
            clean_mask.loc[drop_indices] = False

    targets = label_df["target_class"]
    print(f"  Phân bố sau Downsample: {label_df.loc[clean_mask, 'target_class'].value_counts().to_dict()}")

    # 3. XỬ LÝ FEATURE ENGINEERING CHO TỪNG NHÁNH MTF_INPUTS
    print(f"\\n[2] Feature Engineering Độc Lập Cho Từng MTF_INPUTS...", flush=True)
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
        # Luôn kèm theo TARGET_close để tính corr_60
        required_cols = list(set(sym_cols + [actual_close]))
        df_sym_raw = df_raw_1m[required_cols].copy()
        
        # 3.2 Resample theo Timeframe
        df_tf = resample_dataframe(df_sym_raw, freq)
        dfs_mtf.append(df_tf)
        window_sizes.append(w)
        
        # 3.3 Gọi FeatureEngineeringV3
        # Trick: Đặt target_prefix thành sym để nó tính toán các chỉ báo nội tại của sym.
        # Đặt macro_features = {TARGET_SYMBOL: []} để nó tính tương quan với TARGET_SYMBOL.
        fe = FeatureEngineeringV3(
            target_prefix=sym,
            macro_features={target_sym: ["corr_60"]} if sym != target_sym else {},
            crypto_mode=fe_cfg.get("CRYPTO_MODE", False)
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
        weekly_split=args.weekly_split
    )

    print(f"\\n👉 KẾT QUẢ: Y={Y.shape}")
    for i, xt in enumerate(X_tensors):
        print(f"  X_tf{i} ({mtf_inputs[i]['SYMBOL']}-{mtf_inputs[i]['TIMEFRAME']}): {xt.shape}")

    # [5] LƯU CỤC BỘ
    y_path = os.path.join(out_dir, f"Y_tensor_{cfg_id}.npy")
    np.save(y_path, Y)
    
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

    print(f"\\n✅ Đã lưu tensor MTF Heterogeneous cục bộ tại: {out_dir}/", flush=True)

if __name__ == "__main__":
    main()
"""

    code = code.replace(old_main, new_main)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("XONG")

if __name__ == "__main__":
    refactor_prepare()
