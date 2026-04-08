import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.bot_v2.data_processor_v2 import V2DataProcessor

class TestV2DataProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = V2DataProcessor(
            scaler_path="fake.pkl",
            inference_feats=["XAU_USD_close", "Macro_USD_VIX"],
            window_size=10,
            log_callback=lambda x: None
        )

    @patch('src.bot_v2.data_processor_v2.V2DataProcessor._init_pipeline')
    @patch('src.core.feature_engineering.create_stationary_features')
    def test_ingest_and_scale_success(self, mock_feature_eng, mock_init_pipeline):
        # Giả lập pipeline
        mock_init_pipeline.return_value = True
        self.processor.pipeline = MagicMock()
        
        # 1. Feature Eng returns 15 rows
        fake_fe_df = pd.DataFrame({
            "XAU_USD_close": np.random.randn(15),
            "Unrelated_Col": np.random.randn(15)
        })
        mock_feature_eng.return_value = fake_fe_df
        
        # 2. Pipeline transform returns scaled dataframe
        fake_scaled_df = pd.DataFrame({
            "XAU_USD_close": np.random.randn(15), 
            "Unrelated_Col": np.random.randn(15)
        })
        self.processor.pipeline.transform.return_value = fake_scaled_df
        
        # Call it
        raw_df = pd.DataFrame()
        tensor_seq, err = self.processor.ingest_and_scale(raw_df)
        
        self.assertIsNone(err)
        self.assertIsNotNone(tensor_seq)
        
        # Shape test: (batch=1, window=10, num_features=2) -> either numpy array or tensor depending on env fallback
        # Because we requested 2 features (XAU_USD_close and Macro_USD_VIX).
        is_numpy = isinstance(tensor_seq, np.ndarray)
        if is_numpy:
            self.assertEqual(tensor_seq.shape, (10, 2))
            macro_vix_slice = tensor_seq[:, 1]
        else:
            self.assertEqual(tensor_seq.shape, (1, 10, 2))
            macro_vix_slice = tensor_seq[0, :, 1].numpy()
            
        # Since Macro_USD_VIX was missing from scaled df, processor should auto-pad with 0
        self.assertTrue(np.all(macro_vix_slice == 0.0))

    @patch('src.bot_v2.data_processor_v2.V2DataProcessor._init_pipeline')
    @patch('src.core.feature_engineering.create_stationary_features')
    def test_ingest_and_scale_not_enough_data(self, mock_feature_eng, mock_init_pipeline):
        mock_init_pipeline.return_value = True
        self.processor.pipeline = MagicMock()
        
        # Return only 5 rows (less than window=10)
        fake_fe_df = pd.DataFrame({
            "XAU_USD_close": np.random.randn(5),
        })
        mock_feature_eng.return_value = fake_fe_df
        
        tensor_seq, err = self.processor.ingest_and_scale(pd.DataFrame())
        
        self.assertIsNone(tensor_seq)
        self.assertIn("Không đủ 10 nến", err)

if __name__ == '__main__':
    unittest.main()
