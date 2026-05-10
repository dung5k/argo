import numpy as np
import os
import sys
import traceback

try:
    import torch
    import torch.nn.functional as F
except ImportError:
    torch = None

class V6InferenceEngine:
    def __init__(self, log_callback=None):
        self.device = torch.device('cpu') if torch else "mock"
        self.model = None
        self.log_callback = log_callback or print
        self.mse_threshold = 70.0
        self.prob_threshold = 0.7
        self.log_callback(f"[InferenceEngineV6] Khởi tạo | device={getattr(self.device, 'type', 'mock').upper()}")

    def load_weights(self, model_path: str, config: dict) -> bool:
        self.log_callback(f"[InferenceEngineV6] ⏳ Nạp model V6 MTF | path={os.path.basename(model_path)}")
        try:
            safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if safe_script_dir not in sys.path:
                sys.path.insert(0, safe_script_dir)

            from src.training_v6.model_v6 import AAMT_MTF_Model
            from packaging import version
            
            load_kwargs = {"map_location": self.device}
            if version.parse(torch.__version__) >= version.parse("1.13.0"):
                load_kwargs["weights_only"] = True
                
            state_dict = torch.load(model_path, **load_kwargs)
            
            arch = config.get("TRAINING", {})
            d_model = arch.get("D_MODEL", 32)
            nhead = arch.get("N_HEAD", 4)
            num_layers = arch.get("NUM_LAYERS", 2)
            
            fe_cfg = config.get("FEATURE_ENGINEERING", {})
            mtf_inputs = fe_cfg.get("MTF_INPUTS", [])
            
            input_dims = [len(tf.get("FEATURES", [])) for tf in mtf_inputs]
            seq_lens = [tf.get("WINDOW_SIZE", 60) for tf in mtf_inputs]
            
            self.model = AAMT_MTF_Model(
                input_dims=input_dims,
                seq_lens=seq_lens,
                d_model=d_model,
                nhead=nhead,
                num_layers=num_layers,
                num_classes=3,
                pooling='mean',
                cls_head=arch.get('CLS_HEAD', 'simple')
            ).to(self.device)

            self.model.load_state_dict(state_dict)
            self.model.eval()
            self.log_callback("[InferenceEngineV6] ✅ Nạp weights thành công.")
            return True
        except Exception as e:
            self.log_callback(f"[InferenceEngineV6] ❌ Lỗi load weights: {e}")
            self.log_callback(traceback.format_exc())
            return False

    def predict(self, X_list: list) -> dict:
        if not self.model or not X_list:
            return {"action": 1, "prob": 0.0, "mse": 0.0, "raw": None}
            
        try:
            tensor_list = [torch.FloatTensor(x).to(self.device) for x in X_list]
            
            with torch.no_grad():
                reconstructed_list, logits, _ = self.model(tensor_list)
                probs = F.softmax(logits, dim=-1)[0].cpu().numpy()
                
                # Tính MSE cho base timeframe (tensor đầu tiên)
                mse = F.mse_loss(reconstructed_list[0], tensor_list[0]).item()
                
            pred_class = int(np.argmax(probs))
            max_prob = float(probs[pred_class])
            
            # LabelingV3 mapping: 0=Sell, 1=Buy, 2=Sideway
            action = 1 # Default is Hold
            if pred_class == 1 and max_prob >= self.prob_threshold:
                action = 2 # In VirtualTradeManager, 2 = BUY
            elif pred_class == 0 and max_prob >= self.prob_threshold:
                action = 0 # In VirtualTradeManager, 0 = SELL
                
            return {
                "action": action,
                "prob": max_prob,
                "mse": mse,
                "raw": probs.tolist(),
                "class": pred_class
            }
        except Exception as e:
            self.log_callback(f"[InferenceEngineV6] ❌ Lỗi predict: {e}")
            return {"action": 1, "prob": 0.0, "mse": 0.0, "raw": None}
