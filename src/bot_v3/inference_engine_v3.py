import os
import traceback
try:
    import torch
    import torch.nn.functional as F
except ImportError:
    torch = None


class V3InferenceEngine:
    """Động Cơ AI phi tuyến V3 (AAMT_Model).
    
    Phân loại đầu ra 3 giá trị: [0=Sell, 1=Hold, 2=Buy]
    Màng lọc MSE rác.
    """

    def __init__(self, log_callback=None):
        self.device = (
            torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            if torch else "mock"
        )
        self.model = None
        self.log_callback = log_callback or print
        
        # Sẽ được cấu hình sau từ config lúc chạy (bot_v3.py gọi method override nếu cần)
        self.mse_threshold = 70.0 # Tạm thời fallback
        self.prob_threshold = 0.7
        
        device_str = getattr(self.device, 'type', 'mock').upper()
        self.log_callback(f"[InferenceEngineV3] Khởi tạo | device={device_str}")

    def load_weights(self, model_path: str, num_features: int, d_model: int,
                     nhead: int, num_attn_layers: int, window_size: int = 60) -> bool:
        """Nạp AAMT_Model V3 từ file .pth"""
        self.log_callback(
            f"[InferenceEngineV3] ⏳ Nạp model | path={os.path.basename(model_path)} "
            f"| input_dim={num_features} seq_len={window_size} d_model={d_model} "
            f"nhead={nhead} layers={num_attn_layers}"
        )
        try:
            import sys
            safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if safe_script_dir not in sys.path:
                sys.path.insert(0, safe_script_dir)

            from src.training_v3.model_v3 import AAMT_Model

            state_dict = torch.load(model_path, map_location=self.device, weights_only=True)
            
            # Khắc phục triệt để lỗi Toán Học đầu vào: tự động suy luận input_dim từ bộ lưu trọng số
            try:
                detected_dim = state_dict['encoder.input_projection.weight'].shape[1]
                if detected_dim != num_features:
                    self.log_callback(f"[InferenceEngineV3] ⚠️ Ghi đè Cột Đầu Vào từ {num_features} -> {detected_dim} theo Model Weights.")
                    num_features = detected_dim
            except KeyError:
                pass

            self.model = AAMT_Model(
                input_dim=num_features,
                seq_len=window_size,
                d_model=d_model,
                nhead=nhead,
                num_layers=num_attn_layers,
                num_classes=3
            ).to(self.device)

            self.model.load_state_dict(state_dict)
            self.model.eval()
            self.num_features = num_features

            device_str = getattr(self.device, 'type', 'mock').upper()
            param_count = sum(p.numel() for p in self.model.parameters())
            self.log_callback(
                f"[InferenceEngineV3] 🌟 Model AAMT nạp thành công vào {device_str} | "
                f"params={param_count:,}"
            )
            return True
        except Exception as e:
            self.log_callback(f"[InferenceEngineV3] ❌ Lỗi nạp trọng số: {e}")
            self.log_callback(traceback.format_exc())
            self.model = None
            return False

    def predict(self, x_tensor) -> tuple:
        """Nhận tensor 3D, trả về (Action, mse_loss, probs_dict).
        
        Action in ["BUY", "SELL", "HOLD", "TÍN_HIỆU_RÁC"]
        Returns (action, mse, dict) hoặc (None, None, None)
        """
        if self.model is None:
            self.log_callback("[InferenceEngineV3] ❌ Giao thức predict() thất bại: Chưa khởi động Não!")
            return None, None, None

        try:
            if type(x_tensor).__name__ not in ('Tensor', 'MagicMock'):
                x_tensor = torch.tensor(x_tensor, dtype=torch.float32)

            input_shape = tuple(x_tensor.shape)
            x_tensor = x_tensor.to(self.device)

            with torch.no_grad():
                reconstructed, logits, _ = self.model(x_tensor)
                
                # Tính Loss (AutoEncoder MSE)
                mse_loss = F.mse_loss(reconstructed, x_tensor).item()
                
                # Lấy xác suất từ 3 class [Sell=0, Buy=1, Sideway=2] bằng Softmax
                probs = F.softmax(logits, dim=-1).cpu().numpy()[0]
                
                out_dict = {
                    "sell": float(probs[0]),  # Class 0: Sell
                    "buy": float(probs[1]),   # Class 1: Buy  ← khớp với LabelingV3
                    "hold": float(probs[2])   # Class 2: Sideway/Hold
                }
                
                action = "HOLD"
                
                # Kiểm duyệt rác
                if mse_loss > self.mse_threshold:
                    action = "TÍN_HIỆU_RÁC"
                else:
                    if out_dict["buy"] >= self.prob_threshold:
                        action = "BUY"
                    elif out_dict["sell"] >= self.prob_threshold:
                        action = "SELL"
                        
            self.log_callback(
                f"[InferenceEngineV3] 🎯 Kêt quả | Hành động={action} | MSE_Loss={mse_loss:.4f} | "
                f"S:{out_dict['sell']:.2f} H:{out_dict['hold']:.2f} B:{out_dict['buy']:.2f}"
            )
            return action, mse_loss, out_dict

        except Exception as e:
            self.log_callback(f"[InferenceEngineV3] ❌ Lỗi suy diễn Pytorch: {e}")
            self.log_callback(traceback.format_exc())
            return None, None, None
