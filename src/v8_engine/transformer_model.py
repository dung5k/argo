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
    Sử dụng Concatenated Self-Attention để thay thế Cross-Attention phức tạp.
    """
    def __init__(self, config: dict):
        super(V8TransformerModel, self).__init__()
        params = config.get('transformer_params', {})
        self.d_model = params.get('embedding_dim', 64)
        self.nhead = params.get('num_heads', 4)
        self.num_layers = params.get('num_layers', 3)
        self.dropout = params.get('dropout', 0.1)
        
        vocab_params = config.get('nlp_tokenizer_params', {})
        self.vocab_size = len(vocab_params.get('vocabulary', [])) + 1 # +1 for PAD
        
        # Share embedding across all timeframes
        self.embedding = nn.Embedding(self.vocab_size, self.d_model)
        # Timeframe Embedding to avoid Positional Collision (0: H4, 1: H1, 2: M15)
        self.tf_embedding = nn.Embedding(3, self.d_model)
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
        
        # Layer gộp Token Feature và Continuous Feature
        self.fc_combine = nn.Sequential(
            nn.Linear(self.d_model + self.cont_dim, self.d_model),
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
        cont_x: [batch, 9]
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
        
        # Nối lại: [batch, 3 * seq_len, d_model]
        # H4 đứng đầu để cung cấp context dài hạn nhất, H1 ở giữa, M15 ở cuối
        emb_concat = torch.cat([emb_h4, emb_h1, emb_m15], dim=1)
        
        # Đưa toàn bộ chuỗi concat qua Positional Encoding một lần duy nhất
        emb_concat = self.pos_encoder(emb_concat)
        
        out = self.transformer_encoder(emb_concat)
        
        # Lấy Output của token M15 cuối cùng (Nằm ở vị trí cuối cùng của chuỗi concat)
        last_token_out = out[:, -1, :] 
        
        # Nối với Continuous Features (Order Block)
        combined = torch.cat([last_token_out, cont_x], dim=1)
        features = self.fc_combine(combined)
        
        # Ép qua LayerNorm
        features = self.layer_norm(features)
        
        logits = self.fc_out(features)
        return logits
