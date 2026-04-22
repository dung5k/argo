import os
import sys
import pandas as pd
import numpy as np
import json
import argparse
from tqdm import tqdm
import pickle
from huggingface_hub import HfApi

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3, LabelingV3
from src.core.feature_engineering import load_and_align_data

def filter_by_session(df, start_utc_str, end_utc_str):
    """Lọc dữ liệu Pandas chỉ lấy những hàng nằm trong khung giờ Session UTC."""
    try:
        start_h, start_m = map(int, start_utc_str.split(':'))
        end_h, end_m = map(int, end_utc_str.split(':'))
    except Exception as e:
        print(f"Cảnh báo: Lỗi parse SESSION_UTC = {start_utc_str}-{end_utc_str}. Giữ nguyên toàn bộ Data.")
        return df

    # Đảm bảo index timezone aware
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    
    # Tính mask
    hours = df.index.hour
    minutes = df.index.minute
    time_in_minutes = hours * 60 + minutes
    
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m
    
    if start_min <= end_min:
        mask = (time_in_minutes >= start_min) & (time_in_minutes <= end_min)
    else:
        # Xuyên qua nửa đêm
        mask = (time_in_minutes >= start_min) | (time_in_minutes <= end_min)
        
    filtered = df[mask].copy()
    print(f"  + Lọc Session {start_utc_str}-{end_utc_str}: Giữ lại {len(filtered)} / {len(df)} nến.")
    return filtered


