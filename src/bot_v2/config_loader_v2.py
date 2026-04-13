import os
import json
from datetime import datetime, timezone

class V2ConfigLoader:
    """Quản lý nạp và merge Hot-reload cấu hình cho V2 Bot."""
    
    def __init__(self, main_config_path: str, schedule_path: str):
        self.main_config_path = main_config_path
        self.schedule_path = schedule_path
        
    def load_base_config(self) -> dict:
        """Đọc file config json chính (vd: bot_config_xau_london_v2.json)."""
        try:
            with open(self.main_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
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
                
                # Logic跨ngày (vòng lặp 24h)
                if start <= end:
                    if start <= hm < end: 
                        return sess_name, sinfo, global_mt5_path
                else: 
                    if hm >= start or hm < end: 
                        return sess_name, sinfo, global_mt5_path
        except Exception:
            pass
            
        return None, None, None

    def apply_schedule_overrides(self, config: dict, target_sinfo: dict, global_mt5_path: str = None) -> dict:
        """Hợp nhất các tham số (Threshold, Lot...) từ Schedule để Override lên Config gốc."""
        if not isinstance(config, dict):
            config = {}
            
        if global_mt5_path:
            config["MT5_PATH"] = global_mt5_path
            
        if not target_sinfo:
            return config
            
        # ĐỒNG BỘ TRADING_CONFIG NÓNG
        trading_config = target_sinfo.get("trading_config")
        if trading_config:
            if "LIVE_TRADING" not in config: 
                config["LIVE_TRADING"] = {}
                
            entry_thr = trading_config.get("entry_thresh")
            if entry_thr is not None:
                config["LIVE_TRADING"]["BUY_ENTRY_THR"] = entry_thr
                config["LIVE_TRADING"]["SELL_ENTRY_THR"] = 1.0 - entry_thr
                
            close_thr = trading_config.get("close_thresh")
            if close_thr is not None:
                config["LIVE_TRADING"]["CLOSE_BUY_THR"] = close_thr
                config["LIVE_TRADING"]["CLOSE_SELL_THR"] = close_thr
                
            lot_size = trading_config.get("lot_size")
            if lot_size is not None:
                config["LIVE_TRADING"]["lot_size"] = lot_size
                
            tp_pips = trading_config.get("tp_pips")
            if tp_pips is not None:
                config["LIVE_TRADING"]["tp_pips"] = tp_pips
                
            sl_pips = trading_config.get("sl_pips")
            if sl_pips is not None:
                config["LIVE_TRADING"]["sl_pips"] = sl_pips
                
        # (Fallback tương thích bản cũ)
        elif target_sinfo.get("max_thresh_override") is not None:
            max_thr = target_sinfo.get("max_thresh_override")
            if "LIVE_TRADING" not in config: 
                config["LIVE_TRADING"] = {}
            config["LIVE_TRADING"]["BUY_ENTRY_THR"] = max_thr
            config["LIVE_TRADING"]["SELL_ENTRY_THR"] = 1.0 - max_thr
            
        return config
