import torch
import torch.nn as nn
import numpy as np

class PositionalEncoding(nn.Module):
    """Mã hóa vị trí Sinusoidal để Transformer hiểu thứ tự nến"""
    def __init__(self, d_model, max_len=200, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

class TransformerModel(nn.Module):
    def __init__(self, num_features, d_model=64, nhead=4, num_layers=2, 
                 dropout_rate=0.2, num_xau_features=None):
        super(TransformerModel, self).__init__()
        
        self.num_xau_features = num_xau_features if num_xau_features else max(1, num_features // 3)
        self.num_macro_features = num_features - self.num_xau_features
        
        # Đảm bảo d_model chia hết cho nhead
        if d_model % nhead != 0:
            d_model = (d_model // nhead) * nhead
        self.d_model = d_model
        
        # === LUỒNG 1: XAU TRANSFORMER STREAM ===
        self.xau_input_proj = nn.Linear(self.num_xau_features, d_model)
        self.xau_pos_enc = PositionalEncoding(d_model, dropout=dropout_rate)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, 
            dim_feedforward=d_model * 4,
            dropout=dropout_rate, batch_first=True, norm_first=True  # Pre-LN: ổn định hơn
        )
        try:
            self.xau_transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers, enable_nested_tensor=False)
        except TypeError:
            self.xau_transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # === LUỒNG 2: MACRO FC EMBEDDER ===
        macro_hidden = max(16, d_model // 4)
        self.macro_fc = nn.Sequential(
            nn.Linear(self.num_macro_features, d_model // 2),
            nn.GELU(),
            nn.LayerNorm(d_model // 2),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model // 2, macro_hidden),
            nn.GELU()
        )
        
        # === MERGE + DECISION HEAD ===
        merged_size = d_model + macro_hidden
        self.decision_head = nn.Sequential(
            nn.LayerNorm(merged_size),
            nn.Linear(merged_size, d_model),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model, 2)
        )

    def forward(self, x):
        # [SAFETY SHIELD] Kiểm tra an toàn Shape
        actual_features = x.size(2)
        expected_features = self.num_xau_features + self.num_macro_features
        if actual_features != expected_features:
            raise RuntimeError(f"[FATAL] Tensor Input có {actual_features} features, nhưng Model được cấu hình đón {expected_features} features (XAU: {self.num_xau_features}, Macro: {self.num_macro_features}). CHẶN SẬP HỆ THỐNG!")
            
        xau_feats = x[:, :, :self.num_xau_features]
        macro_feats = x[:, -1, self.num_xau_features:]
        
        # XAU TRANSFORMER: Project → PositionalEncode → Self-Attention → Lấy token cuối
        xau_t = self.xau_input_proj(xau_feats)
        xau_t = self.xau_pos_enc(xau_t)
        xau_t = self.xau_transformer(xau_t)
        xau_signal = xau_t[:, -1, :]  # Token cuối = tín hiệu HIỆN TẠI
        
        # MACRO EMBEDDER
        macro_signal = self.macro_fc(macro_feats)
        
        # MERGE
        merged = torch.cat([xau_signal, macro_signal], dim=1)
        return self.decision_head(merged)
