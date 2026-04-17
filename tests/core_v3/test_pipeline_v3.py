import pytest
import numpy as np
import pandas as pd
import sys
import os

# Add project root to sys path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from scripts.upload_v3_dataset import build_tensor_dataset

def test_build_tensor_dataset():
    """Kiểm tra logic trượt cửa sổ 60 nến của quá trình tạo Tensor 3D"""
    
    # Giả lập 100 dòng Features có 15 cột
    features_val = np.random.randn(100, 15)
    df_features = pd.DataFrame(features_val)
    
    # Lắp nhãn class (0,1,2)
    labels = pd.Series(np.random.randint(0, 3, size=100))
    
    # Trượt rèm nến 60
    window_size = 60
    step_size = 1
    
    X, Y = build_tensor_dataset(df_features, labels, window_size, step_size)
    
    # 100 nến, bốc mỗi cửa sổ rộng 60 -> Sẽ có tổng (100 - 60) lốp xe = 40 mẫu (+1 nếu lấy viền, ở thuật toán dùng idx max = (100-60) -> chạy tới 39 nên là 40)
    # Check shape
    assert X.shape == (40, 60, 15), f"Lỗi Shape Ma Trận X: {X.shape}"
    assert Y.shape == (40,), f"Lỗi Shape Nhãn Y: {Y.shape}"
    
    # Kiểm tra map: Nhãn dự báo là của cây nến số window_size - 1 (nến đầu mép phải)
    assert Y[0] == labels[59], "Nhãn Mapping của Khung hình đầu tiên bị LỆCH."
    assert Y[-1] == labels[98], "Nhãn Mapping của Khung hình cuối cùng bị LỆCH."
