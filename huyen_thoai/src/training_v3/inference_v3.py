import torch
import torch.nn.functional as F

class InferenceV3:
    """
    Thực thi Live Trading với cơ chế bẫy lọc nhiễu MSE 2 tầng.
    """
    def __init__(self, model, mse_threshold, prob_threshold, device='cpu'):
        self.model = model
        self.mse_threshold = mse_threshold
        self.prob_threshold = prob_threshold
        self.device = device
        
        self.model.to(device)
        self.model.eval()

    def predict(self, window_tensor):
        """
        Dự đoán trạng thái từ ma trận 60 nến (shape: [1, 60, 15])
        Trả về: (Action, MSE, Probabilities dict)
        """
        # Đảm bảo tensor có batch dimension: [1, 60, 15]
        if window_tensor.dim() == 2:
            window_tensor = window_tensor.unsqueeze(0)
            
        window_tensor = window_tensor.to(self.device).float()
        
        with torch.no_grad():
            reconstructed, logits, _ = self.model(window_tensor)
            
            # --- MÀNG LỌC 1: KIỂM ĐỊNH RÁC BẰNG MSE ---
            # Tính MSE (Mean Squared Error) giữa input và hình vẽ lại của Reconstruct Head
            mse_loss = F.mse_loss(reconstructed, window_tensor).item()
            
            # Lấy xác suất từ 3 class [Sell=0, Buy=1, Sideway=2] bằng Softmax
            probs = F.softmax(logits, dim=-1).cpu().numpy()[0]
            
            out_dict = {
                "sell": float(probs[0]),
                "buy": float(probs[1]),
                "sideway": float(probs[2])
            }
            
            if mse_loss > self.mse_threshold:
                # Dữ liệu bất tuân quy luật, AI không thể giải nén
                return "TÍN_HIỆU_RÁC", mse_loss, out_dict
                
            # --- MÀNG LỌC 2: QUYẾT ĐỊNH THEO XÁC SUẤT ---
            if out_dict["buy"] > self.prob_threshold:
                return "BUY", mse_loss, out_dict
            elif out_dict["sell"] > self.prob_threshold:
                return "SELL", mse_loss, out_dict
            else:
                return "SIDEWAY_YẾU_SINH_LÝ", mse_loss, out_dict
