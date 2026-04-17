import os
import sys
import json
import argparse
import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from huggingface_hub import hf_hub_download, HfApi

# Import components
try:
    from model_v3 import AAMT_Model
    from loss_v3 import AAMT_JointLoss
except ImportError:
    from src.training_v3.model_v3 import AAMT_Model
    from src.training_v3.loss_v3 import AAMT_JointLoss

def train_warmup_phase(model, train_loader, criterion, optimizer, device, epochs=5):
    """
    Giai đoạn 1: Dạy AI cách nhìn biểu đồ (Tách nhiễu) bằng cách chỉ bật Reconstruction Loss
    """
    model.train()
    model.to(device)
    
    # Ép trọng số Joint Loss: TẮT hoàn toàn nhánh Dự đoán, DỒN 100% lực cho nhánh Giải nén
    criterion.set_lambdas(lambda_recon=1.0, lambda_class=0.0)
    
    print(f"--- 🚀 BẮT ĐẦU WARM-UP AUTOENCODER ({epochs} Epochs) ---")
    for epoch in range(epochs):
        total_recon_loss = 0.0
        
        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            reconstructed, logits, _ = model(inputs)
            
            loss, l_recon, l_class = criterion(reconstructed, inputs, logits, targets)
            
            loss.backward()
            optimizer.step()
            
            total_recon_loss += l_recon.item()
            
        avg_loss = total_recon_loss / len(train_loader)
        print(f"[Warm-up] Epoch {epoch+1}/{epochs} | Recon_MSE_Loss: {avg_loss:.6f}")
        
    return model

def train_finetuning_phase(model, train_loader, criterion, optimizer, device, epochs=10):
    """
    Giai đoạn 2: Dạy AI ra quyết định Buy/Sell dựa trên nền tảng hiểu biết biểu đồ đã có.
    """
    model.train()
    model.to(device)
    
    # BẬT LẠI nhánh phân loại (lambda_class = 1.0) để đào tạo hàm tổng (Joint)
    criterion.set_lambdas(lambda_recon=1.0, lambda_class=1.0)
    
    print(f"--- 🚀 BẮT ĐẦU FINE-TUNING ĐA NHIỆM ({epochs} Epochs) ---")
    for epoch in range(epochs):
        total_loss_val = 0.0
        total_recon = 0.0
        total_class = 0.0
        
        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            reconstructed, logits, _ = model(inputs)
            
            loss, l_recon, l_class = criterion(reconstructed, inputs, logits, targets)
            
            loss.backward()
            optimizer.step()
            
            total_loss_val += loss.item()
            total_recon += l_recon.item()
            total_class += l_class.item()
            
        avg_loss = total_loss_val / len(train_loader)
        avg_recon = total_recon / len(train_loader)
        avg_class = total_class / len(train_loader)
        
        print(f"[Fine-tune] Epoch {epoch+1}/{epochs} | Total: {avg_loss:.6f} (MSE:{avg_recon:.4f} | CE:{avg_class:.4f})")
        
    return model

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", help="Path to config file")
    args = parser.parse_args()
    
    config_path = args.config if args.config else "data/bot_config_xau_ny_v3.json"
    print(f"Loading config from: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    cfg_id = config.get('CONFIG_ID', 'V3_UNKNOWN')
    dataset_repo = config.get("HF_CLOUD", {}).get("DATASET_REPO")
    train_cfg = config.get("TRAINING", {})
    
    epochs_warmup = train_cfg.get("EPOCHS_PHASE_1", 10)
    epochs_finetune = train_cfg.get("EPOCHS_PHASE_2", 15)
    batch_size = train_cfg.get("BATCH_SIZE", 64)
    lr = train_cfg.get("LEARNING_RATE", 1e-4)
    
    hf_token = os.environ.get("HF_TOKEN", "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")
    
    print(f"🚀 BẮT ĐẦU QUY TRÌNH TRAINING V3 CHO CẤU HÌNH: {cfg_id}")
    
    # 1. Kéo Dataset (Features V3, 37 Cột) từ mây về
    print("☁️ Đang tải Dataset Tensor từ HuggingFace HUB...")
    x_path = hf_hub_download(repo_id=dataset_repo, filename=f"X_tensor_{cfg_id}.npy", repo_type="dataset", token=hf_token)
    y_path = hf_hub_download(repo_id=dataset_repo, filename=f"Y_tensor_{cfg_id}.npy", repo_type="dataset", token=hf_token)
    
    X = np.load(x_path)
    Y = np.load(y_path)
    
    print(f"✅ Tải thành công! Kích thước X: {X.shape}, Y: {Y.shape}")
    
    X_tensor = torch.tensor(X, dtype=torch.float32)
    Y_tensor = torch.tensor(Y, dtype=torch.long)
    
    dataset = TensorDataset(X_tensor, Y_tensor)
    train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"💻 Đang Train trên nền tảng: {device}")
    
    num_features = X.shape[2]
    window_size = X.shape[1]
    
    # 2. Sinh mạng neural AAMTV3
    model = AAMT_Model(num_features=num_features, window_size=window_size)
    criterion = AAMT_JointLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    
    print(f"🧠 KHỞI TẠO SIÊU MẠNG AAMTV3 (Features: {num_features}, Window: {window_size})")
    
    # 3. Chạy 2 phase
    model = train_warmup_phase(model, train_loader, criterion, optimizer, device, epochs=epochs_warmup)
    model = train_finetuning_phase(model, train_loader, criterion, optimizer, device, epochs=epochs_finetune)
    
    # 4. Xuất mẻ model và Push ngược về HuggingFace
    out_dir = "models_v3"
    os.makedirs(out_dir, exist_ok=True)
    
    model_export_path = os.path.join(out_dir, f"aamt_v3_{cfg_id}_final.pth")
    torch.save(model.state_dict(), model_export_path)
    print(f"💾 Đã lưu trọng số phục vụ Trade tại: {model_export_path}")
    
    api = HfApi(token=hf_token)
    model_repo = config.get("HF_CLOUD", {}).get("MODEL_REPO", "dung5k/aamt_v3_xau_ny_weights")
    api.create_repo(repo_id=model_repo, exist_ok=True, private=True)
    
    print(f"☁️ Đang Upload Model siêu cấp lên HuggingFace -> {model_repo} ...")
    api.upload_file(
        path_or_fileobj=model_export_path,
        path_in_repo=f"aamt_v3_{cfg_id}_final.pth",
        repo_id=model_repo,
        commit_message=f"Upload Chiến Thần V3 (Train complete cho {cfg_id})"
    )
    print("✅✅✅ HOÀN TẤT TOÀN BỘ QUY TRÌNH TRAINING V3. HỆ THỐNG GIAO DỊCH SẴN SÀNG! ✅✅✅")

if __name__ == "__main__":
    main()
