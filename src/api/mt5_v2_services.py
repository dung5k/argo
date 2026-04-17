import os
import sys
from pathlib import Path
import json

safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.bot_v2.config_loader_v2 import V2ConfigLoader
from src.bot_v2.inference_engine_v2 import V2InferenceEngine
from src.bot_v2.data_processor_v2 import V2DataProcessor
from src.core.mt5_data_manager import MT5DataManager
import torch
import pandas as pd
from datetime import datetime, timezone

class BrainManager:
    """Class để quản lý việc load Config và Model V2."""
    def __init__(self, main_config_path: str, schedule_path: str):
        self.config_loader = V2ConfigLoader(main_config_path, schedule_path)
        self.engines = {} # {session_name: V2InferenceEngine}
        self.configs = {} # {session_name: config}
        
    def load_brains(self, symbol="XAUUSDm"):
        """Tải trước toàn bộ não của các phiên lên RAM/GPU để bắn API siêu tốc."""
        print(f"[BrainManager] Đang khởi tạo toàn bộ Não bộ cho V2 API...")
        full_config = self.config_loader.load_base_config()
        if not full_config:
            print("[BrainManager] Lỗi: Không thể tải config gốc.")
            return False
            
        with open(self.config_loader.schedule_path, "r", encoding="utf-8-sig") as fs:
            full_data = json.load(fs)
            sched = full_data.get("schedule", {})
            
        # Nạp tất cả phiên
        for sess_name, sinfo in sched.items():
            conf = self.config_loader.apply_schedule_overrides(full_config, sinfo)
            self.configs[sess_name] = conf
            
            # Khởi tạo Inference Engine
            engine = V2InferenceEngine(log_callback=lambda msg: None) # Silent log để tránh Spam
            
            # Các dimension
            arch = conf.get("TRAINING", {}).get("ARCH", {})
            d_mod = arch.get("d_model", 256)
            nhead = arch.get("heads", 8)
            num_attn = arch.get("layers", 3)
            drop = arch.get("dropout", 0.2)
            # num_xau and nf will be dynamically extracted from CloudManager
            
            w_file = sinfo.get("weight_file", "")
            base_dir = os.path.dirname(self.config_loader.main_config_path)
            model_path = os.path.join(base_dir, w_file)
            
            try:
                from src.bot_v2.cloud_manager_v2 import V2CloudManager
                cloud = V2CloudManager("XAUUSDm", "XAUUSDm", "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", log_callback=print)
                m_path, _, num_xau, nf, i_feats = cloud.sync_explicit_model(sinfo.get('run_id'), w_file, sinfo.get("config_id"))
                target_path = m_path
            except Exception as e:
                target_path = model_path
                print(f"[BrainManager] Không thể lấy HF path qua Manager, fallback: {e}")
            
            if os.path.exists(target_path):
                ok = engine.load_weights(target_path, num_features=nf, d_model=d_mod, 
                                         nhead=nhead, num_attn_layers=num_attn, 
                                         dropout_rate=drop, num_xau_features=num_xau)
                if ok:
                    self.engines[sess_name] = engine
                else:
                    print(f"[BrainManager] Lỗi khi load weights cho phiên {sess_name}")
            else:
                print(f"[BrainManager] Cảnh báo: Không tìm thấy file weights {target_path}")
                
        print(f"[BrainManager] Đã load xong {len(self.engines)} brains.")
        return True
        
    def get_brain_for_time(self, current_time_utc: datetime):
        """Lựa chọn bộ não và config phù hợp với giờ nến."""
        hm = current_time_utc.strftime("%H:%M")
        
        with open(self.config_loader.schedule_path, "r", encoding="utf-8-sig") as fs:
            full_data = json.load(fs)
            sched = full_data.get("schedule", {})
            
        for sess_name, sinfo in sched.items():
            start = sinfo.get("start", "00:00")
            end = sinfo.get("end", "23:59")
            if start <= end:
                if start <= hm < end: 
                    return sess_name, self.engines.get(sess_name), self.configs.get(sess_name)
            else: 
                if hm >= start or hm < end: 
                    return sess_name, self.engines.get(sess_name), self.configs.get(sess_name)
                    
        # Fallback (Ví dụ Asian)
        return "asian", self.engines.get("asian"), self.configs.get("asian")


