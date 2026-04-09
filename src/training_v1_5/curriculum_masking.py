"""
curriculum_masking.py - Curriculum Learning: Data Masking
==========================================================
Cung cấp hàm thuần túy (pure function) để che dữ liệu theo cơ chế Curriculum Learning.

Nguyên tắc:
  - GIỮ NGUYÊN shape tensor [batch_size, window_size, num_features].
  - Chỉ nhân các vùng chưa muốn AI học với 0.0 (zero-out).
  - Không slice, không thay đổi kiến trúc mạng, không ảnh hưởng Checkpoint.
"""

from typing import List
import torch


def apply_curriculum_mask(
    batch_x: torch.Tensor,
    active_window: int,
    masked_indices: List[int],
) -> torch.Tensor:
    """
    Áp dụng Curriculum Learning Masking lên batch tensor.

    Ma trận đầu vào giả định layout: [batch_size, window_size, num_features].
    Hàm tạo bản copy để tránh reference leak vào tensor gốc (data integrity).

    Args:
        batch_x        : Tensor [B, W, F] - batch dữ liệu gốc từ DataLoader.
        active_window  : Số nến mới nhất được GIỮ LẠI thật. Ví dụ: 15 -> chỉ
                         W-15 nến cuối có giá trị thật; 0..(W-15-1) bị zero-out.
        masked_indices : Danh sách index của các features bị zero-out toàn window.

    Returns:
        Tensor [B, W, F] - ĐÃ masked, cùng shape với batch_x.
        Hàm trả về tensor mới (clone), tensor gốc KHÔNG bị thay đổi.

    Raises:
        ValueError: Nếu active_window > W hoặc active_window < 0.
    """
    _, window_size, _ = batch_x.shape

    if active_window < 0 or active_window > window_size:
        raise ValueError(
            f"active_window={active_window} phải nằm trong [0, {window_size}]."
        )

    # Clone để tránh reference leak vào tensor gốc
    out = batch_x.clone()

    # --- Time-step Masking ---
    # Số nến bị che = window_size - active_window (tính từ đầu)
    num_masked_steps = window_size - active_window
    if num_masked_steps > 0:
        out[:, :num_masked_steps, :] = 0.0

    # --- Feature Masking ---
    # Toàn bộ window của các feature trong masked_indices bị zero-out
    if masked_indices:
        out[:, :, masked_indices] = 0.0

    return out


def resolve_masked_indices(feature_names: List[str], masked_feature_names: List[str]) -> List[int]:
    """
    Chuyển danh sách tên feature sang danh sách index trong feature_names.

    Args:
        feature_names       : Danh sách tên tất cả features theo thứ tự đúng.
        masked_feature_names: Danh sách tên features cần mask (từ config JSON).

    Returns:
        Danh sách index tương ứng. Features không tìm thấy sẽ bị bỏ qua + warning.
    """
    indices = []
    for name in masked_feature_names:
        if name in feature_names:
            indices.append(feature_names.index(name))
        else:
            print(f"[CURRICULUM] WARN: Feature '{name}' không tìm thấy trong danh sách features, bỏ qua.")
    return indices
