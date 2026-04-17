import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add project root to sys path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3, LabelingV3

@pytest.fixture
def dummy_data():
    """Tạo 100 cây nến giả với xu hướng tăng nhẹ"""
    dates = pd.date_range(start="2026-04-17 00:00:00", periods=100, freq='1min', tz='UTC')
    
    # Tạo giá giả lập (XAUUSDm) dao động quanh 2300, random walk positive
    np.random.seed(42)
    closes = 2300.0 + np.cumsum(np.random.normal(0.05, 0.5, 100))
    opens = closes - np.random.normal(0, 0.2, 100)
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0, 0.3, 100))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0, 0.3, 100))
    
    df = pd.DataFrame({
        'xauusdm_open': opens,
        'xauusdm_high': highs,
        'xauusdm_low': lows,
        'xauusdm_close': closes
    }, index=dates)
    
    return df

def test_price_action_features(dummy_data):
    fe = FeatureEngineeringV3(target_prefix="XAUUSDm")
    
    features = fe.process_features(dummy_data)
    
    # KIỂM TRA 1: Tổng số lượng features đầu ra là 15 (như list đã định)
    # Log Returns (4) + Wicks (2) + Volatility (2) + Momentum (2) + Time (5) = 15
    assert len(features.columns) == 15, "Phải có đúng xấp xỉ 15 features"
    
    # KIỂM TRA 2: Không có NaN trong mảng
    assert features.isna().sum().sum() == 0, "Dữ liệu xuất ra chứa điểm khuyết (NaN)"
    
    # KIỂM TRA 3: Log Returns có bị inf (vô cực) do chia cho 0 không?
    assert not np.isinf(features['log_return_close']).any(), "Log Return chứa vô cực"
    
def test_labeling_logic():
    """Kiểm tra độ chính xác của 3-Class Triple Barrier"""
    # Tạo mock nến dốc đứng lên để test class 1
    dates = pd.date_range(start="2026-01-01", periods=10, freq='1min')
    df_up = pd.DataFrame({
        'open': np.arange(100, 110, 1.0),
        'high': np.arange(100, 110, 1.0) + 0.1,
        'low': np.arange(100, 110, 1.0) - 0.1,
        'close': np.arange(100, 110, 1.0)
    }, index=dates)
    
    labeler = LabelingV3(tp_pips=20, sl_pips=20, max_hold_bars=5, pip_size=0.1) # 20 pips = 2.0 giá
    
    # Từ giá 100 lên 102 mất 2 nến, TP = +2.0 => Phải chạm TP => nhãn 1 (Buy Win)
    labels = labeler.apply_triple_barrier(df_up, 'open', 'high', 'low')
    
    assert labels.iloc[0] == 1, "Nến dốc lên phải chạm TakeProfit và đánh nhãn 1 (BUY)"
    
    # Test đi ngang (sideway)
    df_flat = pd.DataFrame({
        'open': np.full(10, 100.0),
        'high': np.full(10, 100.1),
        'low': np.full(10, 99.9),
        'close': np.full(10, 100.0)
    }, index=dates)
    
    labels_flat = labeler.apply_triple_barrier(df_flat, 'open', 'high', 'low')
    assert labels_flat.iloc[0] == 2, "Nến đi ngang phải Timeout và đánh nhãn 2 (Sideway)"
