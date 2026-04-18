import os
import sys
import json
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from huggingface_hub import hf_hub_download
import pickle

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
    
    time_in_minutes = df.index.hour * 60 + df.index.minute
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m
    
    if start_min <= end_min:
        mask = (time_in_minutes >= start_min) & (time_in_minutes <= end_min)
    else:
        mask = (time_in_minutes >= start_min) | (time_in_minutes <= end_min)
        
    return df[mask].copy()

def get_candlestick_color(open_p, close_p):
    return '#26a69a' if close_p >= open_p else '#ef5350'

def plot_daily_candlesticks_with_analysis(run_id="run_20260418_102449_v3_CFG_XAU_NY_V3_1"):
    import sys, io
    if sys.stdout is not None:
        try: sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except: pass
        
    print(f"=== BẮT ĐẦU VẼ BIỂU ĐỒ NẾN PHÂN TÍCH V3 ===")
    
    config_path = os.path.join(_ROOT, "data", "indicator_config_xau_ny_v3.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    fe_cfg = config['FEATURE_ENGINEERING']
    train_cfg = config['TRAINING']
    target_prefix = config.get('TARGET_PREFIX', 'XAUUSD')
    
    hf_token = os.environ.get("HF_TOKEN", "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")
    
    print("- Đang tải Scaler và Trọng số...")
    cfg_id_pure = config['CONFIG_ID'].replace('_INDICATOR', '')
    scaler_path = hf_hub_download(repo_id="dung5k/xau_v3_tensor_ny", filename=f"data/{cfg_id_pure}/scaler_{cfg_id_pure}.pkl", repo_type="dataset", token=hf_token)
    weights_path = hf_hub_download(repo_id="dung5k/argo_data", filename=f"runs/{run_id}/aamt_v3_{cfg_id_pure}_final.pth", repo_type="dataset", token=hf_token)
    
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
        
    raw_dir = os.path.join(_ROOT, config["DATA_SOURCE"]["RAW_LOCAL_DIR"])
    df_raw = load_and_align_data(raw_dir)
    if 'time' in df_raw.columns:
        df_raw.set_index('time', inplace=True)
        
    fe = FeatureEngineeringV3(target_prefix=target_prefix, macro_features=fe_cfg.get('MACRO_FEATURES', {}))
    fe.scaler = scaler
    fe.is_fitted = True
    
    df_features = fe.process_features(df_raw)
    
    sess_start = config.get('SESSION_UTC', {}).get('START', '13:00')
    sess_end = config.get('SESSION_UTC', {}).get('END', '22:00')
    df_features = filter_by_session(df_features, sess_start, sess_end)
    df_scaled = fe.transform_scaler(df_features)
    
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

    window_size = fe_cfg['WINDOW_SIZE']
    
    # Lấy dữ liệu 5 ngày cuối theo phiên
    unique_days = np.unique(df_scaled.index.date)
    recent_days = unique_days[-5:]
    
    op_col = f'{target_prefix}_open'
    hi_col = f'{target_prefix}_high'
    lo_col = f'{target_prefix}_low'
    cl_col = f'{target_prefix}_close'
    
    out_dir = os.path.join(_ROOT, "outputs", "v3_charts")
    os.makedirs(out_dir, exist_ok=True)
    
    for day in recent_days:
        day_str = str(day)
        print(f">> Phân tích ngày: {day_str}")
        
        day_data_scaled = df_scaled[df_scaled.index.date == day]
        if len(day_data_scaled) < window_size:
            print(f"Bỏ qua {day_str}: Không đủ nến.")
            continue
            
        timestamps = day_data_scaled.index
        feature_vals = day_data_scaled.values
        
        preds_sell, preds_hold, preds_buy, mses = [], [], [], []
        plot_times = timestamps[window_size:]
        
        with torch.no_grad():
            for i in range(len(feature_vals) - window_size):
                window = feature_vals[i : i + window_size]
                x_tensor = torch.tensor(window, dtype=torch.float32).unsqueeze(0).to(device)
                
                recon, logits, _ = model(x_tensor)
                mse = torch.nn.functional.mse_loss(recon, x_tensor).item()
                probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
                
                preds_sell.append(probs[0])
                preds_hold.append(probs[1])
                preds_buy.append(probs[2])
                mses.append(mse)

        df_raw_matched = df_raw.loc[plot_times]
        
        fig, (ax_price, ax_prob) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
        fig.patch.set_facecolor('#1e1e1e')
        for ax in [ax_price, ax_prob]:
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='lightgray')
            for spine in ax.spines.values():
                spine.set_color('#444444')
            ax.grid(color='#444444', linestyle='--', linewidth=0.5)

        x_vals = np.arange(len(plot_times))
        
        opens = df_raw_matched[op_col].values
        highs = df_raw_matched[hi_col].values
        lows = df_raw_matched[lo_col].values
        closes = df_raw_matched[cl_col].values
        
        bull_signals = sum(1 for b in preds_buy if b > 0.7)
        bear_signals = sum(1 for s in preds_sell if s > 0.7)
        avg_mse = np.mean(mses)
        trend = "TĂNG" if bull_signals > bear_signals else "GIẢM" if bear_signals > bull_signals else "ĐI NGANG"
        
        for i in range(len(x_vals)):
            color = get_candlestick_color(opens[i], closes[i])
            ax_price.plot([x_vals[i], x_vals[i]], [lows[i], highs[i]], color=color, linewidth=1)
            ax_price.plot([x_vals[i], x_vals[i]], [opens[i], closes[i]], color=color, linewidth=3)
            
            if preds_buy[i] > 0.7 and mses[i] < 70.0:
                ax_price.axvspan(x_vals[i]-0.5, x_vals[i]+0.5, color='green', alpha=0.15)
            elif preds_sell[i] > 0.7 and mses[i] < 70.0:
                ax_price.axvspan(x_vals[i]-0.5, x_vals[i]+0.5, color='red', alpha=0.15)
                
        analysis_text = (
            f"V3 Phân Tích Phiên {sess_start}-{sess_end} UTC\n"
            f"• Lực xu hướng   : {trend}\n"
            f"• Tổng điểm Mua  : {bull_signals} nến\n"
            f"• Tổng điểm Bán  : {bear_signals} nến\n"
            f"• Độ nhiễu thị trường (MSE): {avg_mse:.4f}"
        )
        ax_price.text(0.02, 0.95, analysis_text, transform=ax_price.transAxes, fontsize=11, 
                      color='yellow', verticalalignment='top', bbox=dict(boxstyle='round', facecolor='#333333', alpha=0.8))

        ax_price.set_title(f"AAMT V3 - Mẫu nến & Phân Tích Ngày {day_str}", color='white', fontsize=15, pad=15)
        ax_price.set_ylabel("Giá Vàng (USD)", color='lightgray')

        ax_prob.stackplot(x_vals, preds_sell, preds_hold, preds_buy, labels=['Sell', 'Hold', 'Buy'], 
                          colors=['#ef5350', '#757575', '#26a69a'], alpha=0.7)
        ax_prob.set_ylabel("Xác suất", color='lightgray')
        ax_prob.set_ylim(0, 1)
        ax_prob.legend(loc='upper right', facecolor='#1e1e1e', labelcolor='white')
        
        step = max(1, len(x_vals) // 10)
        ax_prob.set_xticks(x_vals[::step])
        ax_prob.set_xticklabels([t.strftime('%H:%M') for t in plot_times[::step]])

        plt.tight_layout()
        out_path = os.path.join(out_dir, f"v3_chart_{day_str.replace('-','')}.png")
        plt.savefig(out_path, dpi=120)
        plt.close()
        print(f"  👉 Đã lưu: {out_path}")

if __name__ == "__main__":
    target_run = "run_20260418_102449_v3_CFG_XAU_NY_V3_1"
    if len(sys.argv) > 1:
        target_run = sys.argv[1]
    plot_daily_candlesticks_with_analysis(target_run)
