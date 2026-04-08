import sys
import os
import unittest
import pandas as pd
import numpy as np
import torch
from unittest.mock import MagicMock

# Đưa src vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.training_v1_5.train_v1_5 import TimeSeriesDatasetV1_5, PhoenixRestartV1_5

class TestTrainingV1_5(unittest.TestCase):

    def setUp(self):
        # Giả lập dữ liệu Features (71 côt) với 100 nến (chạy qua nhiều hour khác nhau)
        # Giả lập timezone 'UTC' để check logic Session
        dates = pd.date_range(start='2026-04-01 00:00:00', periods=100, freq='h', tz='UTC')
        features_data = np.random.rand(100, 71)
        self.features = pd.DataFrame(features_data, index=dates)

        # Giả lập Targets
        targets_data = {"target": np.random.randint(0, 2, size=100)}
        self.targets = pd.DataFrame(targets_data, index=dates)

    def test_time_series_dataset_session_split(self):
        """Kiểm tra logic phân mảnh phiên Á (0), Âu (1), Mỹ (2) có hoạt động chính xác không"""
        
        # Test với window_size = 10
        dataset = TimeSeriesDatasetV1_5(self.features, self.targets, window_size=10)
        
        # Chiều dài phải = len(features) - window_size = 100 - 10 = 90
        self.assertEqual(len(dataset), 90)
        
        # Lấy 1 mẫu kiểm tra
        x, y, s = dataset[0]  # Truy cập index 0 -> target_idx = 9
        
        # Kiểm tra hình dạng
        self.assertEqual(x.shape, torch.Size([10, 71]))
        
        # Hàm __getitem__ sẽ bốc nến cuối cùng để làm target: features.index[9]
        # features.index[9] là 2026-04-01 09:00:00 UTC -> Phiên Âu (1)
        expected_hour = self.features.index[9].hour
        expected_session = 0 if expected_hour < 8 else (1 if expected_hour < 13 else 2)
        
        self.assertEqual(s.item(), expected_session)
        self.assertEqual(y.item(), self.targets.iloc[9]['target'])

    def test_phoenix_restart_stagnation_logic(self):
        """Kiểm tra thuật toán Phoenix có đếm số lần rớt (stagnate) và báo kích hoạt tái sinh chuẩn không"""
        mock_model = MagicMock()
        mock_model.parameters.return_value = [torch.nn.Parameter(torch.tensor([1.0]))]
        
        phoenix = PhoenixRestartV1_5(model=mock_model, base_lr=1e-4, max_phoenix=3, max_stagnate=2)
        
        # Điểm chết lần 1
        should_restart_1 = phoenix.notify_no_improve()
        self.assertFalse(should_restart_1)
        self.assertEqual(phoenix.epochs_no_improve, 1)
        self.assertEqual(phoenix.phoenix_count, 0)
        self.assertFalse(phoenix.exhausted)
        
        # Điểm chết lần 2 (Chạm ngưỡng max_stagnate=2)
        should_restart_2 = phoenix.notify_no_improve()
        self.assertTrue(should_restart_2)
        self.assertEqual(phoenix.phoenix_count, 1) # Tái sinh lần 1
        
        # Reset Stagnation
        phoenix.reset_stagnation()
        self.assertEqual(phoenix.epochs_no_improve, 0)
        
        # Kiểm tra kẹt quá giới hạn (max_phoenix = 3)
        phoenix.phoenix_count = 3
        should_restart_fail = phoenix.notify_no_improve() # stagnation 1
        should_restart_fail = phoenix.notify_no_improve() # stagnation 2 -> trigger phoenix_count = 4
        self.assertFalse(should_restart_fail) # Báo false vì Exhausted!
        self.assertTrue(phoenix.exhausted)

if __name__ == '__main__':
    unittest.main()
