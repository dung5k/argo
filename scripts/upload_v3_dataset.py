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


def build_tensor_dataset(df_features, labels_series, window_size=60, step_size=1):
    """Trượt Tensor Window Mảng 3D."""
    feature_vals = df_features.values
    label_vals = labels_series.values
    
    X_list = []
    Y_list = []
    
    max_idx = len(feature_vals) - window_size
    for i in tqdm(range(0, max_idx, step_size), desc="Đang ráp khối Tensor V3"):
        window = feature_vals[i : i + window_size]
        target_label = label_vals[i + window_size - 1]
        
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
        
    cfg_id = config.get('CONFIG_ID', 'V3_UNKNOWN')
    target_sym = config.get('TARGET_SYMBOL', 'XAUUSDm')
    target_prefix = config.get('TARGET_PREFIX', 'XAUUSD')
    fe_cfg = config['FEATURE_ENGINEERING']
    session_start = config.get('SESSION_UTC', {}).get('START', '00:00')
    session_end = config.get('SESSION_UTC', {}).get('END', '23:59')
    
    # 2. Định vị thư mục
    raw_dir = config.get('DATA_SOURCE', {}).get('RAW_LOCAL_DIR', 'data/history')
    out_dir = os.path.join("data", cfg_id)
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"🔥 BẮT ĐẦU CÀO VÀ BỐ TRÍ DỮ LIỆU RIÊNG CHO CẤU HÌNH: {cfg_id}")
    
    # GỌI HÀM V2 ĐỂ GỘP MÚI GIỜ CỦA NHIỀU MÃ RAW VÀO CHUNG 1 DATAFRAME
    os.makedirs(raw_dir, exist_ok=True)
    try:
        df_raw = load_and_align_data(raw_dir)
    except FileNotFoundError:
        df_raw = pd.DataFrame()
        
    if df_raw.empty:
        print(f"❌ Lỗi: Thư mục chứa File Lịch Sử ({raw_dir}) trống không.")
        print("💡 Vui lòng bật Bot MT5 (hoặc cloud_manager_v2.py) cào file parquet các mã Vĩ mô/XAU rồi lưu vào đây trước.")
        sys.exit(1)
        
    if 'time' in df_raw.columns:
        df_raw.set_index('time', inplace=True)
    
    # Xác định prefix linh hoạt (có m hay không có m tùy broker config)
    cols_map = {c.lower(): c for c in df_raw.columns}
    real_prefix = target_prefix.lower()
    if f"{target_prefix.lower()}m_open" in cols_map:
        real_prefix = f"{target_prefix.lower()}m"
        
    actual_open = cols_map.get(f"{real_prefix}_open", f"{target_prefix}_open")
    actual_high = cols_map.get(f"{real_prefix}_high", f"{target_prefix}_high")
    actual_low = cols_map.get(f"{real_prefix}_low", f"{target_prefix}_low")
    
    # Gắn nhãn 3-Class
    print("[1] Gắn nhãn Triple-Barrier...")
    labeler = LabelingV3(
        tp_pips=fe_cfg['TP_PIPS'], sl_pips=fe_cfg['SL_PIPS'], 
        max_hold_bars=fe_cfg['MAX_HOLD_BARS'], pip_size=fe_cfg['PIP_SIZE']
    )
    targets = labeler.apply_triple_barrier(df_raw, actual_open, actual_high, actual_low)
    
    # Feature Eng
    print("[2] Khởi tạo 15 Features XAU + 30 Features Macro (AAMT V3)...")
    fe = FeatureEngineeringV3(target_prefix=target_prefix, macro_features=fe_cfg.get('MACRO_FEATURES', {}))
    df_features = fe.process_features(df_raw)
    
    # Lọc Session Time
    print(f"[3] Xẻ Session Vùng Kín ({session_start} - {session_end})")
    df_features = filter_by_session(df_features, session_start, session_end)
    targets = targets.loc[df_features.index]
    
    # Scale Data
    print("[4] Ép Robust Scaler...")
    df_scaled = fe.fit_transform_scaler(df_features)
    
    # Tensor 3D
    X, Y = build_tensor_dataset(df_scaled, targets, window_size=fe_cfg['WINDOW_SIZE'], step_size=fe_cfg['STEP_SIZE'])
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
    repo_id = config.get("HF_CLOUD", {}).get("DATASET_REPO", "dung5k/xau_v3_tensor_ny")
    hf_token = os.environ.get("HF_TOKEN")
    
    if not hf_token:
        hf_token = "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"
                
    if not hf_token:
        print("⚠️ BỎ QUA UPLOAD: Không tìm thấy HuggingFace Token trong môi trường.")
        sys.exit(0)
        
    api = HfApi(token=hf_token)
    
    files_to_upload = [
        f"X_tensor_{cfg_id}.npy",
        f"Y_tensor_{cfg_id}.npy",
        f"scaler_{cfg_id}.pkl"
    ]
    
    for filename in files_to_upload:
        local_path = os.path.join(out_dir, filename)
        repo_path = f"data/{cfg_id}/{filename}"
        
        if not os.path.exists(local_path):
            print(f"❌ LỖI NGHIÊM TRỌNG: Không tìm thấy file tại Local: {local_path}")
            continue
            
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
