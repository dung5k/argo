import os
import sys
import torch
import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from scripts.prepare_v6_dataset import resample_dataframe, align_mtf_windows, get_split_class
from src.training_v6.model_v6 import AAMT_MTF_Model

class TestV6Pipeline(unittest.TestCase):
    
    def test_resample_dataframe(self):
        # Tạo mock df_raw (1m data)
        times = [datetime(2025, 1, 1, 10, i) for i in range(15)]
        data = {
            'LTCUSDT_open': np.arange(1, 16, dtype=float),
            'LTCUSDT_high': np.arange(1, 16, dtype=float) + 1,
            'LTCUSDT_low': np.arange(1, 16, dtype=float) - 1,
            'LTCUSDT_close': np.arange(1, 16, dtype=float),
            'LTCUSDT_volume': np.ones(15) * 10
        }
        df_raw = pd.DataFrame(data, index=pd.DatetimeIndex(times))
        
        # Resample to 5m
        df_5m = resample_dataframe(df_raw, '5T')
        
        # 15 phút chia thành 3 nến 5m
        self.assertEqual(len(df_5m), 3)
        self.assertEqual(df_5m['LTCUSDT_open'].iloc[0], 1.0)
        self.assertEqual(df_5m['LTCUSDT_close'].iloc[0], 5.0)
        self.assertEqual(df_5m['LTCUSDT_volume'].iloc[0], 50.0)
        
    def test_align_mtf_windows(self):
        # Base TF: 1m, HTF: 5m
        times_1m = [datetime(2025, 1, 1, 10, i) for i in range(15)]
        vals_1m = np.arange(15).reshape(15, 1)
        
        times_5m = [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 10, 5), datetime(2025, 1, 1, 10, 10)]
        vals_5m = np.array([100, 200, 300]).reshape(3, 1)
        
        tf_times = [pd.DatetimeIndex(times_1m), pd.DatetimeIndex(times_5m)]
        tf_vals = [vals_1m, vals_5m]
        
        target_time = datetime(2025, 1, 1, 10, 11)
        target_idx = 11
        # Lấy window_size_1m = 3, window_size_5m = 2
        # win_1m: nến index 9, 10, 11 (vì target_idx = 11, length = 3)
        # target_time là 10:11. Nến 5m gần nhất <= 10:11 là 10:10 (val=300). Nến trước đó là 10:05 (val=200).
        
        windows, has_nan = align_mtf_windows(
            target_time, 
            i=9, # target_idx - win_size + 1 = 11 - 3 + 1 = 9
            target_idx=11, 
            tf_times=tf_times, 
            tf_vals=tf_vals, 
            window_sizes=[3, 2]
        )
        
        self.assertFalse(has_nan)
        self.assertEqual(windows[0].shape, (3, 1))
        self.assertEqual(windows[1].shape, (2, 1))
        
        # Kiểm tra giá trị base
        np.testing.assert_array_equal(windows[0].flatten(), [9, 10, 11])
        # Kiểm tra giá trị HTF
        np.testing.assert_array_equal(windows[1].flatten(), [200, 300])
        
    def test_model_v6_forward(self):
        # Fake input tensor sizes: [Batch, Seq, Features]
        batch_size = 4
        features = 43
        seq1 = 60
        seq2 = 16
        
        x1 = torch.randn(batch_size, seq1, features)
        x2 = torch.randn(batch_size, seq2, features)
        
        model = AAMT_MTF_Model(
            input_dims=[features, features],
            seq_lens=[seq1, seq2],
            d_model=64,
            nhead=4,
            num_layers=2,
            num_classes=3,
            cls_head='residual'
        )
        
        reconstructeds, logits, latent_fusion = model([x1, x2])
        
        self.assertEqual(len(reconstructeds), 2)
        self.assertEqual(reconstructeds[0].shape, (batch_size, seq1, features))
        self.assertEqual(reconstructeds[1].shape, (batch_size, seq2, features))
        
        self.assertEqual(logits.shape, (batch_size, 3))
        self.assertEqual(latent_fusion.shape, (batch_size, 128)) # d_model(64) * 2 = 128
        
if __name__ == '__main__':
    unittest.main()
