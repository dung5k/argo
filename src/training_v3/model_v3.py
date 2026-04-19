import torch
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        # Sửa lỗi shape nếu d_model là số lẻ
        if d_model % 2 != 0:
            pe[:, 1::2] = torch.cos(position * div_term)[:, :-1]
        else:
            pe[:, 1::2] = torch.cos(position * div_term)
            
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        """
        Args:
            x: Tensor, shape [batch_size, seq_len, embedding_dim]
        """
        x = x + self.pe[:, :x.size(1), :]
        return x

class AAMT_Encoder(nn.Module):
    """
    Module 1: Lõi Transformer Encoder.
    Nhiệm vụ: Nén ma trận [Batch, 60, N_features] thành một Latent Vector tóm tắt hình thái thị trường.
    """
    def __init__(self, input_dim=15, d_model=128, nhead=8, num_layers=4, dropout=0.25):
        super().__init__()
        self.d_model = d_model
        
        # Linear layer map từ số feature thực tế (vd: 15) lên d_model (vd: 128) để nhồi vào Transformer
        self.input_projection = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        encoder_layers = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead, 
            dim_feedforward=d_model * 4, 
            dropout=dropout, 
            activation='gelu',
            batch_first=True # Để tensor đầu vào là [Batch, Seq, Features]
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        
    def forward(self, x):
        # x: [Batch, Seq_len, Features]
        
        # Bước 1: Phóng to Feature Space
        x = self.input_projection(x) * math.sqrt(self.d_model)
        
        # Bước 2: Bơm vị trí thời gian
        x = self.pos_encoder(x)
        
        # Bước 3: Cho học tương tác qua Attention
        memory = self.transformer_encoder(x)
        
        # Bước 4: Nén [Batch, 60, 128] -> [Batch, 128] bằng Global Average Pooling
        # Đại diện cho toàn bộ chuỗi 60 nến (chính là Latent Vector)
        latent_vector = torch.mean(memory, dim=1)
        
        return latent_vector, memory

class AAMT_ReconstructionHead(nn.Module):
    """
    Module 2: Bộ giải nén (Autoencoder Decoder) - Hệ thống bẫy rác.
    Nhiệm vụ: Dùng memory (hoặc latent) để vẽ lại y xì ma trận đầu vào [Batch, 60, 15].
    """
    def __init__(self, d_model=128, output_dim=15, seq_len=60):
        super().__init__()
        self.seq_len = seq_len
        self.output_dim = output_dim
        
        # Dùng lại cấu trúc mạng feed-forward để giải mã từ chuỗi Memory sinh ra bởi Encoder
        # Thay vì chỉ dùng latent vector ngắn, ta dùng memory (chứa tính tuần tự) để việc vẽ lại dễ đạt MSE thấp nếu có rules
        self.decoder_net = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(0.25),
            nn.Linear(d_model * 2, output_dim)
        )
        
    def forward(self, memory):
        # memory: [Batch, Seq_len, d_model]
        # output: [Batch, Seq_len, output_dim] -> Giống hệt kích thước Origin Input
        reconstructed = self.decoder_net(memory)
        return reconstructed

class AAMT_ClassificationHead(nn.Module):
    """
    Module 3: Cỗ máy ra quyết định.
    Nhiệm vụ: Softmax dự đoán 3 trạng thái [SELL, BUY, SIDEWAY].
    """
    def __init__(self, d_model=128, num_classes=3):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.BatchNorm1d(64),
            nn.GELU(),
            nn.Dropout(0.25),
            nn.Linear(64, num_classes)
        )
        
    def forward(self, latent_vector):
        # latent_vector: [Batch, d_model]
        logits = self.classifier(latent_vector)
        # Sẽ trả logits raw để lát đưa vào CrossEntropyLoss (tự động tính Softmax)
        return logits

class AAMT_Model(nn.Module):
    """
    Kết Nối Lõi: Khối AAMT Tổng Hợp Đa Nhiệm (Autoencoder-Augmented Multi-Task Transformer).
    """
    def __init__(self, input_dim=15, seq_len=60, d_model=128, nhead=8, num_layers=4, dropout=0.25, num_classes=3):
        super().__init__()
        
        self.encoder = AAMT_Encoder(input_dim, d_model, nhead, num_layers, dropout)
        self.reconstructor = AAMT_ReconstructionHead(d_model, input_dim, seq_len)
        self.classifier = AAMT_ClassificationHead(d_model, num_classes)
        
    def forward(self, x):
        """
        Quá trình chạy của Data:
        Returns: 
           reconstructed (Ma trận vẽ lại để xài MSE Loss)
           logits (Dự báo 3 trạng thái để xài CrossEntropy)
           latent_vector (Mảng nén phục vụ Tracking nếu cần)
        """
        # Bước 1: Nén
        latent_vector, memory = self.encoder(x)
        
        # Bước 2 & 3: Xử lý đa nhiệm song song
        reconstructed = self.reconstructor(memory)
        logits = self.classifier(latent_vector)
        
        return reconstructed, logits, latent_vector
