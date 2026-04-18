import os
import sys
import json
import torch
import numpy as np
import pandas as pd
from datetime import datetime
from huggingface_hub import hf_hub_download
import shutil
import pickle
from tqdm import tqdm

# Khai báo đường dẫn root để import src
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3
from src.core.feature_engineering import load_and_align_data
from src.training_v3.model_v3 import AAMT_Model

def filter_by_session(df, start_utc_str, end_utc_str):
    try:
        start_h, start_m = map(int, start_utc_str.split(':'))
        end_h, end_m = map(int, end_utc_str.split(':'))
    except:
        return df

    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    
    hours = df.index.hour
    minutes = df.index.minute
    time_in_minutes = hours * 60 + minutes
    
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m
    
    if start_min <= end_min:
        mask = (time_in_minutes >= start_min) & (time_in_minutes <= end_min)
    else:
        mask = (time_in_minutes >= start_min) | (time_in_minutes <= end_min)
        
    return df[mask].copy()

def export_indicator_csv(run_id: str):
    print(f"=== BẮT ĐẦU XUẤT DỮ LIỆU INDICATOR V3 ===")
    print(f"Run ID: {run_id}")
    
    config_path = os.path.join(_ROOT, "data", "indicator_config_xau_ny_v3.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    fe_cfg = config['FEATURE_ENGINEERING']
    train_cfg = config['TRAINING']
    target_prefix = config.get('TARGET_PREFIX', 'XAUUSD')
    
    hf_token = os.environ.get("HF_TOKEN", "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")
    
    # Kéo resources từ HF
    print("- Đang tải Scaler và Trọng số Mô hình từ HF...")
    try:
        scaler_path = hf_hub_download(repo_id="dung5k/xau_v3_tensor_ny", filename=f"data/{config['CONFIG_ID'].replace('_INDICATOR', '')}/scaler_{config['CONFIG_ID'].replace('_INDICATOR', '')}.pkl", repo_type="dataset", token=hf_token)
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        print("  => Đã load Scaler thành công.")
    except Exception as e:
        print(f"  ❌ Lỗi tải Scaler (Bạn kiểm tra lại filename): {e}")
        return

    try:
        weights_path = hf_hub_download(repo_id="dung5k/argo_data", filename=f"runs/{run_id}/aamt_v3_{config['CONFIG_ID'].replace('_INDICATOR', '')}_final.pth", repo_type="dataset", token=hf_token)

        print("  => Đã load Model Weights thành công.")
    except Exception as e:
        print(f"  ❌ Lỗi tải Weights: {e}")
        return

    # Load dữ liệu Parquet
    print(f"- Đang trích xuất dữ liệu Lịch sử (nến Local Parquet) để làm Base...")
    raw_dir = os.path.join(_ROOT, config["DATA_SOURCE"]["RAW_LOCAL_DIR"])
    try:
        df_raw = load_and_align_data(raw_dir)
        if 'time' in df_raw.columns:
            df_raw.set_index('time', inplace=True)
    except Exception as e:
        print(f"❌ Lỗi tải dữ liệu parquet: {e}")
        return

    print("  => Độ dài raw data:", len(df_raw))
    
    # Khởi tạo FE và Scale
    fe = FeatureEngineeringV3(target_prefix=target_prefix, macro_features=fe_cfg.get('MACRO_FEATURES', {}))
    fe.scaler = scaler
    fe.is_fitted = True
    
    df_features = fe.process_features(df_raw)
    
    session_start = config.get('SESSION_UTC', {}).get('START', '13:00')
    session_end = config.get('SESSION_UTC', {}).get('END', '22:00')
    df_features = filter_by_session(df_features, session_start, session_end)
    
    df_scaled = fe.transform_scaler(df_features)
    
    # Khởi tạo Model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = AAMT_Model(
        input_dim=df_scaled.shape[1], 
        seq_len=fe_cfg['WINDOW_SIZE'],
        d_model=train_cfg['D_MODEL'],
        nhead=train_cfg['N_HEAD'],
        num_layers=train_cfg['NUM_LAYERS'],
        num_classes=3
    ).to(device)
    
    model.load_state_dict(torch.load(weights_path, map_location=device, weights_only=True))
    model.eval()

    # Quét Tensor tạo CSV
    window_size = fe_cfg['WINDOW_SIZE']
    feature_vals = df_scaled.values
    timestamps = df_scaled.index
    
    # Lấy 10,000 nến gần nhất để xuất ra indicator cho đỡ nặng MT5
    max_history = 10000 
    
    csv_lines = []
    print("- Bắt đầu Inference chạy Slide Window...")
    
    with torch.no_grad():
        start_idx = max(0, len(feature_vals) - max_history - window_size)
        
        for i in tqdm(range(start_idx, len(feature_vals) - window_size)):
            window = feature_vals[i : i + window_size]
            if np.isnan(window).any():
                continue
                
            # Numpy -> Tensor
            x_tensor = torch.tensor(window, dtype=torch.float32).unsqueeze(0).to(device)
            _, logits, _ = model(x_tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
            
            # probs[0] = Sell, probs[1] = Sideway, probs[2] = Buy
            prob_sell = probs[0]
            prob_hold = probs[1]
            prob_buy = probs[2]
            
            # Công thức Oscillator: Giá trị [-1, 1], dương là Buy, âm là Sell
            diff_prob = prob_buy - prob_sell
            
            # Thời điểm của nến hiện tại (tại thời điểm ra quyết định cho nến tương lai)
            current_time = timestamps[i + window_size - 1]
            t = int(current_time.timestamp())
            
            csv_lines.append(f"{t},{diff_prob:.4f}")

    out_dir = os.path.join(os.environ.get("APPDATA", ""), "MetaQuotes", "Terminal", "Common", "Files")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "ai_predictions_v3.csv")
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))
        
    print(f"✅ THÀNH CÔNG! Đã dự báo xong {len(csv_lines)} nến.")
    print(f"👉 Đã lưu file: {out_file}")

if __name__ == "__main__":
    target_run = "run_20260418_102449_v3_CFG_XAU_NY_V3_1"
    if len(sys.argv) > 1:
        target_run = sys.argv[1]
    export_indicator_csv(target_run)
