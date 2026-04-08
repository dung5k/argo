import os
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.bot_v2.cloud_manager_v2 import V2CloudManager

class TestV2CloudManager(unittest.TestCase):

    def setUp(self):
        self.manager = V2CloudManager("xauusd", "XAU_USD", "fake_token", log_callback=lambda x: None)

    def test_translate_weight_name(self):
        self.assertEqual(
            self.manager._translate_weight_name("v2_weights_BEST.pth", "asian"),
            "asia_weights_BEST.pth"
        )
        self.assertEqual(
            self.manager._translate_weight_name("xauusd_unified_weights.pth", "european"),
            "xauusd_london_weights_BEST_VLOSS.pth"
        )

    @patch('src.bot_v2.cloud_manager_v2.HfApi')
    def test_get_latest_run_id(self, mock_api_class):
        mock_api = MagicMock()
        mock_api.list_repo_files.return_value = [
            "runs/run_20260408_144446_xauusd_CFG/abc.pth",
            "runs/run_20260409_144446_xauusd_CFG/asia_weights_BEST.pth",
            "runs/old_run/asia_weights_BEST.pth",
        ]
        
        latest = self.manager.get_latest_run_id(mock_api, "asia_weights_BEST.pth")
        self.assertEqual(latest, "run_20260409_144446_xauusd_CFG")

    @patch('src.bot_v2.cloud_manager_v2.hf_hub_download')
    @patch('src.bot_v2.cloud_manager_v2.V2CloudManager.get_latest_run_id')
    @patch('shutil.copy')
    @patch('os.path.exists')
    def test_sync_session_model_success(self, mock_exists, mock_copy, mock_get_latest, mock_hub_download):
        mock_get_latest.return_value = "mock_run"
        mock_hub_download.return_value = "mock_path_to_weight.pth"
        
        # Override file exists checks so it thinks models and metadata exist
        mock_exists.return_value = True
        
        fake_json = '{"num_xau_features": 12, "data_features": ["f1", "f2", "f3"]}'
        
        with patch('builtins.open', unittest.mock.mock_open(read_data=fake_json)):
            model_path, active_name, num_xau, num_feat, feats = self.manager.sync_session_model(
                "v2_weights_BEST.pth", "asian"
            )
            
        self.assertEqual(model_path, "mock_path_to_weight.pth")
        self.assertIn("mock_run", active_name)
        self.assertEqual(num_xau, 12)
        self.assertEqual(num_feat, 3)

if __name__ == '__main__':
    unittest.main()
