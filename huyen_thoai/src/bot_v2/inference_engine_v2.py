import os
import traceback
try:
    import torch
except ImportError:
    torch = None


class V2InferenceEngine:
    """Động cơ tải Neural Network và thực hiện suy diễn (inference).

    Trách nhiệm duy nhất: nhận tensor đầu vào → trả về xác suất quyết định.
    Không chứa logic trading hay data processing.
    """

    def __init__(self, log_callback=None):
        self.device = (
            torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            if torch else "mock"
        )
        self.model = None
        self.log_callback = log_callback or print
        device_str = getattr(self.device, 'type', 'mock').upper()
        self.log_callback(f"[InferenceEngine] Khởi tạo | device={device_str}")

    def load_weights(self, model_path: str, num_features: int, d_model: int,
                     nhead: int, num_attn_layers: int, dropout_rate: float,
                     num_xau_features: int = 8) -> bool:
        """Khởi tạo TransformerModel và nạp trọng số từ file .pth.

        Returns: True nếu thành công.
        """
        self.log_callback(
            f"[InferenceEngine] 🔧 Nạp model | path={os.path.basename(model_path)} "
            f"| n_feat={num_features} n_xau={num_xau_features} d_model={d_model} "
            f"nhead={nhead} layers={num_attn_layers} dropout={dropout_rate}"
        )
        try:
            import sys
            safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if safe_script_dir not in sys.path:
                sys.path.insert(0, safe_script_dir)

            from src.core.models.transformer import TransformerModel

            self.model = TransformerModel(
                num_features=num_features,
                d_model=d_model,
                nhead=nhead,
                num_layers=num_attn_layers,
                dropout_rate=dropout_rate,
                num_xau_features=num_xau_features,
            ).to(self.device)

            self.model.load_state_dict(
                torch.load(model_path, map_location=self.device, weights_only=True)
            )
            self.model.eval()

            device_str = getattr(self.device, 'type', 'mock').upper()
            param_count = sum(p.numel() for p in self.model.parameters())
            self.log_callback(
                f"[InferenceEngine] ✅ Model nạp thành công vào {device_str} | "
                f"params={param_count:,}"
            )
            return True
        except Exception as e:
            self.log_callback(f"[InferenceEngine] ❌ Lỗi nạp trọng số: {e}")
            self.log_callback(traceback.format_exc())
            self.model = None
            return False

    def predict(self, x_tensor) -> tuple:
        """Nhận tensor 3D (Batch=1, Seq=Win, Feat), trả về (prob_up, raw_logits).

        Returns: (float, numpy_array) hoặc (None, None) nếu lỗi.
        """
        if self.model is None:
            self.log_callback("[InferenceEngine] ❌ predict() gọi khi model chưa được nạp!")
            return None, None

        try:
            # Chuyển về tensor nếu chưa phải
            if type(x_tensor).__name__ not in ('Tensor', 'MagicMock'):
                x_tensor = torch.tensor(x_tensor, dtype=torch.float32)

            input_shape = tuple(x_tensor.shape)
            self.log_callback(f"[InferenceEngine] 🧠 Đang suy diễn | input_shape={input_shape}")

            x_tensor = x_tensor.to(self.device)

            with torch.no_grad():
                output = self.model(x_tensor)
                probs = torch.softmax(output.data, dim=1).squeeze()

                if probs.dim() == 0:
                    probs = probs.unsqueeze(0)

                prob_down = probs[0].item()
                prob_up   = probs[1].item()
                raw_logits = output.cpu().numpy()[0]

            self.log_callback(
                f"[InferenceEngine] ✅ Kết quả | prob_down={prob_down:.4f} prob_up={prob_up:.4f} "
                f"logits={[f'{v:.3f}' for v in raw_logits]}"
            )
            return prob_up, raw_logits

        except Exception as e:
            self.log_callback(f"[InferenceEngine] ❌ Lỗi suy diễn Pytorch: {e}")
            self.log_callback(traceback.format_exc())
            return None, None
