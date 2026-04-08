import os
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.bot_v2.inference_engine_v2 import V2InferenceEngine

class TestV2InferenceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = V2InferenceEngine(log_callback=lambda x: None)

    @patch('src.bot_v2.inference_engine_v2.torch')
    def test_load_weights_success(self, mock_torch):
        # We need to mock the TransformerModel import inside load_weights
        with patch.dict('sys.modules', {'src.legacy.train_ga': MagicMock()}):
            res = self.engine.load_weights(
                model_path="fake.pth",
                num_features=86,
                d_model=256,
                nhead=8,
                num_attn_layers=3,
                dropout_rate=0.2
            )
            self.assertTrue(res)
            self.assertIsNotNone(self.engine.model)

    @patch('src.bot_v2.inference_engine_v2.torch')
    def test_predict_success(self, mock_torch):
        self.engine.model = MagicMock()
        
        # 1. Setup Mock for model forward passing
        mock_output = MagicMock()
        mock_output.data = [MagicMock(), MagicMock()] # Output representation
        self.engine.model.return_value = mock_output
        
        # 2. Setup mock for Softmax
        # Simulate a [0.3, 0.7] probability out of Softmax
        mock_probs = MagicMock()
        mock_probs.squeeze.return_value = mock_probs
        mock_probs.dim.return_value = 1
        mock_probs.__getitem__.side_effect = [MagicMock(item=lambda: 0.3), MagicMock(item=lambda: 0.7)]
        mock_torch.softmax.return_value = mock_probs
        
        # 3. Predict
        tensor_dummy = MagicMock()
        mock_torch.tensor.return_value = tensor_dummy
        
        # We pass a fake numpy array to trigger typecast inside predict
        pred, logits = self.engine.predict([1, 2, 3])
        
        self.assertIsNotNone(pred)
        self.assertEqual(pred, 0.7) # Should capture prob_up

if __name__ == '__main__':
    unittest.main()