def build_tensor_dataset_with_session(df_features, labels_series, start_utc_str, end_utc_str, window_size=60, step_size=1):
    """
    Trượt Tensor trên Data liên tục 24/24.
    Sau đó chỉ giữ lại các Window mà Nến mục tiêu (Target Candle - nến CUỐI cửa sổ)
    nằm trong khung giờ Session quy định.
    → Tránh hiện tượng ghép nến qua đêm (Time-Series Rupture).
    """
    try:
        start_h, start_m = map(int, start_utc_str.split(':'))
        end_h, end_m     = map(int, end_utc_str.split(':'))
        start_min = start_h * 60 + start_m
        end_min   = end_h   * 60 + end_m
    except Exception:
        start_min, end_min = 0, 1439  # Mặc định cả ngày

    feature_vals = df_features.values
    label_vals   = labels_series.values
    timestamps   = df_features.index  # Lấy trục thời gian thực

    X_list, Y_list = [], []
    max_idx = len(feature_vals) - window_size
    for i in tqdm(range(0, max_idx, step_size), desc="Đang ráp khối Tensor V3"):
        target_idx  = i + window_size - 1
        target_time = timestamps[target_idx]

        # Kiểm tra nến mục tiêu có nằm trong Session không
        time_in_minutes = target_time.hour * 60 + target_time.minute
        if start_min <= end_min:
            in_session = (start_min <= time_in_minutes <= end_min)
        else:  # Phiên xuyên nửa đêm
            in_session = (time_in_minutes >= start_min) or (time_in_minutes <= end_min)

        if not in_session:
            continue

        window       = feature_vals[i: i + window_size]
        target_label = label_vals[target_idx]

        if not np.isnan(window).any() and not np.isnan(target_label):
            X_list.append(window)
            Y_list.append(target_label)

    return np.array(X_list, dtype=np.float32), np.array(Y_list, dtype=np.int64)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='data/bot_config_xau_ny_v3.json')
    args = parser.parse_args()

    # 1. Đọc config
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    cfg_id        = config.get('CONFIG_ID', 'V3_UNKNOWN')
    target_sym    = config.get('TARGET_SYMBOL', 'XAUUSDm')
    target_prefix = config.get('TARGET_PREFIX', 'XAUUSD')
    fe_cfg        = config['FEATURE_ENGINEERING']
    session_start = config.get('SESSION_UTC', {}).get('START', '00:00')
    session_end   = config.get('SESSION_UTC', {}).get('END', '23:59')

    # 2. Định vị thư mục theo chuẩn Run-Based
    import datetime
    import shutil
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}_v3"
    run_dir = os.path.join("workspaces", cfg_id, "runs", run_id)
    out_dir = os.path.join(run_dir, "data", "tensors")
    
    os.makedirs(out_dir, exist_ok=True)
    raw_dir = config.get('DATA_SOURCE', {}).get('RAW_LOCAL_DIR', 'data/history')
    os.makedirs(raw_dir, exist_ok=True)
    
    # Lưu bản sao config vào lượt chạy
    run_config_path = os.path.join(run_dir, "config.json")
    shutil.copy(args.config, run_config_path)
    print(f"📁 Đã tạo Lượt chạy mới: {run_id}")

    print(f"🔥 BẮT ĐẦU CÀO VÀ BỐ TRÍ DỮ LIỆU RIÊNG CHO CẤU HÌNH: {cfg_id}")

    crypto_mode_data = fe_cfg.get('CRYPTO_MODE', False)

    if crypto_mode_data:
        # --- Chế độ Crypto: đọc trực tiếp từ file parquet Binance theo danh sách config ---
        print("  [Crypto] Đọc trực tiếp file parquet Binance (bỏ qua load_and_align_data)...")
        binance_cfg = config.get('DATA_SOURCE', {}).get('CRYPTO_BINANCE', {})
        mt5_routing  = config.get('DATA_SOURCE', {}).get('ROUTING', {})
        # Danh sách tất cả mã cần: target + macro
        all_syms = {config.get('TARGET_SYMBOL', '').upper().replace('M', '')}  # ETH/USDT → ETHUSDT
        all_syms.add(config.get('TARGET_SYMBOL', '').upper())  # ETHUSDT
        for sym in fe_cfg.get('MACRO_FEATURES', {}).keys():
            all_syms.add(sym.upper())  # BTCUSDT, ETHBTC, USTECm
        # Đọc từng file và gộp
        df_list = []
        for fname in os.listdir(raw_dir):
            if not fname.endswith('.parquet'):
                continue
            # Lấy symbol name từ tên file: ETHUSDT_MT5_1M_2026.parquet → ETHUSDT
            if '_MT5_' in fname:
                sym_raw = fname.split('_MT5_')[0].upper()
            elif '_BINANCE_' in fname:
                sym_raw = fname.split('_BINANCE_')[0].upper()
            else:
                sym_raw = fname.split('_')[0].upper()
            # Kiểm tra có trong danh sách cần thiết không
            matched = any(sym_raw == s.upper() or sym_raw == s.upper().rstrip('M')
                          for s in all_syms)
            if not matched:
                continue
            df_sym = pd.read_parquet(os.path.join(raw_dir, fname))
            if 'time' in df_sym.columns:
                df_sym.set_index('time', inplace=True)
            if df_sym.index.tz is None:
                df_sym.index = df_sym.index.tz_localize('UTC')
            # Prefix cột
            rename_map = {c: f"{sym_raw}_{c}" for c in df_sym.columns}
            df_sym = df_sym.rename(columns=rename_map)
            df_list.append(df_sym)
            print(f"  + Đọc: {fname} → prefix={sym_raw} ({len(df_sym)} nến)")

        if not df_list:
            print(f"❌ Không tìm thấy parquet nào phù hợp tại {raw_dir}")
            sys.exit(1)
        df_raw = df_list[0].copy()
        for df_next in df_list[1:]:
            df_raw = df_raw.join(df_next, how='outer')
        df_raw = df_raw.sort_index()
        # Forward fill ngắn (tối đa 5 phút) để xử lý lệch timestamp nhỏ
        df_raw = df_raw.ffill(limit=5)
        print(f"  ✅ Crypto df_raw: {df_raw.shape[0]} dòng x {df_raw.shape[1]} cột")
    else:
        # --- Chế độ Forex/Vàng: dùng hàm gộp cũ ---
        try:
            df_raw = load_and_align_data(raw_dir)
        except FileNotFoundError:
            df_raw = pd.DataFrame()

    if df_raw is None or df_raw.empty:
        print(f"❌ Lỗi: Thư mục chứa File Lịch Sử ({raw_dir}) trống không.")
        sys.exit(1)

    if 'time' in df_raw.columns:
        df_raw.set_index('time', inplace=True)

    # Xác định prefix linh hoạt (Forex: XAUUSDm → xauusdm, Crypto: ETH → ethusdt)
    cols_map    = {c.lower(): c for c in df_raw.columns}
    real_prefix = target_prefix.lower()

    # Kiểm tra dạng có 'm' suffix (broker Exness: XAUUSDm)
    if f"{target_prefix.lower()}m_open" in cols_map:
        real_prefix = f"{target_prefix.lower()}m"
    # Kiểm tra dạng có 'usdt' suffix (Binance Crypto: ETHUSDT)
    elif f"{target_prefix.lower()}usdt_open" in cols_map:
        real_prefix = f"{target_prefix.lower()}usdt"

    actual_open = cols_map.get(f"{real_prefix}_open", f"{target_prefix}_open")
    actual_high = cols_map.get(f"{real_prefix}_high", f"{target_prefix}_high")
    actual_low  = cols_map.get(f"{real_prefix}_low",  f"{target_prefix}_low")

    # Cập nhật TARGET_PREFIX để FeatureEngineeringV3 tìm đúng cột
    target_prefix_mapped = real_prefix.upper()

    # Gắn nhãn 3-Class trên dữ liệu 24/24 (hardé LabelingV3 nhìn đủ ngữ cảnh giá thật)
    print("[1] Gắn nhãn Triple-Barrier trên Data 24/24...")
    label_mode = fe_cfg.get('LABEL_MODE', 'pip')  # 'pip' (Forex) hoặc 'pct' (Crypto)
    if label_mode == 'pct':
        labeler = LabelingV3(
            max_hold_bars=fe_cfg['MAX_HOLD_BARS'],
            label_mode='pct',
            tp_pct=fe_cfg.get('TP_PCT', 0.003),
            sl_pct=fe_cfg.get('SL_PCT', 0.003),
            pip_size=fe_cfg.get('PIP_SIZE', 0.01)
        )
        print(f"  [Crypto mode] TP={fe_cfg.get('TP_PCT',0.003)*100:.2f}% | SL={fe_cfg.get('SL_PCT',0.003)*100:.2f}%")
    else:
        labeler = LabelingV3(
            tp_pips=fe_cfg.get('TP_PIPS', 10), sl_pips=fe_cfg.get('SL_PIPS', 10),
            max_hold_bars=fe_cfg['MAX_HOLD_BARS'], pip_size=fe_cfg['PIP_SIZE']
        )
    targets = labeler.apply_triple_barrier(df_raw, actual_open, actual_high, actual_low)

    # Feature Eng trên dữ liệu 24/24 (để Scaler hiểu toàn bộ biến động)
    print(f"[2] Khởi tạo Features Target ({target_prefix_mapped}) + Macro (AAMT V3)...")
    crypto_mode = fe_cfg.get('CRYPTO_MODE', False)
    fe = FeatureEngineeringV3(
        target_prefix=target_prefix_mapped,
        macro_features=fe_cfg.get('MACRO_FEATURES', {}),
        crypto_mode=crypto_mode
    )
    df_features = fe.process_features(df_raw)

    # Scale Data trên dữ liệu 24/24
    print("[3] Ép Robust Scaler...")
    df_scaled = fe.fit_transform_scaler(df_features)

    # Đồng bộ targets với df_scaled (sau khi process_features có thể bị drop row NaN)
    targets = targets.loc[targets.index.isin(df_scaled.index)]
    df_scaled_aligned = df_scaled.loc[df_scaled.index.isin(targets.index)]
    targets = targets.loc[df_scaled_aligned.index]

    # Ráp Tensor VÀ Lọc Session CÙNG LÚC (không còn thủng lỗ hổng thời gian)
    print(f"[4] Xẻ Tensor và Lọc Session ({session_start} - {session_end})...")
    X, Y = build_tensor_dataset_with_session(
        df_scaled_aligned, targets,
        start_utc_str=session_start, end_utc_str=session_end,
        window_size=fe_cfg['WINDOW_SIZE'], step_size=fe_cfg['STEP_SIZE']
    )
    print(f"👉 KẾT QUẢ TENSOR ({cfg_id}): X={X.shape}, Y={Y.shape}")
    
    # Lưu xuống Data Hub cục bộ theo tên Cấu Hình
    x_path = os.path.join(out_dir, f"X_tensor_{cfg_id}.npy")
    y_path = os.path.join(out_dir, f"Y_tensor_{cfg_id}.npy")
    scaler_path = os.path.join(out_dir, f"scaler_{cfg_id}.pkl")
    
    np.save(x_path, X)
    np.save(y_path, Y)
    with open(scaler_path, "wb") as f:
        pickle.dump(fe.scaler, f)
        
    print(f"✅ Đã đóng gói DỮ LIỆU RIÊNG rẽ nhánh cho {cfg_id} tại {out_dir}/")
    print("Bây giờ đã sẵn sàng Train bằng src/training_v3/train_v3.py!")
    
    # Kích hoạt đẩy lên Huggingface
    print(f"\n🚀 TIẾN HÀNH ĐẨY DỮ LIỆU LÊN HUGGINGFACE (V3 STANDARD)...")
    repo_id = "dung5k/argo_workspaces"
    hf_token = os.environ.get("HF_TOKEN")
    
    if not hf_token:
        hf_token = "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"
                
    if not hf_token:
        print("⚠️ BỎ QUA UPLOAD: Không tìm thấy HuggingFace Token trong môi trường.")
        sys.exit(0)
        
    api = HfApi(token=hf_token)
    
    files_to_upload = [
        (os.path.join(out_dir, f"X_tensor_{cfg_id}.npy"), f"workspaces/{cfg_id}/runs/{run_id}/data/tensors/X_tensor_{cfg_id}.npy"),
        (os.path.join(out_dir, f"Y_tensor_{cfg_id}.npy"), f"workspaces/{cfg_id}/runs/{run_id}/data/tensors/Y_tensor_{cfg_id}.npy"),
        (os.path.join(out_dir, f"scaler_{cfg_id}.pkl"), f"workspaces/{cfg_id}/runs/{run_id}/data/tensors/scaler_{cfg_id}.pkl"),
        (run_config_path, f"workspaces/{cfg_id}/runs/{run_id}/config.json"),
        (args.config, f"workspaces/{cfg_id}/base_config.json")
    ]
    
    for local_path, repo_path in files_to_upload:
        
        if not os.path.exists(local_path):
            print(f"❌ LỖI NGHIÊM TRỌNG: Không tìm thấy file tại Local: {local_path}")
            continue
            
        filename = os.path.basename(local_path)
        print(f"☁️ Uploading {filename} (Size: {os.path.getsize(local_path) / (1024*1024):.2f} MB)...")
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=True)
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=repo_path,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"Sync 1-year MT5 Multi-Task Training V3 Data ({filename})"
            )
            print(f"✅ Đã Push thành công: {repo_path}")
        except Exception as e:
            print(f"❌ Lỗi khi Push {filename}: {str(e)}")

    print("\n🎉 HOÀN TẤT TOÀN BỘ QUY TRÌNH CHUẨN BỊ RANDOM-SEED CHO V3!")
