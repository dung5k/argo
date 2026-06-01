import sys
import os
import unittest
import torch
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bot_v6.inference_engine_v6 import V6InferenceEngine
from src.training_v6.model_v6 import AAMT_MTF_Model

class DummyConfig:
    def get(self, key, default=None):
        return default

class TestInferenceEngineV6Robustness(unittest.TestCase):
    def setUp(self):
        self.engine = V6InferenceEngine(config={}, force_cpu=True, log_callback=lambda x: None)
        
        # Create a dummy V6 model
        # 3 timeframes: input_dims=[6, 1, 1], seq_lens=[10, 10, 10]
        self.input_dims = [6, 1, 1]
        self.seq_lens = [10, 10, 10]
        self.d_model = 16
        self.model = AAMT_MTF_Model(
            input_dims=self.input_dims,
            seq_lens=self.seq_lens,
            d_model=self.d_model,
            nhead=2,
            num_layers=1,
            num_classes=3
        )
        self.model.eval()
        self.engine.model = self.model
    
    def test_predict_probs_with_2d_numpy_arrays(self):
        """Test simulator scenario: input is unbatched 2D numpy arrays (seq_len, features)"""
        x_list = [
            np.random.rand(self.seq_lens[0], self.input_dims[0]).astype(np.float32),
            np.random.rand(self.seq_lens[1], self.input_dims[1]).astype(np.float32),
            np.random.rand(self.seq_lens[2], self.input_dims[2]).astype(np.float32)
        ]
        
        # Should NOT throw RuntimeError about tensor dimensions
        try:
            res = self.engine.predict_probs(x_list)
            self.assertIsNotNone(res)
            self.assertEqual(len(res), 3) # p_sell, p_hold, p_buy
        except Exception as e:
            self.fail(f"predict_probs failed with 2D numpy arrays: {e}")

    def test_predict_probs_with_3d_numpy_arrays(self):
        """Test batched scenario: input is batched 3D numpy arrays (batch, seq_len, features)"""
        x_list = [
            np.random.rand(1, self.seq_lens[0], self.input_dims[0]).astype(np.float32),
            np.random.rand(1, self.seq_lens[1], self.input_dims[1]).astype(np.float32),
            np.random.rand(1, self.seq_lens[2], self.input_dims[2]).astype(np.float32)
        ]
        
        try:
            res = self.engine.predict_probs(x_list)
            self.assertIsNotNone(res)
            self.assertEqual(len(res), 3)
        except Exception as e:
            self.fail(f"predict_probs failed with 3D numpy arrays: {e}")

    def test_predict_probs_with_2d_tensors(self):
        """Test unbatched scenario: input is 2D PyTorch tensors"""
        x_list = [
            torch.rand(self.seq_lens[0], self.input_dims[0]),
            torch.rand(self.seq_lens[1], self.input_dims[1]),
            torch.rand(self.seq_lens[2], self.input_dims[2])
        ]
        
        try:
            res = self.engine.predict_probs(x_list)
            self.assertIsNotNone(res)
            self.assertEqual(len(res), 3)
        except Exception as e:
            self.fail(f"predict_probs failed with 2D tensors: {e}")

    def test_predict_probs_with_3d_tensors(self):
        """Test batched scenario: input is 3D PyTorch tensors"""
        x_list = [
            torch.rand(1, self.seq_lens[0], self.input_dims[0]),
            torch.rand(1, self.seq_lens[1], self.input_dims[1]),
            torch.rand(1, self.seq_lens[2], self.input_dims[2])
        ]
        
        try:
            res = self.engine.predict_probs(x_list)
            self.assertIsNotNone(res)
            self.assertEqual(len(res), 3)
        except Exception as e:
            self.fail(f"predict_probs failed with 3D tensors: {e}")

    def test_predict_with_2d_numpy_arrays(self):
        """Test predict method with unbatched 2D numpy arrays"""
        x_list = [
            np.random.rand(self.seq_lens[0], self.input_dims[0]).astype(np.float32),
            np.random.rand(self.seq_lens[1], self.input_dims[1]).astype(np.float32),
            np.random.rand(self.seq_lens[2], self.input_dims[2]).astype(np.float32)
        ]
        
        try:
            res = self.engine.predict(x_list)
            self.assertIsNotNone(res)
            self.assertIn(res, [0, 1, 2]) # class label
        except Exception as e:
            self.fail(f"predict failed with 2D numpy arrays: {e}")

if __name__ == '__main__':
    unittest.main()
