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
        if d_model % 2 != 0:
            pe[:, 1::2] = torch.cos(position * div_term)[:, :-1]
        else:
            pe[:, 1::2] = torch.cos(position * div_term)
            
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return x

class AttentionPooling(nn.Module):
    def __init__(self, d_model):
        super().__init__()
        self.query = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)
        self.scale = math.sqrt(d_model)
    
    def forward(self, memory):
        query = self.query.expand(memory.size(0), -1, -1)
        attn_scores = torch.bmm(query, memory.transpose(1, 2)) / self.scale
        attn_weights = torch.softmax(attn_scores, dim=-1)
        pooled = torch.bmm(attn_weights, memory).squeeze(1)
        return pooled

class StochasticDepthEncoder(nn.Module):
    def __init__(self, encoder_layer, num_layers, drop_rate=0.1):
        super().__init__()
        self.layers = nn.ModuleList(
            [self._clone_layer(encoder_layer) for _ in range(num_layers)]
        )
        self.drop_rate = drop_rate
        self.num_layers = num_layers
    
    @staticmethod
    def _clone_layer(layer):
        import copy
        return copy.deepcopy(layer)
    
    def forward(self, src, mask=None, src_key_padding_mask=None):
        output = src
        for i, layer in enumerate(self.layers):
            if self.training and self.drop_rate > 0:
                layer_drop_prob = self.drop_rate * (i + 1) / self.num_layers
                if torch.rand(1).item() < layer_drop_prob:
                    continue
            output = layer(output, src_mask=mask, src_key_padding_mask=src_key_padding_mask)
        return output

class AAMT_Encoder(nn.Module):
    def __init__(self, input_dim=15, d_model=128, nhead=8, num_layers=4, dropout=0.25, d_ff=512,
                 pooling='mean', layer_drop=0.0):
        super().__init__()
        self.d_model = d_model
        self.pooling_type = pooling
        
        self.input_projection = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_ff, dropout=dropout, activation='gelu', batch_first=True
        )
        
        if layer_drop > 0.0:
            self.transformer_encoder = StochasticDepthEncoder(encoder_layer, num_layers, drop_rate=layer_drop)
        else:
            self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        
        if pooling == 'attention':
            self.pooler = AttentionPooling(d_model)
        else:
            self.pooler = None
        
    def forward(self, x):
        x = self.input_projection(x) * math.sqrt(self.d_model)
        x = self.pos_encoder(x)
        memory = self.transformer_encoder(x)
        
        if self.pooler is not None:
            latent_vector = self.pooler(memory)
        else:
            latent_vector = torch.mean(memory, dim=1)
        
        return latent_vector, memory

class AAMT_ReconstructionHead(nn.Module):
    def __init__(self, d_model=128, output_dim=15, seq_len=60):
        super().__init__()
        self.seq_len = seq_len
        self.output_dim = output_dim
        
        self.decoder_net = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(0.25),
            nn.Linear(d_model * 2, output_dim)
        )
        
    def forward(self, memory):
        reconstructed = self.decoder_net(memory)
        return reconstructed

class AAMT_ResidualClassificationHead(nn.Module):
    def __init__(self, d_model=128, num_classes=3, dropout=0.25):
        super().__init__()
        bottleneck = max(32, d_model // 2)
        
        self.fc1 = nn.Linear(d_model, bottleneck)
        self.ln1 = nn.LayerNorm(bottleneck)  # LayerNorm: an toàn với batch_size=1 khi inference
        self.fc2 = nn.Linear(bottleneck, bottleneck)
        self.ln2 = nn.LayerNorm(bottleneck)  # LayerNorm: an toàn với batch_size=1 khi inference
        self.fc_out = nn.Linear(bottleneck, num_classes)
        
        self.skip_proj = nn.Linear(d_model, bottleneck) if d_model != bottleneck else nn.Identity()
        
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, latent_vector):
        skip = self.skip_proj(latent_vector)
        
        x = self.fc1(latent_vector)
        x = self.ln1(x)
        x = self.act(x)
        x = self.dropout(x)
        
        x = self.fc2(x)
        x = self.ln2(x)
        x = x + skip
        x = self.act(x)
        x = self.dropout(x)
        
        logits = self.fc_out(x)
        return logits

class AAMT_ClassificationHead(nn.Module):
    def __init__(self, d_model=128, num_classes=3):
        super().__init__()
        # LayerNorm thay thế BatchNorm1d: hoạt động đúng với batch_size=1 khi live inference
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(0.25),
            nn.Linear(64, num_classes)
        )
        
    def forward(self, latent_vector):
        logits = self.classifier(latent_vector)
        return logits

# =====================================================================
# [MỚI] V6 MULTI-TIMEFRAME FUSION MODEL (MTF)
# =====================================================================
class AAMT_MTF_Model(nn.Module):
    """
    Kết Nối Lõi V6: Khối AAMT Đa Khung Thời Gian (Multi-Timeframe Fusion Transformer).
    Cho phép nhận song song N tensor đầu vào ứng với N khung thời gian (ví dụ: M1 và H1).
    """
    def __init__(self, input_dims=[43, 43], seq_lens=[60, 16], d_model=128, nhead=8, num_layers=4, dropout=0.25, num_classes=3, d_ff=512,
                 pooling='mean', cls_head='simple', layer_drop=0.0):
        super().__init__()
        
        # 1. Tạo nhiều Encoders riêng biệt cho từng khung thời gian
        self.encoders = nn.ModuleList([
            AAMT_Encoder(input_dims[i], d_model, nhead, num_layers, dropout, d_ff, pooling=pooling, layer_drop=layer_drop)
            for i in range(len(input_dims))
        ])
        
        # 2. Khối Reconstructor cho từng khung (dùng cho AutoEncoder Loss)
        self.reconstructors = nn.ModuleList([
            AAMT_ReconstructionHead(d_model, input_dims[i], seq_lens[i])
            for i in range(len(input_dims))
        ])
        
        # 3. Nối các Latent Vectors lại (Concat) nên input_dim của classifier = d_model * N
        fusion_dim = d_model * len(input_dims)
        
        if cls_head == 'residual':
            self.classifier = AAMT_ResidualClassificationHead(fusion_dim, num_classes, dropout)
        else:
            self.classifier = AAMT_ClassificationHead(fusion_dim, num_classes)
            
    def forward(self, xs):
        """
        xs: list các tensor đầu vào [x_tf1, x_tf2, ...]
        Returns:
           reconstructeds (list ma trận vẽ lại để xài MSE Loss riêng cho từng TF)
           logits (Dự báo 3 trạng thái cuối cùng)
           latent_fusion (Mảng nén tổng hợp)
        """
        if not isinstance(xs, list) and not isinstance(xs, tuple):
            # Tương thích ngược: Nếu truyền 1 tensor, biến thành list
            xs = [xs]
            
        latents = []
        memories = []
        
        for i, x in enumerate(xs):
            latent, memory = self.encoders[i](x)
            latents.append(latent)
            memories.append(memory)
            
        # Fusion: Nối tất cả các latent vectors lại thành 1 siêu vector chứa ngữ cảnh Đa Khung
        latent_fusion = torch.cat(latents, dim=-1)
        
        # Đưa siêu vector vào Classifier để quyết định
        logits = self.classifier(latent_fusion)
        
        # Decode từng memory thành hình dạng ban đầu
        reconstructeds = []
        for i, memory in enumerate(memories):
            reconstructeds.append(self.reconstructors[i](memory))
            
        return reconstructeds, logits, latent_fusion
