import os
import sys
import pandas as pd
import numpy as np
import json
import argparse
from tqdm import tqdm
from huggingface_hub import HfApi, login

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3, LabelingV3

def build_tensor_dataset(df_features, labels_series, window_size=60, step_size=1):
    """
    Trượt cửa sổ [Batch, Seq, Features] từ Pandas DataFrame.
    """
    feature_vals = df_features.values
    label_vals = labels_series.values
    
    X_list = []
    Y_list = []
    
    # Do nhãn Triple-Barrier có tính Look-ahead (nhìn trước tương lai max_hold_bars nến)
    # nên các cây nến ở sát viền hiện tại (ví dụ 20 nến cuối) có thể chưa rõ TP/SL.
    # Trong Labeling class chúng ta đã trả về 2 (Sideway). Ở đây giữ nguyên.
    
    max_idx = len(feature_vals) - window_size
    for i in tqdm(range(0, max_idx, step_size), desc="Đang trượt Tensor Window"):
        window = feature_vals[i : i + window_size]
        
        # Nhãn dự đoán tương lai là nhãn CỦA CÂY NẾN CUỐI CÙNG TRONG WINDOW
        target_label = label_vals[i + window_size - 1]
        
        # Chỉ lấy những window nào KHÔNG có dòng chứa NaN
        if not np.isnan(window).any() and not np.isnan(target_label):
            X_list.append(window)
            Y_list.append(target_label)
            
    return np.array(X_list, dtype=np.float32), np.array(Y_list, dtype=np.int64)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='data/bot_config_xau_v3_template.json')
    parser.add_argument('--dataset', type=str, default='v3_dummy.parquet')
    parser.add_argument('--token', type=str, default='')
    args = parser.parse_args()
    
    # 1. Đọc mô phỏng config
    with open(args.config, 'r') as f:
        config = json.load(f)
        
    fe_cfg = config['FEATURE_ENGINEERING']
    
    # 2. Extract Features
    print("[1] Tiến hành Trích Xuất 15 Features (V3) trực giao")
    fe = FeatureEngineeringV3(target_prefix=config['TARGET_PREFIX'])
    
    # Đây là mô phỏng đọc file tĩnh (thay cho MT5 raw db). Bot thực tế sẽ gọi pd.read_parquet
    if os.path.exists(args.dataset):
        df_raw = pd.read_parquet(args.dataset)
        
        df_features = fe.process_features(df_raw)
        df_scaled = fe.fit_transform_scaler(df_features)
        
        print(f" -> Feat_Shape: {df_scaled.shape}")
        
        # 3. Gắn nhãn
        print("[2] Gắn nhãn 3-Class Triple Barrier")
        labeler = LabelingV3(
            tp_pips=fe_cfg['TP_PIPS'],
            sl_pips=fe_cfg['SL_PIPS'],
            max_hold_bars=fe_cfg['MAX_HOLD_BARS'],
            pip_size=fe_cfg['PIP_SIZE']
        )
        
        prefix = config['TARGET_PREFIX'].lower()
        targets = labeler.apply_triple_barrier(
            df_raw, 
            f'{prefix}_open', f'{prefix}_high', f'{prefix}_low'
        )
        
        # Đoạn trượt Tensor ở khối dữ liệu lớn:
        window = fe_cfg['WINDOW_SIZE']
        step = fe_cfg['STEP_SIZE']
        
        print(f"[3] Tạo Tensor Mảng 3D [Batch, {window}, 15]")
        X, Y = build_tensor_dataset(df_scaled, targets, window, step)
        print(f" -> Output Tensor: X={X.shape}, Y={Y.shape}")
        
        # HF Upload mô phỏng
        if args.token:
            print(f"[4] Tải thẳng Tensor lên HuggingFace repo: {config['DATA_SOURCE']['HG_DATASET']}")
    else:
        print(f"File mô phỏng {args.dataset} không tồn tại. Tắt tiến trình Upload.")
