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


# =====================================================================
# [MỚI] Attention Pooling — Học trọng số thời gian thay vì Mean cào bằng
# =====================================================================
class AttentionPooling(nn.Module):
    """
    Learnable Attention Pooling: Thay thế Global Average Pooling.
    Dùng 1 query vector (learnable) để attend vào toàn bộ memory sequence,
    cho phép model tập trung vào những bước thời gian quan trọng nhất
    (ví dụ: nến breakout, nến volume spike) thay vì cào bằng 60 nến.
    
    Input:  [Batch, Seq_len, d_model]
    Output: [Batch, d_model]
    """
    def __init__(self, d_model):
        super().__init__()
        # Query vector khởi tạo ngẫu nhiên, sẽ được học qua backprop
        self.query = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)
        self.scale = math.sqrt(d_model)
    
    def forward(self, memory):
        # memory: [B, S, D]
        # query:  [1, 1, D] → broadcast sang [B, 1, D]
        query = self.query.expand(memory.size(0), -1, -1)
        
        # Attention scores: [B, 1, S]
        attn_scores = torch.bmm(query, memory.transpose(1, 2)) / self.scale
        attn_weights = torch.softmax(attn_scores, dim=-1)
        
        # Weighted sum: [B, 1, D] → [B, D]
        pooled = torch.bmm(attn_weights, memory).squeeze(1)
        return pooled


# =====================================================================
# [MỚI] Stochastic Depth Transformer Encoder — LayerDrop Regularization
# =====================================================================
class StochasticDepthEncoder(nn.Module):
    """
    Transformer Encoder với Stochastic Depth (LayerDrop).
    Trong lúc training, mỗi layer có xác suất `drop_rate` bị skip hoàn toàn.
    Tương đương với việc huấn luyện một ensemble của sub-networks cùng lúc.
    
    Hiệu quả:
    - Chống overfitting mạnh hơn dropout thông thường
    - Đặc biệt tốt cho data ít (Asian session)
    - Không thay đổi gì khi inference (tất cả layer đều chạy)
    """
    def __init__(self, encoder_layer, num_layers, drop_rate=0.1):
        super().__init__()
        self.layers = nn.ModuleList(
            [self._clone_layer(encoder_layer) for _ in range(num_layers)]
        )
        self.drop_rate = drop_rate
        self.num_layers = num_layers
    
    @staticmethod
    def _clone_layer(layer):
        """Deep clone một TransformerEncoderLayer"""
        import copy
        return copy.deepcopy(layer)
    
    def forward(self, src, mask=None, src_key_padding_mask=None):
        output = src
        for i, layer in enumerate(self.layers):
            if self.training and self.drop_rate > 0:
                # Tính xác suất drop tăng dần theo depth (layer sâu dễ bị skip hơn)
                layer_drop_prob = self.drop_rate * (i + 1) / self.num_layers
                if torch.rand(1).item() < layer_drop_prob:
                    continue  # Skip layer này
            output = layer(output, src_mask=mask, src_key_padding_mask=src_key_padding_mask)
        return output


