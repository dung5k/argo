import os
import json
import time
import re
import shutil
from datetime import datetime
import torch
import numpy as np
from huggingface_hub import HfApi, hf_hub_download

def sync_brain_from_cloud(
    target_symbol, target_prefix, base_weight_name, hf_run_cfg,
    current_loaded_session, session_id,
    num_features, d_model, nhead, num_attn_layers, dropout_rate, device,
    log_callback, mt5_manager, TransformerModel
):
    """Tải và đồng bộ Weights từ HF hoặc Local Cache. Hỗ trợ Đa Lõi (Từng Phiên Độc Lập)."""
    
    # Dịch session_id (0,1,2) -> 'asia', 'london', 'ny'
    s_map = {0: "asia", 1: "london", 2: "ny"}
    session_str = s_map.get(session_id, "unified")
    
    # v2_weights_EV_L3... -> asia_weights_EV_L3...
    weight_file = base_weight_name
    if "v2_weights_" in base_weight_name:
        weight_file = base_weight_name.replace("v2_weights_", f"{session_str}_weights_")
    
    active_brain_name = weight_file
    gui_status = ""
    model = None
    num_xau_features = 8 # Fallback gốc
    
    if session_id == current_loaded_session:
        return None, active_brain_name, current_loaded_session, "", num_xau_features

    log_callback(f"[BOT] Thay đổi Phiên: {session_id}. Đang nạp {weight_file}...")
    runs_model_path = ""
    hf_token = "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"
    
    try:
        if hf_run_cfg:
            latest_run = hf_run_cfg
            log_callback(f"[HF CLOUD] XÁC ĐỊNH NÃO BỘ CHỈ ĐỊNH: {latest_run} (File: {weight_file})")
        else:
            api = HfApi(token=hf_token)
            files = api.list_repo_files("dung5k/argo_data", repo_type="dataset")
            run_dirs = [f.split('/')[1] for f in files if f.startswith('runs/') and f'_{target_symbol.lower()}_' in f and weight_file in f]
            valid_runs = [r for r in run_dirs if r != 'old']
            if not valid_runs:
                raise Exception("Không tìm thấy thư mục run_ tương thích trên Repo!")
            latest_run = max(valid_runs)
            log_callback(f"[HF CLOUD] TỰ ĐỘNG DÒ TÌM NÃO BỘ MỚI NHẤT: {latest_run}")

        active_brain_name = latest_run
        gui_status = f"Đang kéo mây Không Gian {latest_run}..."
        
        runs_model_path = hf_hub_download(
            repo_id="dung5k/argo_data", repo_type="dataset", token=hf_token,
            filename=f"runs/{latest_run}/{weight_file}"
        )
        
        # Đồng bộ scaler
        do_sync_scaler = True
        try:
            safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cfg_path = os.path.join(safe_script_dir, "data", f"bot_config_{target_prefix.lower()}.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as cf:
                    c = json.load(cf)
                    do_sync_scaler = c.get("LIVE_TRADING", {}).get("SYNC_SCALER", True)
        except: pass
        if do_sync_scaler:
            try:
                scaler_cloud_path = hf_hub_download(
                    repo_id="dung5k/argo_data", repo_type="dataset", token=hf_token,
                    filename=f"runs/{latest_run}/scaler.pkl"
                )
                safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                scaler_local = os.path.join(safe_script_dir, "data", "scaler.pkl")
                import shutil
                shutil.copy2(scaler_cloud_path, scaler_local)
                if 'mt5_manager' in globals() and mt5_manager:
                    mt5_manager.reload_features()
                log_callback(f" ├─ ✅ [SCALE SHIELD] Đã đồng bộ Scaler Local về đúng định dạng của não {latest_run}!")
            except Exception as sce:
                log_callback(f" ├─ ⚠️ Không thể đồng bộ scaler.pkl từ đám mây: {sce}")
            
        # Đọc Metrix để tái tạo Khuôn Shape Pytorch
        try:
            metrix_path = hf_hub_download(
                repo_id="dung5k/argo_data", repo_type="dataset", token=hf_token,
                filename=f"runs/{latest_run}/training_metrix.json"
            )
            with open(metrix_path, "r", encoding='utf-8') as fm:
                metrix = json.load(fm)
            feats = metrix.get("training_metadata", {}).get("data_features", [])
            
            safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            meta_path_local = os.path.join(safe_script_dir, "data", f"feature_meta_{target_prefix}.json")
            if os.path.exists(meta_path_local):
                with open(meta_path_local, "r", encoding='utf-8') as mf:
                    num_xau_features = json.load(mf).get("num_xau_features", 8)
                    
            num_features = len(feats)
            log_callback(f" ├─ 📐 Khớp Kích thước Mạng: {target_prefix} ({num_xau_features}) | Macro ({num_features - num_xau_features}) | SUM ({num_features})")
            log_callback(f" ├─ 🧠 [METRIX DATA] Không gian yêu cầu TỔNG CỘNG {num_features} Dimensions để nạp đạn!")
            
            sample_feats = [f for f in feats if 'close' in f.lower() or 'PARQUET' in f or 'volume' in f.lower()][:10]
            log_callback(f" ├─ Danh sách Features nhận diện mẫu: {', '.join(sample_feats)}...")
        except Exception:
            pass
            
        log_callback(f"[HF CLOUD] Đã tải thành công HỆ TƯ TƯỞNG từ Đám mây!")
    except Exception as e:
        log_callback(f"[HF CLOUD] Không thể kết nối Đám mây hoặc Lỗi Tải: {str(e)[:100]}. Chuyển qua lấy bộ nhớ Local.")
        from pathlib import Path
        runs_dir = Path(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs")
        found_models = list(runs_dir.rglob(weight_file))
        runs_model_path = str(max(found_models, key=os.path.getctime)) if found_models else ""
    
    old_model_path = os.path.join(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\models", f"{target_symbol.lower()}_{session_id}_weights.pth")
    
    if os.path.exists(runs_model_path):
        log_callback(f"[BOT] Đang ốp Ma trận trọng số (Local Cache): {runs_model_path}")
        
        # TỰ ĐỘNG ĐỌC KÍCH THƯỚC THỰC TẾ TỪ FILE WEIGHTS
        try:
            _state = torch.load(runs_model_path, map_location='cpu', weights_only=True)
            _xau_w = _state.get('xau_input_proj.weight', None)
            _macro_w = _state.get('macro_fc.0.weight', None)
            if _xau_w is not None:
                num_xau_features = _xau_w.shape[1]
            if _xau_w is not None and _macro_w is not None:
                num_features = num_xau_features + _macro_w.shape[1]
            log_callback(f"[BOT] ✅ [AUTO-DETECT] XAU={num_xau_features} | MACRO={num_features - num_xau_features} | SUM={num_features}")
        except Exception as ade:
            log_callback(f"[BOT] ⚠️ Auto-detect thất bại: {ade}")
        
        model = TransformerModel(
            num_features=num_features, d_model=d_model, nhead=nhead,
            num_layers=num_attn_layers, dropout_rate=dropout_rate,
            num_xau_features=num_xau_features
        ).to(device)
        model.load_state_dict(torch.load(runs_model_path, map_location=device, weights_only=True))
        model.eval()
        gui_status = f"Đã Nạp Trọng Số: {active_brain_name[:20]}..."
        log_callback(f"[BOT] Nạp não bộ thành công: {active_brain_name}")
    elif os.path.exists(old_model_path):
        log_callback(f"[BOT] Đang load model từ file {old_model_path}")
        active_brain_name = weight_file
        try:
            match = re.search(r'(run_\d{8}_\d{6}_[^/\\]+)', old_model_path)
            if match: active_brain_name = match.group(1)
        except: pass
        
        model = TransformerModel(
            num_features=num_features, d_model=d_model, nhead=nhead,
            num_layers=num_attn_layers, dropout_rate=dropout_rate,
            num_xau_features=num_xau_features
        ).to(device)
        model.load_state_dict(torch.load(old_model_path, map_location=device, weights_only=True))
        model.eval()
        gui_status = f"Đã Nạp Lõi Pytorch Phiên {session_id.upper()}"
        log_callback(f"[BOT] Nạp thành công {old_model_path}")
    else:
        gui_status = f"⚠️ Lỗi: Không tìm thấy file trọng số {weight_file}!"
        log_callback(f"[BOT] LỖI THIẾU MODEL: {weight_file}")
        
    return model, active_brain_name, session_id, gui_status, num_xau_features

def check_session_guard(
    target_symbol, config, mt5, log_callback, gui_time
):
    """Kiểm tra giá chết (Frozen) và Khung giờ cấm giao dịch."""
    block_trading = False
    force_close = False
    gui_status = ""
    
    tick = mt5.symbol_info_tick(target_symbol)
    if tick is None:
        return True, False, "MT5 Không có Tick Data" # lock if no tick
        
    staleness_seconds = time.time() - tick.time
    if staleness_seconds > 300: # 5 minutes
        gui_status = f"Giá ngưng đọng ({int(staleness_seconds/60)}p). Chờ..."
        try:
            dt_tick = datetime.utcfromtimestamp(tick.time).strftime('%H:%M:%S %d/%m')
            dt_sys = datetime.utcfromtimestamp(time.time()).strftime('%H:%M:%S %d/%m')
        except:
            dt_tick, dt_sys = "N/A", "N/A"
        log_callback(f"[{gui_time}] 🔴 [SESSION GUARD] Giá bị Frozen/Stale. Từ chối Crawl/Trade.")
        log_callback(f" ├─ Mã ngưng đọng (Symbol): {target_symbol}")
        log_callback(f" ├─ Tick cuối MT5 trả về: {dt_tick} (Hệ quy chiếu MT5)")
        log_callback(f" ├─ Thời điểm kiểm tra: {dt_sys} (Hệ quy chiếu PC)")
        log_callback(f" └─ Tổng chênh lệch: {staleness_seconds:.0f} giây (~{int(staleness_seconds/60)} phút) > Ngưỡng 5 phút.")
        return True, False, gui_status
        
    session_guard_enabled = config.get("SESSION_GUARD_ENABLED", False)
    if session_guard_enabled:
        tick_dt = datetime.utcfromtimestamp(tick.time)
        market_open = config.get("MARKET_OPEN", "01:00")
        market_close = config.get("MARKET_CLOSE", "23:55")
        
        h_open, m_open = map(int, market_open.split(':'))
        h_close, m_close = map(int, market_close.split(':'))
        
        curr_min = tick_dt.hour * 60 + tick_dt.minute
        open_min = h_open * 60 + m_open
        close_min = h_close * 60 + m_close
        
        if open_min <= curr_min < open_min + 30:
            block_trading = True
        elif close_min - 30 <= curr_min < close_min:
            block_trading = True
            
        if close_min - 15 <= curr_min < close_min:
            force_close = True
            
        if curr_min >= close_min or curr_min < open_min:
            block_trading = True
            
    if block_trading:
        gui_status = "Đang Khóa Phiên Giao Dịch"
        log_callback(f"[{gui_time}] 🚧 [SESSION GUARD] Khung giờ cấm giao dịch. Bỏ qua Vòng lặp.")
        
    return block_trading, force_close, gui_status

def extract_quantum_signals(
    mt5_manager, model, device, window_size, fe, log_callback, gui_time
):
    """Kéo dữ liệu từ RAM, Normalize, nạp Tensor và tính Softmax."""
    gui_status = "Đang Cào Dữ Liệu Thời Gian Thực (In-Memory)..."
    log_callback(f"\n[{gui_time}] 🔄 BẮT ĐẦU VẬN CÔNG HÍT THỞ (TRỰC TIẾP TỪ RAM)...")
    
    t0_feat = time.time()
    merged_df, sym_data, err_msg = mt5_manager.get_live_merged_data_in_memory(window=120)
    
    if err_msg:
        gui_status = err_msg
        
    if merged_df is None or len(merged_df) < window_size:
        if "KHÔNG TÌM THẤY MÃ" not in gui_status:
            gui_status = "❌ KHÔNG ĐỦ 120 NẾN HOẶC MẤT MẠNG MT5!"
            log_callback(f" ├─ Trạm Lõi (In-Memory): {gui_status}")
        return None, None, sym_data, gui_status, "", ()

    gui_status = "Ép Ma trận 3D Tensor Pytorch (In-Memory)..."
    
    try:
        df, _ = fe.create_stationary_features(merged_df, is_live=True)
    except Exception as ex_feat:
        log_callback(f" ├─ Lõi Lượng Tử (RAM Mapped): ❌ LỖI VĂNG SÓNG {str(ex_feat)[:50]}")
        raise ex_feat
        
    dt_feat = time.time() - t0_feat
    log_callback(f" ├─ Trạm Lõi lượng tử (RAM Mapped): ✅ HOÀN TẤT ({dt_feat:.2f}s)")
    log_callback(f" 📊 KIỂM KÊ KHO: RAM Nạp thành công {len(df):,} nến.")
    
    last_60_candles = df.iloc[-window_size:].values
    if len(last_60_candles) < window_size:
        gui_status = "Mạng lag, đợi nến 1 phút sau..."
        log_callback(f" ⚠️ CẢNH BÁO LỰC: Lượng Nến Cắt quá mỏng ({len(last_60_candles)}/{window_size}). AI từ chối uống dòng Máu này!")
        return None, None, sym_data, gui_status, "", ()
        
    if np.isnan(last_60_candles).any() or np.isinf(last_60_candles).any():
        gui_status = "Data chứa Rác (NaN/Inf), Xả bỏ!"
        log_callback(f" 🚨 LỖI TINH KHIẾT: Phát hiện dữ liệu lỗi (NaN hoặc Inf). Model từ chối tiêu thụ!")
        return None, None, sym_data, gui_status, "", ()
        
    log_callback(f" ├─ [DEBUG] Chuẩn bị Convert Tensor...")
    X_tensor = torch.tensor(last_60_candles, dtype=torch.float32).unsqueeze(0).to(device)
    
    gui_status = "Đang trích xuất Lực Cầu (Softmax Confidence)..."
    t0_infer = time.time()
    log_callback(f" ├─ [DEBUG] Bắt đầu Inference (model forward)...")
    try:
        from datetime import datetime as dt_sys
        current_utc_hour = dt_sys.utcnow().hour
        session_id_val = 0
        if 8 <= current_utc_hour < 13:
            session_id_val = 1
        elif current_utc_hour >= 13:
            session_id_val = 2
            
        session_tensor = torch.tensor([session_id_val], dtype=torch.long).to(device)
        session_name = {0: "Á", 1: "Âu", 2: "Mỹ"}.get(session_id_val, "?")

        with torch.no_grad():
            output = model(X_tensor)
            probs = torch.softmax(output.data, dim=1).squeeze()
            prob_down, prob_up = probs[0].item(), probs[1].item()
            prediction = prob_up 
            
            t_min, t_max, t_mean = X_tensor.min().item(), X_tensor.max().item(), X_tensor.mean().item()
            raw_logits = output.cpu().numpy()[0]
    except Exception as e:
        log_callback(f" ├─ ❌ [DEBUG] Lỗi Inference bùng nổ: {e}")
        raise e
        
    log_callback(f" ├─ [DEBUG] Hoàn tất Inference! Trả về.")
    dt_infer = time.time() - t0_infer
    gui_prediction_txt = f"{prediction*100:.2f}%"
    
    tensor_stats = (X_tensor.shape, t_min, t_max, t_mean, last_60_candles[-1][:5], dt_infer, raw_logits)
    
    return prediction, prob_down, sym_data, gui_status, gui_prediction_txt, tensor_stats
