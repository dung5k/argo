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
from src.core.constants import TradingAction

class V6InferenceEngine:
    """Động Cơ AI phi tuyến V6 (AAMT_MTF_Model) hỗ trợ Multi-Timeframe.
    
    Phân loại đầu ra 3 giá trị: [0=Sell, 1=Hold, 2=Buy]
    Màng lọc Prob.
    """

    def __init__(self, model_path: str = None, config: dict = None, log_callback=None, force_cpu: bool = False):
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
        if force_cpu:
            self.device = torch.device('cpu')
        else:
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
            state_dict = torch.load(model_path, map_location=self.device)
            # DYNAMICALLY CHECK NUMBER OF ENCODERS
            encoder_keys = [k for k in state_dict.keys() if k.startswith("encoders.")]
            if encoder_keys:
                import re
                encoder_indices = set(int(re.search(r"encoders\.(\d+)", k).group(1)) for k in encoder_keys)
                num_encoders_in_model = max(encoder_indices) + 1
                if len(input_dims) > num_encoders_in_model:
                    self.log_callback(f"[InferenceEngineV6] WARNING: Config có {len(input_dims)} inputs, nhưng model chỉ có {num_encoders_in_model} encoders. Đang cắt bớt cấu hình đầu vào!")
                    input_dims = input_dims[:num_encoders_in_model]
                    seq_lens = seq_lens[:num_encoders_in_model]
                    if "FEATURE_ENGINEERING" in self.config and "MTF_INPUTS" in self.config["FEATURE_ENGINEERING"]:
                        self.config["FEATURE_ENGINEERING"]["MTF_INPUTS"] = self.config["FEATURE_ENGINEERING"]["MTF_INPUTS"][:num_encoders_in_model]
            
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
                        t = torch.tensor(x, dtype=torch.float32)
                        if t.dim() == 2:
                            t = t.unsqueeze(0)
                        x_tensors_pt.append(t.to(self.device))
                    else:
                        t = x.clone() if isinstance(x, torch.Tensor) else torch.tensor(x)
                        if t.dim() == 2:
                            t = t.unsqueeze(0)
                        x_tensors_pt.append(t.to(self.device))
                
                _, logits, _ = self.model(x_tensors_pt)
                
                probs = F.softmax(logits, dim=-1) # [1, 3]
                
                # Sử dụng TradingAction Enum thống nhất cấu trúc nhãn
                p_sell = probs[0, TradingAction.SELL.value].item()
                p_buy  = probs[0, TradingAction.BUY.value].item()
                
                if p_buy >= self.prob_threshold:
                    return TradingAction.to_bot_action(TradingAction.BUY.value)
                elif p_sell >= self.prob_threshold:
                    return TradingAction.to_bot_action(TradingAction.SELL.value)
                else:
                    return TradingAction.to_bot_action(TradingAction.HOLD.value)
                    
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
                        t = torch.tensor(x, dtype=torch.float32)
                        if t.dim() == 2:
                            t = t.unsqueeze(0)
                        x_tensors_pt.append(t.to(self.device))
                    else:
                        t = x.clone() if isinstance(x, torch.Tensor) else torch.tensor(x)
                        if t.dim() == 2:
                            t = t.unsqueeze(0)
                        x_tensors_pt.append(t.to(self.device))
                
                _, logits, _ = self.model(x_tensors_pt)
                probs = F.softmax(logits, dim=-1) # [1, 3]
                
                # Sử dụng TradingAction Enum thống nhất cấu trúc nhãn
                p_sell = probs[0, TradingAction.SELL.value].item()
                p_hold = probs[0, TradingAction.HOLD.value].item()
                p_buy  = probs[0, TradingAction.BUY.value].item()
                
                return p_sell, p_hold, p_buy
                
        except Exception as e:
            self.log_callback(f"[InferenceEngineV6] Lỗi predict_probs: {e}")
            import traceback
            traceback.print_exc()
            return None
