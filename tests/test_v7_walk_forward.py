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

from src.training_v7.v7_walk_forward import (
    get_synced_data, estimate_dynamic_lag, build_features_and_labels, 
    run_backtest_simulation, run_walk_forward_learning
)
from src.training_v7.v7_transformer import CrossAssetTransformerModel

class TestV7WalkForwardEngine(unittest.TestCase):
    def setUp(self):
        self.master_config_path = os.path.join(_ROOT, "v7_configs", "v7_master_config.json")
        self.master_config_backup = os.path.join(_ROOT, "v7_configs", "v7_master_config_backup_wf.json")
        if os.path.exists(self.master_config_path):
            shutil.copy(self.master_config_path, self.master_config_backup)
            
        self.bot_config_path = os.path.join(_ROOT, "bot_config_v7.json")
        self.bot_config_backup = os.path.join(_ROOT, "bot_config_v7_backup_wf.json")
        if os.path.exists(self.bot_config_path):
            shutil.copy(self.bot_config_path, self.bot_config_backup)
            
        # Tạo test master config thu nhỏ để test chạy siêu nhanh
        self.test_mcfg = {
            "data": {
                "leader_symbol": "BTCUSD",
                "follower_symbol": "LTCUSD",
                "timeframe": "M15"
            },
            "window": {
                "initial_train_size_days": 10,  # Thu nhỏ để test nhanh
                "validation_size_days": 3,
                "slide_step_days": 3,
                "start_date": "2026-05-01",
                "end_date": "2026-05-20"
            },
            "ai": {
                "llm_model": "gemini-2.5-flash",
                "correlation_threshold": 0.01,  # Ngưỡng thấp để luôn pass
                "max_lag_steps": 3
            },
            "train": {
                "learning_rate_base": 0.001,
                "learning_rate_finetune": 0.0001,
                "min_win_rate_threshold": 0.0,  # Luôn pass để test luồng
                "min_profit_factor": 0.0,
                "epochs_base": 1,
                "epochs_finetune": 1,
                "batch_size": 16
            }
        }
        with open(self.master_config_path, "w", encoding="utf-8") as f:
            json.dump(self.test_mcfg, f, indent=4)

    def tearDown(self):
        # Dọn dẹp các config chung
        for f in [self.master_config_path, self.bot_config_path]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
                
        if os.path.exists(self.master_config_backup):
            try: shutil.copy(self.master_config_backup, self.master_config_path)
            except: pass
            try: os.remove(self.master_config_backup)
            except: pass
            
        if os.path.exists(self.bot_config_backup):
            try: shutil.copy(self.bot_config_backup, self.bot_config_path)
            except: pass
            try: os.remove(self.bot_config_backup)
            except: pass

    def test_synced_data_and_lag_estimation(self):
        """Kiểm tra đồng bộ dữ liệu và tính Dynamic Lag."""
        merged = get_synced_data("BTCUSD", "LTCUSD", "M15", "2026-05-01", "2026-05-05", "LOCAL")
        self.assertIsNotNone(merged)
        self.assertTrue("follower_close" in merged.columns)
        self.assertTrue("leader_close" in merged.columns)
        
        lag, corr = estimate_dynamic_lag(merged, 3, 0.01)
        self.assertTrue(1 <= lag <= 3)
        self.assertIsNotNone(corr)

    def test_features_and_labels(self):
        """Kiểm tra tạo feature và label."""
        merged = get_synced_data("BTCUSD", "LTCUSD", "M15", "2026-05-01", "2026-05-15", "LOCAL")
        X, Y, times = build_features_and_labels(merged, 2, 0.008, 0.004, 10, seq_len=5)
        self.assertEqual(X.ndim, 3)  # [samples, seq_len, features]
        self.assertEqual(X.shape[1], 5) # seq_len = 5
        self.assertEqual(Y.ndim, 1)  # [samples]
        self.assertEqual(len(X), len(Y))

    def test_walk_forward_learning_flow(self):
        """Kiểm tra toàn bộ luồng Walk-Forward hoạt động thành công."""
        # Giả lập không có API Key để test nhanh fallback AI feedback loop
        old_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        # Tạo test bot config độc lập với CONFIG_ID riêng biệt cho testcase này
        test_bot_cfg = {
            "TARGET_SYMBOL": "LTCUSD",
            "LEADER_SYMBOL": "BTCUSD",
            "CONFIG_ID": "CFG_V7_TEST_WF_FLOW", # CONFIG_ID riêng biệt để tránh đụng độ tài nguyên!
            "VERSION": "7.0",
            "MASTER_CONFIG": "v7_configs/v7_master_config.json",
            "FEATURE_ENGINEERING": {
                "TP_PCT": 0.008,
                "SL_PCT": 0.004,
                "MAX_HOLD_BARS": 10,
                "MAX_LAG_STEPS": 3,
                "CORRELATION_THRESHOLD": 0.01,
                "TIMEFRAME": "M15"
            },
            "TRAINING": {
                "LEARNING_RATE_BASE": 0.001,
                "LEARNING_RATE_FINETUNE": 0.0001,
                "BATCH_SIZE": 16,
                "EPOCHS_BASE": 1,
                "EPOCHS_FINETUNE": 1
            },
            "WALK_FORWARD": {
                "INITIAL_TRAIN_SIZE_DAYS": 10,
                "VALIDATION_SIZE_DAYS": 3,
                "SLIDE_STEP_DAYS": 3,
                "START_DATE": "2026-05-01",
                "END_DATE": "2026-05-20"
            }
        }
        with open(self.bot_config_path, "w", encoding="utf-8") as f:
            json.dump(test_bot_cfg, f, indent=4)
            
        workspace_test_dir = os.path.join(_ROOT, "workspaces", "CFG_V7_TEST_WF_FLOW")
        if os.path.exists(workspace_test_dir):
            try: shutil.rmtree(workspace_test_dir)
            except: pass
            
        try:
            workspace_dir = run_walk_forward_learning("bot_config_v7.json")
            self.assertTrue(os.path.exists(workspace_dir))
            
            # Kiểm tra bố trí thư mục con chuẩn
            self.assertTrue(os.path.exists(os.path.join(workspace_dir, "brains")))
            self.assertTrue(os.path.exists(os.path.join(workspace_dir, "results")))
            self.assertTrue(os.path.exists(os.path.join(workspace_dir, "config")))
            self.assertTrue(os.path.exists(os.path.join(workspace_dir, "data")))
            
            # Kiểm tra file kết quả chặng được lưu quy củ
            self.assertTrue(os.path.exists(os.path.join(workspace_dir, "results", "step_1_results.json")))
            self.assertTrue(os.path.exists(os.path.join(workspace_dir, "brains", "aamt_v7_foundation.pth")))
        finally:
            if old_key is not None:
                os.environ["GEMINI_API_KEY"] = old_key
                
            # Dọn dẹp thư mục workspace test độc lập sau khi hoàn tất test case này
            if os.path.exists(workspace_test_dir):
                try: shutil.rmtree(workspace_test_dir)
                except: pass

    def test_session_filtering(self):
        """Kiểm tra tính năng lọc dữ liệu theo phiên giao dịch."""
        test_bot_cfg = {
            "TARGET_SYMBOL": "LTCUSD",
            "LEADER_SYMBOL": "BTCUSD",
            "CONFIG_ID": "CFG_V7_TEST_SESSION",
            "VERSION": "7.0",
            "MASTER_CONFIG": "v7_configs/v7_master_config.json",
            "SESSION": "london",
            "SESSION_UTC": {
                "START": "07:00",
                "END": "16:00"
            },
            "FEATURE_ENGINEERING": {
                "TP_PCT": 0.008,
                "SL_PCT": 0.004,
                "MAX_HOLD_BARS": 10,
                "MAX_LAG_STEPS": 3,
                "CORRELATION_THRESHOLD": 0.01,
                "TIMEFRAME": "M15"
            },
            "TRAINING": {
                "LEARNING_RATE_BASE": 0.001,
                "LEARNING_RATE_FINETUNE": 0.0001,
                "BATCH_SIZE": 16,
                "EPOCHS_BASE": 1,
                "EPOCHS_FINETUNE": 1
            },
            "WALK_FORWARD": {
                "INITIAL_TRAIN_SIZE_DAYS": 10,
                "VALIDATION_SIZE_DAYS": 3,
                "SLIDE_STEP_DAYS": 3,
                "START_DATE": "2026-05-01",
                "END_DATE": "2026-05-20"
            }
        }
        
        with open(self.bot_config_path, "w", encoding="utf-8") as f:
            json.dump(test_bot_cfg, f, indent=4)
            
        workspace_test_dir = os.path.join(_ROOT, "workspaces", "CFG_V7_TEST_SESSION")
        if os.path.exists(workspace_test_dir):
            try: shutil.rmtree(workspace_test_dir)
            except: pass
            
        try:
            workspace_dir = run_walk_forward_learning("bot_config_v7.json")
            self.assertTrue(os.path.exists(workspace_dir))
            
            # Đọc config đã lưu để kiểm tra
            with open(os.path.join(workspace_dir, "config.json"), "r", encoding="utf-8") as f:
                saved_cfg = json.load(f)
            self.assertEqual(saved_cfg.get("SESSION"), "london")
        finally:
            if os.path.exists(workspace_test_dir):
                try: shutil.rmtree(workspace_test_dir)
                except: pass

if __name__ == "__main__":
    unittest.main()
