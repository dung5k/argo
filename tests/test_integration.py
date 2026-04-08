import sys
import os
import json
import time

project_dir = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"
sys.path.insert(0, project_dir)

from src.core.mt5_data_manager import MT5DataManager

def main():
    print("--- 1. ĐỌC CẤU HÌNH ---")
    config_file = os.path.join(project_dir, "data", "bot_config_xau.json")
    with open(config_file, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
        
    print(f"TARGET: {cfg.get('TARGET_SYMBOL')}")
    print(f"HF_RUN_ID: {cfg.get('HF_RUN_ID')}")
    print(f"WEIGHT_FILE: {cfg.get('WEIGHT_FILE')}")
    
    hf_token = "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"
    latest_run = cfg.get('HF_RUN_ID')
    weight_file = cfg.get('WEIGHT_FILE')
    
    print("\n--- 2. GIẢ LẬP TẢI RUN TỪ ĐÁM MÂY (HUGGINGFACE) ---")
    from huggingface_hub import hf_hub_download
    import shutil
    
    try:
        pass
    except Exception as e:
        print(f"❌ Lỗi kéo Scaler: {e}")
        return
        
    print("\n--- 3. KHỞI TẠO MT5 DATA MANAGER & REBUILD ---")
    mt5_manager = MT5DataManager(log_callback=print, target_sym=cfg.get("TARGET_SYMBOL", "XAUUSD"))
    
    # Reload sau khi copy scaler file
    mt5_manager.reload_features()
    expected = mt5_manager.features
    print(f"=> Lưới nhận dạng Sensor: {len(expected)} chiều (Dimesions).")
    
    print("\n--- 4. THỬ NGHIỆM CÀO DỮ LIỆU MT5 THEO RUN ---")
    merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=120)
    
    if err_msg:
        print(f"🔥 KẾT QUẢ: LỖI NGẮT QUÃNG -> {err_msg}")
    elif merged_df is not None:
        print(f"💎 KẾT QUẢ: THÀNH CÔNG RỰC RỠ!")
        print(f"Tổng số bản ghi (nến): {len(merged_df)}")
        print(f"Tổng số Sensor đã lấy được: {len(merged_df.columns)}")
        
        import src.core.feature_engineering as fe
        print("\n--- 5. KIỂM THỬ TẠO FINAL FEATURES & ALIGN SCALER ---")
        try:
            final_df, scaler_obj = fe.create_stationary_features(merged_df, is_live=True)
            print(f"✅ FE Thành Công! Số chiều Data cuối mảng: {len(final_df.columns)}")

            missing = [c for c in expected if c not in final_df.columns]
            if missing:
                print(f"⚠️ CẢNH BÁO: Bị THIẾU {len(missing)} Cột so với Scaler:")
                for m in missing[:15]: print(f" - {m}")
            else:
                print("=> 💎 Mảng dữ liệu tương thích 100% với Trọng số đang thử nghiệm.")
                
            print("\n--- 6. KIỂM TRA CHẶN DATA (INSUFFICIENT DATA) ---")
            window_size = 60
            if len(final_df) < window_size:
                print(f"⚠️ BỊ CHẶN: Dữ liệu không đủ {window_size} nến (chỉ có {len(final_df)} nến). Test dừng lại!")
            else:
                print(f"✅ PASSED chặn data: Dữ liệu có {len(final_df)} nến (>= {window_size}).")
                
                print("\n--- 7. ĐƯA VÀO MẠNG NƠ RON THỬ NGHIỆM ---")
                last_60_candles = final_df.iloc[-window_size:].values
                
                # Check NaNs
                import numpy as np
                if np.isnan(last_60_candles).any() or np.isinf(last_60_candles).any():
                    print("❌ LỖI: Dữ liệu rác chứa NaN hoặc Inf!")
                else:
                    import torch
                    from src.models.transformer_v5 import TimeSeriesTransformer
                    
                    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                    
                    # Fetch hyperparameters
                    with open(os.path.join(project_dir, "runs", latest_run, "training_metrix.json"), "r", encoding="utf-8") as f:
                        metrix = json.load(f)
                    hp = metrix.get("training_metadata", {}).get("hyperparameters", {})
                    d_model = hp.get("d_model", 256)
                    nhead = hp.get("nhead", 8)
                    num_attn_layers = hp.get("num_attn_layers", 3)
                    dropout_rate = hp.get("dropout_rate", 0.2)
                    num_features = len(expected)
                    
                    print(f"=> Hyperparams từ đám mây: d_model={d_model}, nhead={nhead}, layers={num_attn_layers}")
                    
                    model = TimeSeriesTransformer(
                        num_features=num_features, d_model=d_model, nhead=nhead,
                        num_layers=num_attn_layers, dropout_rate=dropout_rate,
                        num_xau_features=None
                    ).to(device)
                    
                    # Load Trọng số
                    runs_model_path = os.path.join(project_dir, "runs", latest_run, weight_file)
                    print(f"   Đang Load tệp: {runs_model_path}")
                    model.load_state_dict(torch.load(runs_model_path, map_location=device, weights_only=True))
                    model.eval()
                    
                    X_tensor = torch.tensor(last_60_candles, dtype=torch.float32).unsqueeze(0).to(device)
                    with torch.no_grad():
                        output = model(X_tensor)
                        probs = torch.softmax(output.data, dim=1).squeeze()
                        prob_down, prob_up = probs[0].item(), probs[1].item()
                    
                    print(f"✅ OUTPUT MẠNG NƠ RON THÀNH CÔNG!")
                    print(f"   => Phe Gấu (Sell): {prob_down*100:.2f}% | Phe Bò (Buy): {prob_up*100:.2f}%")
                    if prob_up > 0.57: print("   🚀 TÍN HIỆU: ĐÁNH LÊN (BUY)")
                    elif prob_up < 0.43: print("   🩸 TÍN HIỆU: ĐÁNH XUỐNG (SELL)")
                    else: print("   ⚖️ TÍN HIỆU: LƯỠNG LỰ (QUAN SÁT)")

        except Exception as e:
            print(f"❌ LỖI TRONG QUÁ TRÌNH FE/AI: {e}")
    else:
        print("❌ MERGED_DF Rỗng. Không kéo được data.")

if __name__ == "__main__":
    main()
