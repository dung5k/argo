import os
import json
from datetime import datetime, timezone

class V3ConfigLoader:
    """Quản lý nạp và merge Hot-reload cấu hình cho V3 Master Bot."""
    
    def __init__(self, main_config_path: str, schedule_path: str, log_callback=print):
        self.main_config_path = main_config_path
        self.schedule_path = schedule_path
        self.log_callback = log_callback
        self.last_logged_session = None
        
    def load_base_config(self) -> dict:
        """Đọc file config json chính làm khung nền."""
        try:
            with open(self.main_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.log_callback(f"[V3ConfigLoader] Lỗi đọc base config: {e}")
            return {}
            
    def get_current_schedule(self):
        """Đọc và tìm kiếm phiên giao dịch theo thời gian thực (UTC)."""
        try:
            if not os.path.exists(self.schedule_path): 
                return None, None, None
                
            with open(self.schedule_path, "r", encoding="utf-8") as fs:
                full_data = json.load(fs)
                sched = full_data.get("schedule", {})
                global_mt5_path = full_data.get("mt5_path")
                
            now_utc = datetime.now(timezone.utc)
            hm = now_utc.strftime("%H:%M")
            for sess_name, sinfo in sched.items():
                start = sinfo.get("start", "00:00")
                end = sinfo.get("end", "23:59")
                
                if start <= end:
                    if start <= hm <= end: 
                        return sess_name, sinfo, global_mt5_path
                else: 
                    if hm >= start or hm <= end: 
                        return sess_name, sinfo, global_mt5_path
        except Exception as e:
            self.log_callback(f"[V3ConfigLoader] Lỗi đọc schedule: {e}")
            pass
            
        return None, None, None

    def apply_schedule_overrides(self, config: dict, target_sinfo: dict, global_mt5_path: str = None) -> dict:
        """Hợp nhất các tham số (RunID, Dataset, Threshold) từ Schedule để Override lên Config gốc."""
        if not isinstance(config, dict):
            config = {}
            
        if global_mt5_path:
            config["MT5_PATH"] = global_mt5_path
            
        if not target_sinfo:
            return config
            
        config["HF_RUN_ID"] = target_sinfo.get("run_id", config.get("HF_RUN_ID"))
        config["CONFIG_ID"] = target_sinfo.get("config_id", config.get("CONFIG_ID"))
        
        # Override DATASET_REPO nếu có
        dataset_repo = target_sinfo.get("dataset_repo")
        if dataset_repo:
            if "HF_CLOUD" not in config:
                config["HF_CLOUD"] = {}
            config["HF_CLOUD"]["DATASET_REPO"] = dataset_repo
            
        # Override LIVE_BOT thresholds
        trading_config = target_sinfo.get("trading_config")
        if trading_config:
            if "LIVE_BOT" not in config:
                config["LIVE_BOT"] = {}
                
            min_prob = trading_config.get("min_prob_thresh")
            if min_prob is not None:
                config["LIVE_BOT"]["MIN_PROBABILITY_THRESH"] = min_prob
                
            mse_perc = trading_config.get("mse_thresh_perc")
            if mse_perc is not None:
                config["LIVE_BOT"]["MSE_THRESHOLD_PERCENTILE"] = mse_perc
                
        # Override FEATURE_ENGINEERING
        fe_config = target_sinfo.get("feature_engineering")
        if fe_config:
            if "FEATURE_ENGINEERING" not in config:
                config["FEATURE_ENGINEERING"] = {}
            config["FEATURE_ENGINEERING"].update(fe_config)
            
        # Override TRAINING
        train_config = target_sinfo.get("training")
        if train_config:
            if "TRAINING" not in config:
                config["TRAINING"] = {}
            config["TRAINING"].update(train_config)
            
        return config
