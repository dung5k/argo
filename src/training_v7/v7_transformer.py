# -*- coding: utf-8 -*-
"""
v7_transformer.py - Cross-Asset Transformer Model (QTS-V7)
Mạng Transformer nhận đầu vào đa biến kết hợp Follower và Leader bị dịch trễ.
"""
import torch
import torch.nn as nn
import numpy as np

class PositionalEncoding(nn.Module):
    """Mã hóa vị trí Sinusoidal để Transformer hiểu thứ tự nến."""
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
        # x shape: [batch_size, seq_len, d_model]
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

class CrossAssetTransformerModel(nn.Module):
    """
    Cross-Asset Transformer Model nhận đầu vào tích hợp đa tài sản (Follower + Lagged Leader).
    Dự đoán 3 nhãn: 0 (HOLD), 1 (BUY), 2 (SELL)
    """
    def __init__(self, num_features, d_model=64, nhead=4, num_layers=3, dropout_rate=0.25):
        super().__init__()
        
        # Đảm bảo d_model chia hết cho nhead
        if d_model % nhead != 0:
            d_model = (d_model // nhead) * nhead
        self.d_model = d_model
        
        # Project đặc trưng đầu vào lên d_model chiều
        self.input_proj = nn.Linear(num_features, d_model)
        self.pos_enc = PositionalEncoding(d_model, dropout=dropout_rate)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout_rate, batch_first=True, norm_first=True
        )
        
        try:
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers, enable_nested_tensor=False)
        except TypeError:
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            
        self.ln = nn.LayerNorm(d_model)
        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model // 2, 3) # Dự đoán 3 nhãn: HOLD (0), BUY (1), SELL (2)
        )

    def forward(self, x):
        # x shape: [batch_size, seq_len, num_features]
        out = self.input_proj(x)
        out = self.pos_enc(out)
        out = self.transformer(out)
        
        # Lấy Global Average Pooling của tất cả các nến thay vì chỉ lấy nến cuối cùng
        # Điều này giúp mô hình tổng hợp thông tin tốt hơn theo góp ý của chuyên gia
        gap_out = torch.mean(out, dim=1)
        gap_out = self.ln(gap_out)
        
        logits = self.fc(gap_out)
        return logits
