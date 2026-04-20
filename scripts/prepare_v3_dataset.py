# -*- coding: utf-8 -*-
"""
Script chuẩn bị dữ liệu V3.1 cho CFG_LTC_CRYPTO_V3.
Tích hợp:
  - Giải pháp C (Clean Data Diet): chỉ giữ setup TP trong <= FAST_HIT_BARS nến.
  - Fail-fast: dừng ngay khi gặp lỗi, không tiếp tục với dữ liệu bẩn.
  - Upload lên HuggingFace sau khi xác thực tensor thành công.
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

# ─────────────────────────────────────────────────────────────────────────────
# FAIL-FAST HELPER
# ─────────────────────────────────────────────────────────────────────────────
def abort(msg: str):
    """In lỗi đỏ và dừng toàn bộ tiến trình ngay lập tức."""
    print(f"\n💥 ABORT: {msg}", flush=True)
    sys.exit(1)


def assert_ok(condition: bool, msg: str):
    """Kiểm tra điều kiện - dừng ngay nếu sai."""
    if not condition:
        abort(msg)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD PARQUET CRYPTO
# ─────────────────────────────────────────────────────────────────────────────
def load_crypto_parquets(raw_dir: str, target_symbol: str, target_prefix: str,
                          macro_features: dict, dataset_suffix: str = "2026"):
    """
    Đọc các file parquet Binance + MT5 theo danh sách macro_features trong config.
    Fail-fast nếu thiếu bất kỳ symbol bắt buộc nào.
    """
    print(f"\n[LOAD] Quét thư mục: {raw_dir}", flush=True)
    all_files = [f for f in os.listdir(raw_dir) if f.endswith(".parquet")]
    assert_ok(len(all_files) > 0, f"Thư mục {raw_dir} không có file parquet nào!")

    # Xây dựng mapping: symbol -> source
    required_symbols = {}
    
    t_sym = target_symbol.upper()
    file_sym = t_sym[:-1] if t_sym.endswith("M") else t_sym
    if t_sym in ("BTCUSDT", "ETHUSDT", "LTCUSDT"):
        required_symbols[file_sym] = "BINANCE"
    else:
        required_symbols[file_sym] = "MT5"
        
    for sym, _ in macro_features.items():
        sym_up = sym.upper()
        file_sym_macro = sym_up[:-1] if sym_up.endswith("M") else sym_up
        if sym_up in ("BTCUSDT", "ETHUSDT", "LTCUSDT"):
            required_symbols[file_sym_macro] = "BINANCE"
        else:
            required_symbols[file_sym_macro] = "MT5"

    df_list = []
    loaded = set()

    for fname in sorted(all_files):
        fname_upper = fname.upper()
        for sym, source in required_symbols.items():
            if sym in fname_upper and source in fname_upper:
                path = os.path.join(raw_dir, fname)
                df_sym = pd.read_parquet(path)
                if "time" in df_sym.columns:
                    df_sym.set_index("time", inplace=True)
                if df_sym.index.tz is None:
                    df_sym.index = df_sym.index.tz_localize("UTC")
                rename_map = {c: f"{sym}_{c}" for c in df_sym.columns}
                df_sym = df_sym.rename(columns=rename_map)
                df_list.append(df_sym)
                loaded.add(sym)
                print(f"  + {fname} → prefix={sym} ({len(df_sym):,} nến)", flush=True)
                break

    # Kiểm tra thiếu symbol
    missing = set(required_symbols.keys()) - loaded
    assert_ok(len(missing) == 0,
              f"Thiếu dữ liệu cho các symbol: {missing}. "
              f"Hãy chạy crawl_crypto_v3.py trước!")

    # Merge outer join
    df_raw = df_list[0].copy()
    for df_next in df_list[1:]:
        df_raw = df_raw.join(df_next, how="outer")
    df_raw = df_raw.sort_index().ffill(limit=5)

    print(f"  ✅ df_raw tổng hợp: {df_raw.shape[0]:,} dòng × {df_raw.shape[1]} cột", flush=True)
    return df_raw


# ─────────────────────────────────────────────────────────────────────────────
# BUILD TENSOR WITH SESSION FILTER
# ─────────────────────────────────────────────────────────────────────────────
def build_tensor(df_features: pd.DataFrame, labels_series: pd.Series,
                 clean_mask: pd.Series,
                 session_start: str, session_end: str,
                 window_size: int = 20, step_size: int = 1):
    """
    Tạo tensor X/Y với 2 lớp lọc:
    1. Session filter: chỉ lấy window mà nến mục tiêu trong session
    2. Clean mask: chỉ lấy window có nhãn "Chân Sóng Vĩ Đại" (Giải pháp C)
    """
    try:
        sh, sm = map(int, session_start.split(":"))
        eh, em = map(int, session_end.split(":"))
        start_min = sh * 60 + sm
        end_min   = eh * 60 + em
    except Exception:
        start_min, end_min = 0, 1439

    feature_vals = df_features.values
    label_vals   = labels_series.values
    clean_vals   = clean_mask.values         # boolean array aligned to df_features
    timestamps   = df_features.index

    X_list, Y_list = [], []
    max_idx = len(feature_vals) - window_size

    n_skip_session = 0
    n_skip_clean   = 0
    n_skip_nan     = 0

    for i in tqdm(range(0, max_idx, step_size), desc="Ráp Tensor + Lọc"):
        target_idx  = i + window_size - 1
        target_time = timestamps[target_idx]

        # Lọc Session
        tim = target_time.hour * 60 + target_time.minute
        if start_min <= end_min:
            in_session = (start_min <= tim <= end_min)
        else:
            in_session = (tim >= start_min) or (tim <= end_min)

        if not in_session:
            n_skip_session += 1
            continue

        # Lọc Clean Data Diet (Giải pháp C)
        if not clean_vals[target_idx]:
            n_skip_clean += 1
            continue

        window = feature_vals[i: i + window_size]
        target_label = label_vals[target_idx]

        if np.isnan(window).any() or np.isnan(target_label):
            n_skip_nan += 1
            continue

        X_list.append(window)
        Y_list.append(target_label)

    print(f"  Bỏ qua (ngoài session): {n_skip_session:,}", flush=True)
    print(f"  Bỏ qua (clean mask):    {n_skip_clean:,}", flush=True)
    print(f"  Bỏ qua (NaN):          {n_skip_nan:,}", flush=True)
    print(f"  Giữ lại:               {len(X_list):,}", flush=True)

    return np.array(X_list, dtype=np.float32), np.array(Y_list, dtype=np.int64)


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATE TENSORS (FAIL-FAST)
# ─────────────────────────────────────────────────────────────────────────────
def validate_tensors(X: np.ndarray, Y: np.ndarray, cfg_id: str):
    """Kiểm tra tensor trước khi upload. Dừng ngay nếu có vấn đề."""
    print(f"\n[VALIDATE] Kiểm tra tensor {cfg_id}...", flush=True)

    assert_ok(len(X) > 0 and len(Y) > 0,
              f"Tensor rỗng! X={X.shape}, Y={Y.shape}. "
              f"Có thể do FAST_HIT_BARS quá nhỏ hoặc thiếu data!")
    assert_ok(X.shape[0] == Y.shape[0],
              f"Kích thước không khớp: X={X.shape[0]}, Y={Y.shape[0]}!")

    # Kiểm tra scale
    x_abs_max = float(np.abs(X).max())
    x_mean    = float(np.abs(X).mean())
    print(f"  X abs_max={x_abs_max:.4f} | abs_mean={x_mean:.4f}", flush=True)
    assert_ok(x_abs_max <= 100,
              f"Tensor chưa scale! abs_max={x_abs_max:.1f} >> 100. "
              f"Kiểm tra lại RobustScaler.")

    # Kiểm tra phân bố nhãn
    unique, counts = np.unique(Y, return_counts=True)
    dist = dict(zip(unique.tolist(), counts.tolist()))
    print(f"  Phân bố nhãn Y: {dist}", flush=True)
    assert_ok(len(unique) >= 2,
              f"Chỉ có {len(unique)} class trong Y! "
              f"Data không đủ đa dạng sau khi lọc Clean Mask.")
    # Cảnh báo nếu mất cân bằng nghiêm trọng (> 95% một class)
    max_ratio = max(counts) / sum(counts)
    if max_ratio > 0.95:
        print(f"  ⚠️ CẢNH BÁO: Class mất cân bằng nghiêm trọng ({max_ratio*100:.1f}%)!", flush=True)

    print(f"  ✅ Tensor HỢP LỆ: X={X.shape}, Y={Y.shape}", flush=True)
    return dist


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD TO HUGGINGFACE
# ─────────────────────────────────────────────────────────────────────────────
def upload_to_hf(out_dir: str, cfg_id: str, repo_id: str, hf_token: str):
    """Upload tensor X, Y, scaler lên HuggingFace. Fail-fast nếu upload lỗi."""
    print(f"\n[HF UPLOAD] → {repo_id}", flush=True)
    assert_ok(bool(hf_token), "Không có HF_TOKEN! Set biến môi trường HF_TOKEN hoặc hardcode.")

    api = HfApi(token=hf_token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=True)

    files_to_upload = [
        f"X_tensor_{cfg_id}.npy",
        f"Y_tensor_{cfg_id}.npy",
        f"scaler_{cfg_id}.pkl",
    ]

    for filename in files_to_upload:
        local_path = os.path.join(out_dir, filename)
        assert_ok(os.path.exists(local_path),
                  f"File cục bộ không tìm thấy: {local_path}")

        repo_path = f"data/{cfg_id}/{filename}"
        size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"  ☁️  Uploading {filename} ({size_mb:.2f} MB)...", flush=True)

        try:
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=repo_path,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"[V3.1 Clean Diet] Update {filename}"
            )
            print(f"  ✅ Đã push: {repo_path}", flush=True)
        except Exception as e:
            abort(f"Upload HF thất bại cho {filename}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="data/bot_config_ltc_crypto_v3.json")
    parser.add_argument("--fast-hit-bars", type=int, default=3,
                        help="[Giải pháp C] Số nến tối đa để TP được coi là 'Chân Sóng Vĩ Đại'.")
    parser.add_argument("--no-upload", action="store_true", help="Bỏ qua upload HF (chỉ build local)")
    args = parser.parse_args()

    # ── 1. ĐỌC CONFIG ──────────────────────────────────────────────────────
    assert_ok(os.path.exists(args.config), f"File config không tồn tại: {args.config}")
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    cfg_id        = config.get("CONFIG_ID", "V3_UNKNOWN")
    target_sym    = config.get("TARGET_SYMBOL", "LTCUSDT")
    target_prefix = config.get("TARGET_PREFIX", "LTC")
    fe_cfg        = config["FEATURE_ENGINEERING"]
    session_start = config.get("SESSION_UTC", {}).get("START", "00:00")
    session_end   = config.get("SESSION_UTC", {}).get("END",   "23:59")
    raw_dir       = config.get("DATA_SOURCE", {}).get("RAW_LOCAL_DIR", "data/history")
    out_dir       = os.path.join("data", cfg_id)
    os.makedirs(out_dir, exist_ok=True)

    FAST_HIT_BARS = args.fast_hit_bars
    print(f"\n{'='*70}", flush=True)
    print(f"🔥 CHUẨN BỊ DỮ LIỆU V3.1 (CLEAN DATA DIET): {cfg_id}", flush=True)
    print(f"   Fast-Hit Filter: TP phải chạm trong <= {FAST_HIT_BARS} nến", flush=True)
    print(f"{'='*70}", flush=True)

    # ── 2. ĐỌC PARQUET DATA ────────────────────────────────────────────────
    macro_features = fe_cfg.get("MACRO_FEATURES", {})
    df_raw = load_crypto_parquets(
        raw_dir, target_sym, target_prefix, macro_features,
        dataset_suffix=config.get("DATA_SOURCE", {}).get("DATASET_SUFFIX", "2026")
    )
    
    resample_freq = config.get("DATA_SOURCE", {}).get("RESAMPLE_FREQ", None)
    if resample_freq:
        print(f"\n[1.5] Resample dữ liệu về khung {resample_freq}...", flush=True)
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
                
        df_raw = df_raw.resample(resample_freq).agg(agg_dict).dropna()
        print(f"  ✅ df_raw SAU resample: {df_raw.shape}", flush=True)

    # Xác định cột OHLC thực tế (flex prefix)
    sym_up = target_sym.upper()
    if sym_up.endswith("M"): sym_up = sym_up[:-1]
    actual_open = f"{sym_up}_open"
    actual_high = f"{sym_up}_high"
    actual_low  = f"{sym_up}_low"
    for col in [actual_open, actual_high, actual_low]:
        assert_ok(col in df_raw.columns,
                  f"Thiếu cột {col} trong df_raw! Columns có: {list(df_raw.columns[:10])}")

    # ── 3. GẮNG NHÃN FAST-HIT (GIẢI PHÁP C) ───────────────────────────────
    print(f"\n[1] Gắn nhãn Triple-Barrier + Fast-Hit Filter (Giải pháp C)...", flush=True)
    label_mode = fe_cfg.get("LABEL_MODE", "pip")
    labeler = LabelingV3(
        max_hold_bars=fe_cfg["MAX_HOLD_BARS"],
        label_mode=label_mode,
        tp_pct=fe_cfg.get("TP_PCT", 0.003),
        sl_pct=fe_cfg.get("SL_PCT", 0.003),
        pip_size=fe_cfg.get("PIP_SIZE", 0.01)
    )
    print(f"  TP={fe_cfg.get('TP_PCT',0.003)*100:.2f}% | SL={fe_cfg.get('SL_PCT',0.003)*100:.2f}% | MaxHold={fe_cfg['MAX_HOLD_BARS']}",
          flush=True)

    label_df = labeler.apply_triple_barrier_fast_hit(df_raw, actual_open, actual_high, actual_low)
    clean_mask = labeler.get_clean_mask(label_df, fast_hit_bars=FAST_HIT_BARS)

    total  = len(label_df)
    n_clean = int(clean_mask.sum())
    print(f"  Tổng: {total:,} nến | Sạch (TP<={FAST_HIT_BARS}): {n_clean:,} ({n_clean/total*100:.1f}%)",
          flush=True)
    dist_full = label_df["target_class"].value_counts().to_dict()
    dist_clean = label_df.loc[clean_mask, "target_class"].value_counts().to_dict()
    print(f"  Toàn bộ phân bố  : {dist_full}", flush=True)
    print(f"  Sau Clean Diet    : {dist_clean}", flush=True)

    assert_ok(n_clean >= 500,
              f"Chỉ có {n_clean} mẫu sạch sau khi lọc FAST_HIT_BARS={FAST_HIT_BARS}. "
              f"Hãy tăng fast_hit_bars hoặc kiểm tra lại TP_PCT/SL_PCT!")

    # Labels series (chỉ lấy class, không lấy hit_bars)
    targets = label_df["target_class"]

    # ── 4. FEATURE ENGINEERING ─────────────────────────────────────────────
    print(f"\n[2] Feature Engineering V3 (Macro: {list(macro_features.keys())})...", flush=True)
    target_prefix_mapped = target_prefix.upper()
    if target_prefix_mapped.endswith("M"): target_prefix_mapped = target_prefix_mapped[:-1]
    # Re-append USDT if it's Crypto, but wait, XAUUSD doesn't need USDT appended if target_prefix is already XAUUSD.
    # Actually, for crypto it was f"{target_prefix.upper()}USDT".
    # But for Forex it's just XAUUSD.
    if fe_cfg.get("CRYPTO_MODE", False):
        target_prefix_mapped = f"{target_prefix_mapped}USDT"
    
    assert_ok(f"{target_prefix_mapped}_open".lower() in [c.lower() for c in df_raw.columns],
              f"Không tìm thấy cột open cho prefix '{target_prefix_mapped}'!")

    fe = FeatureEngineeringV3(
        target_prefix=target_prefix_mapped,
        macro_features=macro_features,
        crypto_mode=fe_cfg.get("CRYPTO_MODE", False)
    )
    df_features = fe.process_features(df_raw)
    assert_ok(not df_features.empty, "df_features rỗng sau process_features!")
    assert_ok(df_features.isnull().mean().max() < 0.5,
              f"Có cột feature quá nhiều NaN: {df_features.isnull().mean().idxmax()}")

    print(f"  ✅ Features: {df_features.shape} ({df_features.columns.tolist()[:5]}...)", flush=True)

    # ── 5. SCALE ───────────────────────────────────────────────────────────
    print(f"\n[3] Robust Scaler...", flush=True)
    df_scaled = fe.fit_transform_scaler(df_features)

    # Đồng bộ index
    idx_common = df_scaled.index.intersection(targets.index).intersection(clean_mask.index)
    assert_ok(len(idx_common) > 0, "Index giao nhau rỗng sau khi đồng bộ!")
    df_scaled  = df_scaled.loc[idx_common]
    targets    = targets.loc[idx_common]
    clean_mask = clean_mask.loc[idx_common]

    # ── 6. BUILD TENSOR ─────────────────────────────────────────────────────
    print(f"\n[4] Ráp Tensor (Window={fe_cfg['WINDOW_SIZE']}, Session={session_start}-{session_end})...",
          flush=True)
    X, Y = build_tensor(
        df_scaled, targets, clean_mask,
        session_start=session_start, session_end=session_end,
        window_size=fe_cfg["WINDOW_SIZE"], step_size=fe_cfg.get("STEP_SIZE", 1)
    )
    print(f"\n👉 KẾT QUẢ: X={X.shape}, Y={Y.shape}", flush=True)

    # ── 7. VALIDATE ─────────────────────────────────────────────────────────
    validate_tensors(X, Y, cfg_id)

    # ── 8. LƯU CỤC BỘ ──────────────────────────────────────────────────────
    x_path      = os.path.join(out_dir, f"X_tensor_{cfg_id}.npy")
    y_path      = os.path.join(out_dir, f"Y_tensor_{cfg_id}.npy")
    scaler_path = os.path.join(out_dir, f"scaler_{cfg_id}.pkl")

    np.save(x_path, X)
    np.save(y_path, Y)
    
    # Lưu scaler + column_order để đảm bảo thứ tự cột khớp hoàn hảo khi live inference
    scaler_bundle = {
        "scaler": fe.scaler,
        "column_order": list(df_scaled.columns),
    }
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler_bundle, f)
    print(f"  📐 Column order ({len(df_scaled.columns)} cột): {list(df_scaled.columns)[:5]}...", flush=True)
    print(f"\n✅ Đã lưu tensor cục bộ tại: {out_dir}/", flush=True)

    # ── 9. UPLOAD HF ────────────────────────────────────────────────────────
    if not args.no_upload:
        repo_id   = config.get("HF_CLOUD", {}).get("DATASET_REPO", "dung5k/ltc_v3_tensor_crypto")
        hf_token  = os.environ.get("HF_TOKEN", "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")
        upload_to_hf(out_dir, cfg_id, repo_id, hf_token)
    else:
        print("\n⏭️  Bỏ qua upload HF (--no-upload).", flush=True)

    print(f"\n🎉 HOÀN TẤT! {cfg_id} sẵn sàng cho training V3.1 Selective Sniper!", flush=True)


if __name__ == "__main__":
    main()