class AAMT_Encoder(nn.Module):
    """
    Module 1: Lõi Transformer Encoder.
    Nhiệm vụ: Nén ma trận [Batch, 60, N_features] thành một Latent Vector tóm tắt hình thái thị trường.
    
    [V2] Hỗ trợ các tùy chọn kiến trúc mới:
    - pooling: 'mean' (mặc định) hoặc 'attention' (Learnable Attention Pooling)
    - layer_drop: 0.0 (tắt) đến 0.3 (Stochastic Depth cho regularization mạnh)
    """
    def __init__(self, input_dim=15, d_model=128, nhead=8, num_layers=4, dropout=0.25, d_ff=512,
                 pooling='mean', layer_drop=0.0):
        super().__init__()
        self.d_model = d_model
        self.pooling_type = pooling
        
        # Linear layer map từ số feature thực tế (vd: 15) lên d_model (vd: 128) để nhồi vào Transformer
        self.input_projection = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead, 
            dim_feedforward=d_ff, 
            dropout=dropout, 
            activation='gelu',
            batch_first=True # Để tensor đầu vào là [Batch, Seq, Features]
        )
        
        # [MỚI] Chọn encoder có/không Stochastic Depth
        if layer_drop > 0.0:
            self.transformer_encoder = StochasticDepthEncoder(encoder_layer, num_layers, drop_rate=layer_drop)
        else:
            self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # [MỚI] Chọn pooling strategy
        if pooling == 'attention':
            self.pooler = AttentionPooling(d_model)
        else:
            self.pooler = None  # Sẽ dùng torch.mean
        
    def forward(self, x):
        # x: [Batch, Seq_len, Features]
        
        # Bước 1: Phóng to Feature Space
        x = self.input_projection(x) * math.sqrt(self.d_model)
        
        # Bước 2: Bơm vị trí thời gian
        x = self.pos_encoder(x)
        
        # Bước 3: Cho học tương tác qua Attention
        memory = self.transformer_encoder(x)
        
        # Bước 4: Nén [Batch, 60, 128] -> [Batch, 128]
        if self.pooler is not None:
            latent_vector = self.pooler(memory)
        else:
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


# =====================================================================
# [MỚI] Residual MLP Classification Head — Gradient flow mạnh hơn
# =====================================================================
class AAMT_ResidualClassificationHead(nn.Module):
    """
    Module 3B: Cỗ máy ra quyết định CAO CẤP (Residual MLP).
    
    So với AAMT_ClassificationHead (2-layer linear):
    - 3-layer MLP với skip connection (residual)
    - Gradient flow tốt hơn khi d_model lớn
    - Tự động điều chỉnh dimension qua bottleneck
    
    Nhiệm vụ: Softmax dự đoán 3 trạng thái [SELL, BUY, SIDEWAY].
    """
    def __init__(self, d_model=128, num_classes=3, dropout=0.25):
        super().__init__()
        bottleneck = max(32, d_model // 2)
        
        # Nhánh chính: d_model → bottleneck → bottleneck → num_classes
        self.fc1 = nn.Linear(d_model, bottleneck)
        self.bn1 = nn.BatchNorm1d(bottleneck)
        self.fc2 = nn.Linear(bottleneck, bottleneck)
        self.bn2 = nn.BatchNorm1d(bottleneck)
        self.fc_out = nn.Linear(bottleneck, num_classes)
        
        # Skip connection: d_model → bottleneck (project nếu dimension khác)
        self.skip_proj = nn.Linear(d_model, bottleneck) if d_model != bottleneck else nn.Identity()
        
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, latent_vector):
        # latent_vector: [Batch, d_model]
        skip = self.skip_proj(latent_vector)
        
        x = self.fc1(latent_vector)
        x = self.bn1(x)
        x = self.act(x)
        x = self.dropout(x)
        
        x = self.fc2(x)
        x = self.bn2(x)
        x = x + skip  # Residual connection
        x = self.act(x)
        x = self.dropout(x)
        
        logits = self.fc_out(x)
        return logits


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
    
    [V2] Tùy chọn kiến trúc cao cấp (backward-compatible):
    - pooling:    'mean' (mặc định) | 'attention' (Learnable Attention Pooling)
    - cls_head:   'simple' (mặc định) | 'residual' (Residual MLP 3-layer)
    - layer_drop: 0.0 (mặc định, tắt) | 0.0-0.3 (Stochastic Depth)
    """
    def __init__(self, input_dim=15, seq_len=60, d_model=128, nhead=8, num_layers=4, dropout=0.25, num_classes=3, d_ff=512,
                 pooling='mean', cls_head='simple', layer_drop=0.0):
        super().__init__()
        
        self.encoder = AAMT_Encoder(input_dim, d_model, nhead, num_layers, dropout, d_ff,
                                     pooling=pooling, layer_drop=layer_drop)
        self.reconstructor = AAMT_ReconstructionHead(d_model, input_dim, seq_len)
        
        # [MỚI] Chọn Classification Head
        if cls_head == 'residual':
            self.classifier = AAMT_ResidualClassificationHead(d_model, num_classes, dropout)
        else:
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
