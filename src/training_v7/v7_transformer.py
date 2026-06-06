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
    def __init__(self, num_features, d_model=128, nhead=8, num_layers=4, dropout_rate=0.25):
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
        
        # [NEW V6 AUTOENCODER] Nhánh giải nén dữ liệu để chống học vẹt (Reconstruction Loss)
        self.reconstructor = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model * 2, num_features)
        )

    def forward(self, x):
        # x shape: [batch_size, seq_len, num_features]
        out = self.input_proj(x)
        out = self.pos_enc(out)
        out = self.transformer(out)
        
        # Phục hồi dữ liệu đầu vào thông qua Reconstructor
        reconstructed = self.reconstructor(out)
        
        # Thay vì chỉ lấy output của nến cuối cùng (bottleneck), ta dùng Global Average Pooling
        # để lấy trung bình trọng số của toàn bộ 30 nến, giúp Transformer tổng hợp bối cảnh tốt hơn.
        last_out = out.mean(dim=1)
        last_out = self.ln(last_out)
        
        logits = self.fc(last_out)
        return logits, reconstructed

class GLU(nn.Module):
    def __init__(self, d_model):
        super().__init__()
        self.fc1 = nn.Linear(d_model, d_model)
        self.fc2 = nn.Linear(d_model, d_model)

    def forward(self, x):
        return self.fc1(x) * torch.sigmoid(self.fc2(x))

class GatedResidualNetwork(nn.Module):
    def __init__(self, input_size, hidden_size, output_size, dropout_rate=0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.elu1 = nn.ELU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout_rate)
        self.glu = GLU(hidden_size)
        self.out_proj = nn.Linear(hidden_size, output_size)
        self.residual_proj = nn.Linear(input_size, output_size) if input_size != output_size else nn.Identity()
        self.ln = nn.LayerNorm(output_size)

    def forward(self, x):
        res = self.residual_proj(x)
        x = self.fc1(x)
        x = self.elu1(x)
        x = self.fc2(x)
        x = self.dropout(x)
        x = self.glu(x)
        x = self.out_proj(x)
        return self.ln(res + x)

class VariableSelectionNetwork(nn.Module):
    def __init__(self, num_vars, d_model, dropout_rate=0.1):
        super().__init__()
        self.num_vars = num_vars
        self.weight_network = GatedResidualNetwork(num_vars * d_model, d_model, num_vars, dropout_rate)
        self.variable_networks = nn.ModuleList([
            GatedResidualNetwork(d_model, d_model, d_model, dropout_rate) for _ in range(num_vars)
        ])

    def forward(self, x):
        # x: [batch, seq_len, num_vars, d_model]
        batch_size, seq_len, _, _ = x.size()
        
        # Calculate weights
        flat_x = x.view(batch_size, seq_len, -1)
        weights = self.weight_network(flat_x) # [batch, seq_len, num_vars]
        weights = torch.softmax(weights, dim=-1).unsqueeze(-1) # [batch, seq_len, num_vars, 1]
        
        # Process individual variables
        processed_vars = []
        for i in range(self.num_vars):
            var_x = x[:, :, i, :] # [batch, seq_len, d_model]
            processed_vars.append(self.variable_networks[i](var_x))
            
        processed_vars = torch.stack(processed_vars, dim=2) # [batch, seq_len, num_vars, d_model]
        
        # Combine
        combined = (processed_vars * weights).sum(dim=2) # [batch, seq_len, d_model]
        return combined

class TemporalFusionTransformerModel(nn.Module):
    def __init__(self, num_features, d_model=64, nhead=4, num_layers=2, dropout_rate=0.2):
        super().__init__()
        if d_model % nhead != 0:
            d_model = (d_model // nhead) * nhead
        self.d_model = d_model
        self.num_features = num_features
        
        # Map each feature to d_model individually for VSN
        self.feature_proj = nn.Linear(1, d_model)
        
        self.vsn = VariableSelectionNetwork(num_features, d_model, dropout_rate)
        self.pos_enc = PositionalEncoding(d_model, dropout=dropout_rate)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout_rate, batch_first=True, norm_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.ln = nn.LayerNorm(d_model)
        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model // 2, 3) 
        )
        
        # Reconstructor
        self.reconstructor = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model * 2, num_features)
        )

    def forward(self, x):
        # x: [batch_size, seq_len, num_features]
        batch_size, seq_len, _ = x.size()
        
        # Reshape to project each feature individually
        x_expanded = x.unsqueeze(-1) # [batch, seq_len, num_features, 1]
        x_proj = self.feature_proj(x_expanded) # [batch, seq_len, num_features, d_model]
        
        # Pass through Variable Selection Network
        out = self.vsn(x_proj) # [batch, seq_len, d_model]
        
        out = self.pos_enc(out)
        out = self.transformer(out)
        
        reconstructed = self.reconstructor(out)
        
        last_out = out.mean(dim=1)
        last_out = self.ln(last_out)
        
        logits = self.fc(last_out)
        return logits, reconstructed
