import os
import json
import unittest
from datetime import datetime, timezone
import tempfile

from src.bot_v2.config_loader_v2 import V2ConfigLoader

class TestV2ConfigLoader(unittest.TestCase):
    def setUp(self):
        # Create temp files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.main_config_path = os.path.join(self.temp_dir.name, "main.json")
        self.schedule_path = os.path.join(self.temp_dir.name, "sched.json")
        
        main_data = {"LIVE_TRADING": {"BUY_ENTRY_THR": 0.60}}
        with open(self.main_config_path, "w", encoding="utf-8") as f:
            json.dump(main_data, f)
            
        sched_data = {
            "mt5_path": "C:\\fake\\mt5.exe",
            "schedule": {
                "test_session": {
                    "start": "00:00",
                    "end": "23:59",
                    "trading_config": {
                        "entry_thresh": 0.58,
                        "close_thresh": 0.50
                    }
                }
            }
        }
        with open(self.schedule_path, "w", encoding="utf-8") as f:
            json.dump(sched_data, f)
            
        self.loader = V2ConfigLoader(self.main_config_path, self.schedule_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_base_config_success(self):
        cfg = self.loader.load_base_config()
        self.assertEqual(cfg["LIVE_TRADING"]["BUY_ENTRY_THR"], 0.60)
        
    def test_get_current_schedule_finds_session(self):
        sess_name, sinfo, global_mt5 = self.loader.get_current_schedule()
        self.assertIsNotNone(sess_name)
        self.assertEqual(sess_name, "test_session")
        self.assertEqual(sinfo["trading_config"]["entry_thresh"], 0.58)
        self.assertEqual(global_mt5, "C:\\fake\\mt5.exe")

    def test_apply_schedule_overrides(self):
        cfg = self.loader.load_base_config()
        _, sinfo, global_mt5 = self.loader.get_current_schedule()
        
        modified_cfg = self.loader.apply_schedule_overrides(cfg, sinfo, global_mt5)
        
        # Verify Threshold was OVERRIDEN
        self.assertEqual(modified_cfg["LIVE_TRADING"]["BUY_ENTRY_THR"], 0.58)
        # Verify SELL threshold is calculated exactly as 1.0 - 0.58 = 0.42
        self.assertAlmostEqual(modified_cfg["LIVE_TRADING"]["SELL_ENTRY_THR"], 0.42)
        # Verify MT5 path added
        self.assertEqual(modified_cfg["MT5_PATH"], "C:\\fake\\mt5.exe")

if __name__ == '__main__':
    unittest.main()
