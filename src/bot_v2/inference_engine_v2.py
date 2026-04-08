import os
try:
    import torch
except ImportError:
    torch = None
from pathlib import Path

class V2InferenceEngine:
    """Lõi Động cơ Pytorch tải Neural Network và trả về Xác suất quyết định (Softmax)"""
    
    def __init__(self, log_callback=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if torch else "mock"
        self.model = None
        self.log_callback = log_callback or print

    def load_weights(self, model_path: str, num_features: int, d_model: int, 
                     nhead: int, num_attn_layers: int, dropout_rate: float, num_xau_features: int = 8):
        """Khởi tạo TransformerModel và tải trọng số"""
        try:
            # 1. Tránh lỗi Module Not Found cho TransformerModel
            import sys
            safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if safe_script_dir not in sys.path:
                sys.path.insert(0, safe_script_dir)
                
            from src.legacy.train_ga import TransformerModel
            
            # 2. Khởi tạo
            self.model = TransformerModel(
                num_features=num_features, 
                d_model=d_model, 
                nhead=nhead,
                num_layers=num_attn_layers, 
                dropout_rate=dropout_rate,
                num_xau_features=num_xau_features
            ).to(self.device)
            
            # 3. Nạp trọng số
            self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
            self.model.eval()
            device_str = getattr(self.device, 'type', 'mock').upper()
            self.log_callback(f"[InferenceEngine] ✅ Đã nạp thành công Mạng Nơ ron Lượng tử vào {device_str}")
            return True
        except Exception as e:
            self.log_callback(f"[InferenceEngine] ❌ Lỗi Nạp Trọng số: {e}")
            return False

    def predict(self, x_tensor):
        """
        Nhận Tensor 3D (Batch=1, Seq=Win, Feat), đẩy qua Mạng và xuất Xác suất.
        Trả về (prediction_score, raw_logits) hoặc (None, None) nếu lỗi.
        """
        if self.model is None:
            self.log_callback("[InferenceEngine] Mô hình chưa được tải!")
            return None, None
            
        try:
            if type(x_tensor).__name__ != 'Tensor' and type(x_tensor).__name__ != 'MagicMock':
                x_tensor = torch.tensor(x_tensor, dtype=torch.float32)
                
            x_tensor = x_tensor.to(self.device)
            
            with torch.no_grad():
                output = self.model(x_tensor)
                
                # Hàm Softmax lấy độ tự tin
                probs = torch.softmax(output.data, dim=1).squeeze()
                
                # Phe Gấu (0) và Phe Bò (1)
                if probs.dim() == 0:
                    probs = probs.unsqueeze(0)
                prob_down, prob_up = probs[0].item(), probs[1].item()
                prediction = prob_up 
                
                raw_logits = output.cpu().numpy()[0]
                
            return prediction, raw_logits
        except Exception as e:
            self.log_callback(f"[InferenceEngine] ❌ Lỗi Suy diễn Pytorch: {e}")
            import traceback
            self.log_callback(traceback.format_exc())
            return None, None
