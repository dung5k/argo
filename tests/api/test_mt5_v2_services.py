import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from src.api.mt5_v2_services import BrainManager, PredictionService

class TestMT5V2Services(unittest.TestCase):
    def setUp(self):
        self.mock_brain_manager = MagicMock(spec=BrainManager)
        
        # Giả lập trả về engine và config rỗng
        mock_engine = MagicMock()
        # Sửa mock để handle batch size thông qua side_effect
        import torch
        def mock_model_forward(x):
            batch_size = x.shape[0] if len(x.shape) > 0 else 1
            return torch.tensor([[0.4, 0.6]] * batch_size)
            
        mock_engine.model.side_effect = mock_model_forward
        mock_engine.device = torch.device('cpu')
        mock_engine.predict.return_value = (0.6, [1.0, 2.0])
        
        self.mock_brain_manager.get_brain_for_time.return_value = (
            "asian", 
            mock_engine, 
            {
                "MODEL_INPUT": {"window_size": 60},
                "FEATURE_ENGINEERING": {"scaler_path": "data/scaler_v2_1.pkl"},
                "MODEL_DIMENSIONS": {"num_features": 38}
            }
        )

    @patch("src.api.mt5_v2_services.MT5DataManager")
    @patch("src.api.mt5_v2_services.V2DataProcessor")
    def test_prediction_service_live(self, mock_processor_cls, mock_mt5_cls):
        """Test xem PredictionService có trả về Data chuẩn cho hàm Live Predict hay không."""
        mock_mt5 = mock_mt5_cls.return_value
        dates = pd.date_range("2026-04-16 10:00:00", periods=120, freq="min", tz=timezone.utc)
        df = pd.DataFrame({"open": np.random.rand(120), "close": np.random.rand(120)}, index=dates)
        mock_mt5.get_live_merged_data_in_memory.return_value = (df, {"XAUUSDm": df}, None)
        
        mock_processor = mock_processor_cls.return_value
        mock_processor.ingest_and_scale.return_value = True
        
        import torch
        mock_processor.to_tensor.return_value = torch.tensor(np.random.rand(1, 60, 38), dtype=torch.float32)
        
        service = PredictionService(self.mock_brain_manager, "mock_path")
        result = service.get_live_prediction()
        
        self.assertIsNotNone(result)
        self.assertIn("timestamp", result)
        self.assertEqual(result["timestamp"], int(dates[-1].timestamp()))
        self.assertEqual(result["prob_up"], 0.6)
        self.assertEqual(result["session"], "asian")
        
        mock_mt5.get_live_merged_data_in_memory.assert_called_once_with(window=120)

    @patch("src.api.mt5_v2_services.MT5DataManager")
    @patch("src.api.mt5_v2_services.V2DataProcessor")
    def test_prediction_service_history(self, mock_processor_cls, mock_mt5_cls):
        """Test logic sinh Batch cho Lịch Sử, đảm bảo số vector window trượt chính xác."""
        mock_mt5 = mock_mt5_cls.return_value
        
        limit = 300
        total_candles = limit + 120
        dates = pd.date_range("2026-04-16 00:00:00", periods=total_candles, freq="min", tz=timezone.utc)
        df = pd.DataFrame({"open": np.random.rand(total_candles), "close": np.random.rand(total_candles)}, index=dates)
        mock_mt5.get_live_merged_data_in_memory.return_value = (df, {"XAUUSDm": df}, None)
        
        mock_processor = mock_processor_cls.return_value
        mock_processor.ingest_and_scale.return_value = True
        
        scaled_len = total_candles - 60 
        mock_processor.scaled_df = pd.DataFrame(
            np.random.rand(scaled_len, 38), 
            index=dates[60:]
        )
        
        service = PredictionService(self.mock_brain_manager, "mock_path")
        history = service.get_prediction_history(limit=limit)
        
        self.assertIsNotNone(history)
        self.assertLessEqual(len(history), limit)
        
        t_end, prob_end = history[-1]
        self.assertEqual(t_end, int(dates[-1].timestamp()))
        self.assertGreater(prob_end, 0)

if __name__ == '__main__':
    unittest.main()