class PredictionService:
    """Service xử lý Data và Suy diễn."""
    def __init__(self, brain_manager: BrainManager, mt5_config: str):
        self.brain_manager = brain_manager
        self.mt5_manager = MT5DataManager(
            log_callback=print,
            config_path=self.brain_manager.config_loader.main_config_path
        )

    def get_prediction_history(self, symbol="XAUUSDm", timeframe="M1", limit=1000):
        """Tính toán xác suất lịch sử cho `limit` nến gần nhất."""
        
        # Để lấy limit nến lịch sử, ta cần limit + T_WINDOW nến để đủ features (ví dụ 60 nến T_WINDOW)
        # Cộng thêm dư lượng MACD, EMA lag (60 nến nữa) -> Cần lấy limit + 120
        total_limit = limit + 120
        merged_df, sym_data, err_msg = self.mt5_manager.get_live_merged_data_in_memory(window=total_limit)
        
        if merged_df is None or len(merged_df) < 120:
            print(f"[API] Lỗi lấy Lịch sử MT5: {err_msg}")
            return None
            
        # Lấy session hiện tại để tham chiếu Config (Vì Scaler path ở trong config)
        # Giả định dùng chung scaler config của asian hoặc phiên gần nhất
        sess_name, engine, config = self.brain_manager.get_brain_for_time(datetime.now(timezone.utc))
        if not engine or not config:
            return None
            
        window_size = config.get("MODEL_INPUT", {}).get("window_size", 60)
        scaler_path = config.get("FEATURE_ENGINEERING", {}).get("scaler_path", "data/scaler_v2.pkl")
        num_features = config.get("MODEL_DIMENSIONS", {}).get("num_features", 38)
        
        i_feats = config.get("FEATURE_ENGINEERING", {}).get("EXACT_FEATURES", [])
        processor = V2DataProcessor(scaler_path, i_feats, window_size, log_callback=print)
        
        fe_df, err = processor.run_feature_engineering(merged_df)
        if err: return None
        
        scaled_df, err = processor.scale_features(fe_df)
        if err: return None
        
        final_df, err = processor.filter_and_align(scaled_df)
        if err: return None
            
        # Sliding Window -> [N, window_size, features]
        # Bằng cách sử dụng vòng lặp nhanh tạo ra mảng numpy
        import numpy as np
        
        if final_df is None or len(final_df) < window_size:
            return None
            
        X_arr = final_df.values
        times = final_df.index
        
        N = len(X_arr) - window_size + 1
        # Tránh lấy quá số lượng requested limit
        if N > limit: 
            N = limit
            X_arr = X_arr[-(N + window_size - 1):]
            times = times[-(N + window_size - 1):]
            
        # Tạo batch (N, window_size, features)
        windows = []
        valid_times = []
        for i in range(N):
            w = X_arr[i : i + window_size]
            windows.append(w)
            valid_times.append(int(times[i + window_size - 1].timestamp()))
            
        X_tensor = torch.tensor(np.array(windows), dtype=torch.float32)
        
        # Batch Predict
        with torch.no_grad():
            output = engine.model(X_tensor.to(engine.device))
            probs = torch.softmax(output.data, dim=1)
            prob_ups = probs[:, 1].cpu().numpy()
            
        # Trả về list tuple (timestamp, prob_up)
        return list(zip(valid_times, prob_ups))
        
    def get_prediction_history_for_session(self, symbol="XAUUSDm", timeframe="M1", limit=2000, target_session="asian", target_hours=(0, 7)):
        """Tính toán lịch sử RẤT LỚN (vd 2500 nến) nhưng CHỈ VẼ ĐIỂM nằm trong KHUNG GIỜ của Target Session."""
        
        # 1. Quét dữ liệu 
        total_limit = limit + 120
        merged_df, sym_data, err_msg = self.mt5_manager.get_live_merged_data_in_memory(window=total_limit)
        
        if merged_df is None or len(merged_df) < 120:
            print(f"[API] Lỗi lấy Lịch sử MT5: {err_msg}")
            return None
            
        # 2. XIN Brain trực tiếp bỏ qua Timezone hiện tại
        engine = self.brain_manager.engines.get(target_session)
        if not engine:
            print(f"❌ Không tìm thấy bộ não đã load cho phiên '{target_session}'")
            return None
            
        # Lấy lịch trình để trích xuất config parameters nếu cần (Tái sử dụng cơ chế có sẵn)
        with open(self.brain_manager.config_loader.schedule_path, 'r', encoding='utf-8-sig') as fs:
            import json
            sched = json.load(fs).get("schedule", {})
        sinfo = sched.get(target_session, {})
        full_config = self.brain_manager.config_loader.main_config_path
        with open(full_config, 'r', encoding='utf-8') as f:
            import json
            full_cfg = json.load(f)
            
        config = self.brain_manager.config_loader.apply_schedule_overrides(full_cfg, sinfo)
        
        # 3. Tiến hành feature scaling
        from src.bot_v2.cloud_manager_v2 import V2CloudManager
        cloud = V2CloudManager("XAUUSDm", "XAUUSDm", "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", log_callback=lambda msg: None)
        _, _, _, _, i_feats = cloud.sync_explicit_model(sinfo.get('run_id'), sinfo.get("weight_file"), sinfo.get("config_id"))
        
        window_size = config.get("TRAINING", {}).get("ARCH", {}).get("win", 60)
        scaler_path = os.path.join(os.path.dirname(self.brain_manager.config_loader.main_config_path), f"scaler_{sinfo.get('config_id')}.pkl")
        
        processor = V2DataProcessor(scaler_path, i_feats, window_size, log_callback=None) # Silent Log vì quét qua nhiều
        
        fe_df, err = processor.run_feature_engineering(merged_df)
        if err: return None
        
        scaled_df, err = processor.scale_features(fe_df)
        if err: return None
        
        final_df, err = processor.filter_and_align(scaled_df)
        if err: return None
            
        import numpy as np
        if final_df is None or len(final_df) < window_size:
            return None
            
        X_arr = final_df.values
        times = final_df.index
        
        N = len(X_arr) - window_size + 1
        if N > limit: 
            N = limit
            X_arr = X_arr[-(N + window_size - 1):]
            times = times[-(N + window_size - 1):]
            
        windows = []
        valid_times = []
        original_idx = []
        
        start_h, end_h = target_hours
        
        for i in range(N):
            candle_time_utc = times[i + window_size - 1]
            # ONLY PREDICT if candle is exactly within target timezone
            if start_h <= candle_time_utc.hour < end_h:
                w = X_arr[i : i + window_size]
                windows.append(w)
                valid_times.append(int(candle_time_utc.timestamp()))
                original_idx.append(i)
            
        if not windows:
            return [] # Không có cây nến nào trong lịch sử rơi vào target timeframe
            
        X_tensor = torch.tensor(np.array(windows), dtype=torch.float32)
        
        # Batch Predict
        with torch.no_grad():
            output = engine.model(X_tensor.to(engine.device))
            probs = torch.softmax(output.data, dim=1)
            prob_ups = probs[:, 1].cpu().numpy()
            
        return list(zip(valid_times, prob_ups))
        
    def get_live_prediction(self, symbol="XAUUSDm", timeframe="M1"):
        """Tính toán xác suất cho nến mới nhất (Live Tick)."""
        merged_df, sym_data, err_msg = self.mt5_manager.get_live_merged_data_in_memory(window=120)
        if merged_df is None or len(merged_df) < 60:
            return None
            
        now_dt = merged_df.index[-1].to_pydatetime()
        sess_name, engine, config = self.brain_manager.get_brain_for_time(now_dt)
        if not engine or not config:
            return None
            
        window_size = config.get("MODEL_INPUT", {}).get("window_size", 60)
        scaler_path = config.get("FEATURE_ENGINEERING", {}).get("scaler_path", "data/scaler_v2.pkl")
        num_features = config.get("MODEL_DIMENSIONS", {}).get("num_features", 38)
        
        i_feats = config.get("FEATURE_ENGINEERING", {}).get("EXACT_FEATURES", [])
        processor = V2DataProcessor(scaler_path, i_feats, window_size, log_callback=None)
        
        X_tensor, err = processor.ingest_and_scale(merged_df)
        if err or X_tensor is None: return None
        
        prob_up, logits = engine.predict(X_tensor)
        
        return {
            "timestamp": int(now_dt.timestamp()),
            "prob_up": prob_up,
            "session": sess_name
        }
