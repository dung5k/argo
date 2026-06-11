import torch
import torch.nn as nn
import math

class V8PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(V8PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))

    def forward(self, x):
        # x shape: [batch, seq_len, d_model]
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

class V8TransformerModel(nn.Module):
    """
    Mô hình NLP Transformer Multi-Timeframe ứng dụng cho Trading.
    V8.2: Sửa kiến trúc theo kết quả Audit đồng thuận:
      - PE riêng cho từng Timeframe (không còn PE chung chồng chéo)
      - Trích xuất token cuối cả 3 TF (H4, H1, M15) thay vì chỉ M15
    """
    def __init__(self, config: dict):
        super(V8TransformerModel, self).__init__()
        params = config.get('transformer_params', {})
        self.d_model = params.get('embedding_dim', 64)
        self.nhead = params.get('num_heads', 4)
        self.num_layers = params.get('num_layers', 3)
        self.dropout = params.get('dropout', 0.1)
        self.seq_len = config.get('nlp_tokenizer_params', {}).get('max_sequence_length', 50)
        
        vocab_params = config.get('nlp_tokenizer_params', {})
        self.vocab_size = len(vocab_params.get('vocabulary', [])) + 1 # +1 for PAD
        
        # Share embedding across all timeframes
        self.embedding = nn.Embedding(self.vocab_size, self.d_model)
        # Timeframe Embedding to avoid Positional Collision (0: H4, 1: H1, 2: M15)
        self.tf_embedding = nn.Embedding(3, self.d_model)
        
        # [FIX 1.1] PE riêng cho từng Timeframe — tránh gán vị trí tuyệt đối chồng chéo
        # Mỗi TF có PE độc lập, phản ánh tính chất song song (parallel) của giá
        self.pos_encoder = V8PositionalEncoding(self.d_model, self.dropout, max_len=5000)
        
        encoder_layers = nn.TransformerEncoderLayer(
            d_model=self.d_model, 
            nhead=self.nhead, 
            dropout=self.dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, self.num_layers)
        
        self.num_classes = params.get('num_classes', 5)
        
        # Continuous features shape: 34 (9 OB + 4 Time + 7 indicators * 3 TFs = 34)
        self.cont_dim = 34
        
        # [FIX 2.1] fc_combine nhận token cuối cả 3 TF: 3 * d_model + cont_dim
        # Trước đây chỉ dùng 1 * d_model (chỉ M15) → bottleneck thông tin
        self.fc_combine = nn.Sequential(
            nn.Linear(3 * self.d_model + self.cont_dim, self.d_model * 2),
            nn.GELU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.d_model * 2, self.d_model),
            nn.GELU(),
            nn.Dropout(self.dropout)
        )
        
        # Thêm LayerNorm ép trung bình (mean) = 0 để chống lách luật tăng Bias toàn cục
        self.layer_norm = nn.LayerNorm(self.d_model)
        
        # Tắt Bias ở lớp Output để triệt tiêu năng lực lười biếng của AI
        self.fc_out = nn.Linear(self.d_model, self.num_classes, bias=False) 
        
    def forward(self, x_m15, x_h1, x_h4, cont_x):
        """
        x_m15, x_h1, x_h4: [batch, seq_len]
        cont_x: [batch, 34]
        """
        # Lấy Timeframe ID cho từng frame: 0=H4, 1=H1, 2=M15
        device = x_m15.device
        tf_h4 = torch.tensor(0, device=device)
        tf_h1 = torch.tensor(1, device=device)
        tf_m15 = torch.tensor(2, device=device)
        
        # Embed từng TF độc lập và cộng với Timeframe Embedding
        emb_h4 = self.embedding(x_h4) * math.sqrt(self.d_model) + self.tf_embedding(tf_h4)
        emb_h1 = self.embedding(x_h1) * math.sqrt(self.d_model) + self.tf_embedding(tf_h1)
        emb_m15 = self.embedding(x_m15) * math.sqrt(self.d_model) + self.tf_embedding(tf_m15)
        
        # [FIX 1.1] PE riêng cho từng TF trước khi nối
        # Mỗi TF có chuỗi vị trí bắt đầu từ 0 → seq_len-1
        # Phản ánh đúng: token cuối của H4 và token cuối của M15 đều ở "hiện tại" (t=0)
        emb_h4 = self.pos_encoder(emb_h4)
        emb_h1 = self.pos_encoder(emb_h1)
        emb_m15 = self.pos_encoder(emb_m15)
        
        # Nối lại: [batch, 3 * seq_len, d_model]
        # H4 đứng đầu để cung cấp context dài hạn nhất, H1 ở giữa, M15 ở cuối
        emb_concat = torch.cat([emb_h4, emb_h1, emb_m15], dim=1)
        
        out = self.transformer_encoder(emb_concat)
        
        # [FIX 2.1] Trích xuất token cuối cùng của CẢ 3 khung thời gian
        # Thay vì chỉ lấy token cuối M15, lấy đại diện từ cả H4 và H1
        # Tận dụng triệt để tính toán Attention đã chạy cho toàn bộ chuỗi
        seq = self.seq_len
        h4_last = out[:, seq - 1, :]       # Token cuối H4 (vị trí seq_len - 1)
        h1_last = out[:, 2 * seq - 1, :]   # Token cuối H1 (vị trí 2*seq_len - 1)
        m15_last = out[:, -1, :]            # Token cuối M15 (vị trí cuối cùng)
        
        # Concatenate 3 token đại diện: [batch, 3 * d_model]
        mtf_features = torch.cat([h4_last, h1_last, m15_last], dim=1)
        
        # Nối với Continuous Features (Order Block + Indicators + Time)
        combined = torch.cat([mtf_features, cont_x], dim=1)
        features = self.fc_combine(combined)
        
        # Ép qua LayerNorm
        features = self.layer_norm(features)
        
        logits = self.fc_out(features)
        return logits
