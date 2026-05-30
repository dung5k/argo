import os
import traceback
from typing import List, Optional, Tuple
import numpy as np
try:
    import torch
    import torch.nn.functional as F
except ImportError:
    torch = None

from src.training_v6.model_v6 import AAMT_MTF_Model

class V6InferenceEngine:
    """Động Cơ AI phi tuyến V6 (AAMT_MTF_Model) hỗ trợ Multi-Timeframe.
    
    Phân loại đầu ra 3 giá trị: [0=Sell, 1=Hold, 2=Buy]
    Màng lọc Prob.
    """

    def __init__(self, model_path: str = None, config: dict = None, log_callback=None):
        """
        Khởi tạo V6InferenceEngine.
        Nếu truyền model_path thì sẽ gọi luôn load_weights().
        """
        self.model_path = model_path
        self.config = config or {}
        self.log_callback = log_callback or (lambda x: print(x))
        self.model = None
        self.scaler = None
        
        # Sửa thành tự động nhận diện CUDA
        self.device = torch.device('cuda' if torch and torch.cuda.is_available() else 'cpu')
        device_str = getattr(self.device, 'type', 'mock').upper()
        if device_str == 'CUDA':
            device_str += f" ({torch.cuda.get_device_name(0)})"
        self.log_callback(f"[InferenceEngineV6] Khởi tạo | device={device_str}")

        self.prob_threshold = 0.55

    def load_weights(self, model_path: str, input_dims: List[int], seq_lens: List[int], d_model: int,
                     nhead: int, num_attn_layers: int, pooling: str = 'mean', cls_head: str = 'simple') -> bool:
        """
        Load model weights cho V6 MTF.
        """
        if torch is None:
            self.log_callback("[InferenceEngineV6] ⚠️ Không thể load model vì pytorch chưa cài đặt!")
            return False

        if not os.path.exists(model_path):
            self.log_callback(f"[InferenceEngineV6] ❌ File Không Tồn Tại: {model_path}")
            return False

        try:
            self.model = AAMT_MTF_Model(
                input_dims=input_dims,
                seq_lens=seq_lens,
                d_model=d_model,
                nhead=nhead,
                num_layers=num_attn_layers,
                num_classes=3,
                pooling=pooling,
                cls_head=cls_head,
                layer_drop=0.0
            )

            state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()

            self.log_callback(f"[InferenceEngineV6] ✔️ Load weights thành công: {os.path.basename(model_path)}")
            self.log_callback(f"   └ input_dims={input_dims}, seq_lens={seq_lens}, params={sum(p.numel() for p in self.model.parameters())}")
            return True
        except Exception as e:
            self.log_callback(f"[InferenceEngineV6] ❌ Lỗi Load Weights: {e}")
            self.log_callback(traceback.format_exc())
            return False

    def predict(self, x_tensors: List[torch.Tensor]) -> Optional[int]:
        """
        Suy luận online Multi-Timeframe.
        """
        if self.model is None or torch is None:
            return None

        try:
            with torch.no_grad():
                # Move x_tensors to device
                x_tensors_pt = []
                for x in x_tensors:
                    if isinstance(x, np.ndarray):
                        x_tensors_pt.append(torch.tensor(x, dtype=torch.float32).to(self.device))
                    else:
                        x_tensors_pt.append(x.to(self.device))
                
                _, logits, _ = self.model(x_tensors_pt)
                
                probs = F.softmax(logits, dim=-1) # [1, 3]
                
                p_sell = probs[0, 0].item()
                p_buy  = probs[0, 2].item()
                
                if p_buy >= self.prob_threshold:
                    return 2 # BUY
                elif p_sell >= self.prob_threshold:
                    return 0 # SELL
                else:
                    return 1 # HOLD
                    
        except Exception as e:
            self.log_callback(f"[InferenceEngineV6] Lỗi predict: {e}")
            import traceback
            traceback.print_exc()
            return None

    def predict_probs(self, x_tensors: List[torch.Tensor]) -> Optional[Tuple[float, float, float]]:
        """
        Trá về xác suất (p_sell, p_hold, p_buy) mà không áp threshold, giúp tiết kiệm tính toán khi test nhiều threshold.
        """
        if self.model is None or torch is None:
            return None

        try:
            with torch.no_grad():
                x_tensors_pt = []
                for x in x_tensors:
                    if isinstance(x, np.ndarray):
                        x_tensors_pt.append(torch.tensor(x, dtype=torch.float32).to(self.device))
                    else:
                        x_tensors_pt.append(x.to(self.device))
                
                _, logits, _ = self.model(x_tensors_pt)
                probs = F.softmax(logits, dim=-1) # [1, 3]
                
                p_sell = probs[0, 0].item()
                p_hold = probs[0, 1].item()
                p_buy  = probs[0, 2].item()
                
                return p_sell, p_hold, p_buy
                
        except Exception as e:
            self.log_callback(f"[InferenceEngineV6] Lỗi predict_probs: {e}")
            import traceback
            traceback.print_exc()
            return None
