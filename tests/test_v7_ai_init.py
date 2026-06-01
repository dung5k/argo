# -*- coding: utf-8 -*-
import os
import sys
import unittest
import json
import shutil

# Thêm project root vào path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.training_v7.v7_ai_init import run_ai_initialization

class TestV7AIInitialization(unittest.TestCase):
    def setUp(self):
        # Tạo bản sao backup nếu file master config đã có sẵn
        self.master_config_path = os.path.join(_ROOT, "v7_master_config.json")
        self.master_config_backup = os.path.join(_ROOT, "v7_master_config_backup_test.json")
        if os.path.exists(self.master_config_path):
            shutil.copy(self.master_config_path, self.master_config_backup)
            
        # Tạo test master config
        self.test_mcfg = {
            "data": {
                "leader_symbol": "BTCUSD",
                "follower_symbol": "LTCUSD",
                "timeframe": "M15"
            },
            "window": {
                "initial_train_size_days": 180,
                "validation_size_days": 30,
                "slide_step_days": 30,
                "start_date": "2025-06-01",
                "end_date": "2026-06-01"
            },
            "ai": {
                "llm_model": "gemini-1.5-flash",
                "correlation_threshold": 0.25,
                "max_lag_steps": 12
            },
            "train": {
                "learning_rate_base": 0.001,
                "learning_rate_finetune": 0.0001,
                "min_win_rate_threshold": 0.50,
                "min_profit_factor": 1.1,
                "epochs_base": 2,
                "epochs_finetune": 1,
                "batch_size": 64
            },
            "telegram": {
                "channel_id": "1816854047"
            }
        }
        with open(self.master_config_path, "w", encoding="utf-8") as f:
            json.dump(self.test_mcfg, f, indent=4)
            
        self.bot_config_path = os.path.join(_ROOT, "bot_config_v7.json")
        if os.path.exists(self.bot_config_path):
            os.remove(self.bot_config_path)

    def tearDown(self):
        # Dọn dẹp test config
        if os.path.exists(self.master_config_path):
            os.remove(self.master_config_path)
            
        # Khôi phục backup
        if os.path.exists(self.master_config_backup):
            shutil.copy(self.master_config_backup, self.master_config_path)
            os.remove(self.master_config_backup)
            
        if os.path.exists(self.bot_config_path):
            os.remove(self.bot_config_path)

    def test_run_ai_initialization_fallback(self):
        """Kiểm tra xem Module 1 chạy fallback trơn tru khi không có/hoặc có API key lỗi."""
        # Giả lập không có API Key để kiểm tra fallback cơ bản
        old_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        try:
            bot_cfg = run_ai_initialization("v7_master_config.json")
            self.assertIsNotNone(bot_cfg)
            self.assertEqual(bot_cfg["TARGET_SYMBOL"], "LTCUSD")
            self.assertEqual(bot_cfg["LEADER_SYMBOL"], "BTCUSD")
            self.assertTrue(os.path.exists(self.bot_config_path))
            
            # Đọc lại và kiểm tra nội dung
            with open(self.bot_config_path, "r", encoding="utf-8") as f:
                saved_cfg = json.load(f)
            self.assertEqual(saved_cfg["FEATURE_ENGINEERING"]["MAX_HOLD_BARS"], 30)
            self.assertEqual(saved_cfg["FEATURE_ENGINEERING"]["MAX_LAG_STEPS"], 10)
        finally:
            if old_key is not None:
                os.environ["GEMINI_API_KEY"] = old_key

if __name__ == "__main__":
    unittest.main()
