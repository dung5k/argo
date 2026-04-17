import torch
import torch.optim as optim

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
