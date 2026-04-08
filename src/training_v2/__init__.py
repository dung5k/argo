"""
Training V2 - Cải tiến toán học theo đề xuất Probability Theory
=================================================================
5 nâng cấp chính so với training_v1 (src/core/train_unified.py):

1. Soft Labels   : y = sigmoid(k * log_return_T+5) thay vì nhị phân cứng
2. Scaler        : QuantileTransformer thay StandardScaler (kháng Fat-tails)
3. Loss Function : FocalLoss với α/γ động, hỗ trợ soft labels
4. Phoenix Noise : Magnitude-aware Δw ~ N(0, (α·||w||)²) thay Gaussian đồng nhất
5. Evaluation    : Expected Value (EV = WR×AvgWin - LR×AvgLoss) thay Win Rate thuần túy
"""

__version__ = "2.0.0"
