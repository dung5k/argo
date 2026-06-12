import os
import sys
import json
import torch
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.v8_engine.transformer_model import V8TransformerModel

class V8InferenceEngine:
    def __init__(self, model_name: str, config_path: str, log_callback=None, threshold=None):
        self.log = log_callback or print
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        self.config_path = config_path
        self.model = None
        
        if threshold is not None:
            self.threshold = threshold
        else:
            self.threshold = 0.30
            # Load Strategy config to get threshold if exists
            strategy_config_path = os.path.join(_ROOT, "v8_configs", "strategy_config.json")
            if os.path.exists(strategy_config_path):
                try:
                    with open(strategy_config_path, "r", encoding="utf-8-sig") as f:
                        strat_cfg = json.load(f)
                        self.threshold = strat_cfg.get("confidence_threshold", 0.30)
                except Exception as e:
                    self.log(f"[V8InferenceEngine] Warning reading strategy config: {e}")
                
        self.load_model()

    def load_model(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            model_path = os.path.join(_ROOT, "v8_configs", "hall_of_fame", self.model_name)
            if not os.path.exists(model_path):
                self.log(f"❌ [V8InferenceEngine] Lỗi: Không tìm thấy model {model_path}")
                return False
                
            self.log(f"[V8InferenceEngine] Đang load model {self.model_name}...")
            state_dict = torch.load(model_path, map_location=self.device, weights_only=False)
            
            layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
            num_layers = max(layer_indices) + 1 if layer_indices else 3
            config['transformer_params']['num_layers'] = num_layers
            
            self.model = V8TransformerModel(config)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            self.log(f"✅ [V8InferenceEngine] Load thành công. Device: {self.device}. Threshold: {self.threshold:.2f}")
            return True
        except Exception as e:
            self.log(f"❌ [V8InferenceEngine] Lỗi load model: {e}")
            return False

    def predict(self, tensors):
        """
        Takes (x_m15, x_h1, x_h4, cont_x, current_price, atr)
        Returns dictionary with signal details
        """
        if self.model is None:
            return {"error": "Model not loaded"}
            
        x_m15, x_h1, x_h4, cont_x, current_price, atr = tensors
        
        x_m15 = x_m15.to(self.device)
        x_h1 = x_h1.to(self.device)
        x_h4 = x_h4.to(self.device)
        cont_x = cont_x.to(self.device)
        
        with torch.no_grad():
            out = self.model(x_m15, x_h1, x_h4, cont_x)
            probs = torch.softmax(out, dim=1)[0] # B=1
            
        prob_s2 = probs[0].item() # Strong Sell
        prob_s1 = probs[1].item() # Weak Sell
        prob_h = probs[2].item()  # Hold
        prob_b1 = probs[3].item() # Weak Buy
        prob_b2 = probs[4].item() # Strong Buy
        
        signal = 2 # Hold
        confidence = prob_h
        action_name = "HOLD"
        
        # Thêm biên lệch tối thiểu (min_delta) để tránh tín hiệu xung đột lưỡng lự
        min_delta = 0.05
        
        if prob_b2 >= self.threshold and prob_b2 > prob_s2 and (prob_b2 - prob_s2) >= min_delta:
            signal = 4
            confidence = prob_b2
            action_name = "STRONG_BUY"
        elif prob_s2 >= self.threshold and prob_s2 > prob_b2 and (prob_s2 - prob_b2) >= min_delta:
            signal = 0
            confidence = prob_s2
            action_name = "STRONG_SELL"
            
        return {
            "signal": signal,
            "action": action_name,
            "confidence": confidence,
            "probs": {
                "S2": prob_s2, "S1": prob_s1, "H": prob_h, "B1": prob_b1, "B2": prob_b2
            },
            "price": current_price,
            "atr": atr
        }
