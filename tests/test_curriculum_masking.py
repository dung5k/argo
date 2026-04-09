"""
test_curriculum_masking.py - Unit Tests cho apply_curriculum_mask
=================================================================
Bao gồm 4 tiêu chí bắt buộc theo Ticket:
  1. Bảo toàn Shape (Shape Preservation)
  2. Time-step Masking đúng chỗ
  3. Feature Masking đúng cột
  4. Vùng An Toàn - Data Integrity (không rò rỉ tham chiếu)

Chạy: python -m pytest tests/test_curriculum_masking.py -v
"""

import sys
import os
from pathlib import Path

# Đảm bảo import được từ src/
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest
import torch

from src.training_v1_5.curriculum_masking import apply_curriculum_mask, resolve_masked_indices


# ==============================================================
# Fixtures
# ==============================================================
BATCH_SIZE   = 8
WINDOW_SIZE  = 60
NUM_FEATURES = 56


@pytest.fixture
def sample_batch() -> torch.Tensor:
    """Tạo batch tensor ngẫu nhiên có giá trị thật để kiểm tra data integrity."""
    torch.manual_seed(42)
    # Đảm bảo không có số 0 ngẫu nhiên nào (để test masked vs unmasked rõ ràng hơn)
    t = torch.rand(BATCH_SIZE, WINDOW_SIZE, NUM_FEATURES) + 0.1  # range [0.1, 1.1]
    return t


# ==============================================================
# Tiêu chí 1: Bảo toàn Shape
# ==============================================================
class TestShapePreservation:

    def test_shape_unchanged_with_masking(self, sample_batch):
        """Output phải có shape Y HỆT Input. Tuyệt đối không slice."""
        active_window  = 15
        masked_indices = [0, 5, 10]
        result = apply_curriculum_mask(sample_batch, active_window, masked_indices)
        assert result.shape == sample_batch.shape, (
            f"Shape thay đổi! Input: {sample_batch.shape}, Output: {result.shape}"
        )

    def test_shape_with_full_window(self, sample_batch):
        """active_window = window_size -> không che nến nào, shape vẫn giữ."""
        result = apply_curriculum_mask(sample_batch, WINDOW_SIZE, [])
        assert result.shape == sample_batch.shape

    def test_shape_with_zero_active_window(self, sample_batch):
        """active_window = 0 -> che toàn bộ nến, shape vẫn giữ."""
        result = apply_curriculum_mask(sample_batch, 0, [])
        assert result.shape == sample_batch.shape

    def test_shape_with_no_masked_features(self, sample_batch):
        """Không có feature nào bị mask, chỉ mask time-step."""
        result = apply_curriculum_mask(sample_batch, 15, [])
        assert result.shape == sample_batch.shape


# ==============================================================
# Tiêu chí 2: Time-step Masking
# ==============================================================
class TestTimestepMasking:

    def test_old_candles_are_zero(self, sample_batch):
        """
        Nến 0..(window - active_window - 1) BẮT BUỘC bằng 0.0.
        Ví dụ: active_window=15, window=60 -> nến 0..44 phải = 0.
        """
        active_window = 15
        num_masked_steps = WINDOW_SIZE - active_window  # 45

        result = apply_curriculum_mask(sample_batch, active_window, [])
        masked_region = result[:, :num_masked_steps, :]  # [B, 45, F]

        assert torch.all(masked_region == 0.0), (
            f"Vùng masked (nến 0..{num_masked_steps-1}) chứa giá trị != 0!"
        )

    def test_recent_candles_are_nonzero(self, sample_batch):
        """
        Vùng active window (nến cuối) của các feature KHÔNG bị mask phải có
        giá trị thật, không bị zeroed-out bởi time-step mask.
        """
        active_window = 15
        result = apply_curriculum_mask(sample_batch, active_window, [])
        active_region = result[:, -active_window:, :]  # [B, 15, F]

        # Tất cả phần tử trong active region phải khác 0 (vì fixture +0.1)
        assert torch.any(active_region != 0.0), (
            "Vùng active window bị zeroed-out sai!"
        )

    def test_timestep_mask_boundary_exact(self, sample_batch):
        """
        Kiểm tra chính xác ranh giới: nến (W-active_window-1) phải = 0,
        nến (W-active_window) phải != 0.
        """
        active_window = 20
        num_masked_steps = WINDOW_SIZE - active_window  # 40

        result = apply_curriculum_mask(sample_batch, active_window, [])

        # Nến cuối cùng trong vùng bị mask
        last_masked_candle = result[:, num_masked_steps - 1, :]  # timestep 39
        assert torch.all(last_masked_candle == 0.0), "Nến cuối vùng mask chưa bị zero!"

        # Nến đầu tiên của vùng active (không bị mask bởi time-step)
        first_active_candle = result[:, num_masked_steps, :]  # timestep 40
        assert torch.any(first_active_candle != 0.0), "Nến đầu vùng active bị zero sai!"

    def test_full_window_active_no_timestep_mask(self, sample_batch):
        """active_window = window_size -> không có nến nào bị mask."""
        result = apply_curriculum_mask(sample_batch, WINDOW_SIZE, [])
        assert torch.allclose(result, sample_batch), (
            "Khi active_window = window_size, không được thay đổi dữ liệu!"
        )

    def test_zero_active_window_masks_all(self, sample_batch):
        """active_window = 0 -> toàn bộ window bị zero-out."""
        result = apply_curriculum_mask(sample_batch, 0, [])
        assert torch.all(result == 0.0), (
            "Khi active_window = 0, toàn bộ tensor phải = 0!"
        )


# ==============================================================
# Tiêu chí 3: Feature Masking
# ==============================================================
class TestFeatureMasking:

    def test_masked_features_all_zero_entire_window(self, sample_batch):
        """
        Toàn bộ cột trong masked_indices phải = 0.0 trên TẤT CẢ 60 nến.
        Kể cả vùng active window.
        """
        masked_indices = [3, 10, 25, 50]
        result = apply_curriculum_mask(sample_batch, WINDOW_SIZE, masked_indices)

        for idx in masked_indices:
            col_values = result[:, :, idx]  # [B, W]
            assert torch.all(col_values == 0.0), (
                f"Feature index {idx} chưa được zero-out đúng toàn bộ window!"
            )

    def test_unmasked_features_unchanged_in_active_window(self, sample_batch):
        """
        Các feature KHÔNG trong masked_indices phải giữ nguyên giá trị gốc
        ở vùng active window.
        """
        active_window  = 15
        masked_indices = [0, 1, 2]  # chỉ mask 3 features đầu
        result = apply_curriculum_mask(sample_batch, active_window, masked_indices)

        # Feature 5 (không bị mask) tại vùng active window phải = gốc
        unmasked_feat = 5
        active_result   = result[:, -active_window:, unmasked_feat]
        active_original = sample_batch[:, -active_window:, unmasked_feat]
        assert torch.allclose(active_result, active_original), (
            f"Feature {unmasked_feat} bị thay đổi sai ở vùng active window!"
        )

    def test_feature_masking_covers_full_window_including_active_region(self, sample_batch):
        """
        Feature masking phải bao phủ CẢ vùng active window (không chỉ vùng old).
        """
        active_window  = 30
        masked_indices = [7, 14]
        result = apply_curriculum_mask(sample_batch, active_window, masked_indices)

        for idx in masked_indices:
            # Vùng active window của feature bị mask cũng phải = 0
            active_region_col = result[:, -active_window:, idx]
            assert torch.all(active_region_col == 0.0), (
                f"Feature {idx} chưa bị zero toàn window (kể cả active region)!"
            )

    def test_empty_masked_indices_no_feature_mask(self, sample_batch):
        """Không có feature nào bị mask -> dữ liệu feature không thay đổi."""
        result = apply_curriculum_mask(sample_batch, WINDOW_SIZE, [])
        assert torch.allclose(result, sample_batch), (
            "Khi masked_indices rỗng, không feature nào được thay đổi!"
        )


# ==============================================================
# Tiêu chí 4: Vùng An Toàn - Data Integrity
# ==============================================================
class TestDataIntegrity:

    def test_no_reference_leak_original_unchanged(self, sample_batch):
        """
        Tensor gốc (batch_x) KHÔNG được bị thay đổi sau khi gọi hàm.
        apply_curriculum_mask phải clone, không mutate in-place.
        """
        original_copy = sample_batch.clone()
        _result = apply_curriculum_mask(sample_batch, 15, [0, 5, 10])

        assert torch.allclose(sample_batch, original_copy), (
            "Reference leak! Tensor gốc bị thay đổi sau khi gọi apply_curriculum_mask!"
        )

    def test_active_window_data_exactly_matches_original(self, sample_batch):
        """
        Vùng active window của features KHÔNG bị mask phải khớp 100% với dữ liệu gốc.
        """
        active_window  = 15
        masked_indices = [0, 1, 2, 3]  # mask 4 features đầu
        unmasked_start = 4              # features từ index 4 trở đi không bị mask
        result = apply_curriculum_mask(sample_batch, active_window, masked_indices)

        active_result   = result[:, -active_window:, unmasked_start:]
        active_original = sample_batch[:, -active_window:, unmasked_start:]
        assert torch.allclose(active_result, active_original), (
            "Dữ liệu tại vùng active window của features không bị mask phải khớp 100% với gốc!"
        )

    def test_combined_mask_integrity(self, sample_batch):
        """
        Kết hợp cả time-step mask và feature mask, kiểm tra vùng an toàn
        [active_window, features_ngoài_masked] = gốc.
        """
        active_window  = 20
        masked_indices = [10, 11]
        result = apply_curriculum_mask(sample_batch, active_window, masked_indices)

        num_masked_steps = WINDOW_SIZE - active_window

        # Các feature KHÔNG bị mask trong vùng active window phải giống gốc
        safe_features = [i for i in range(NUM_FEATURES) if i not in masked_indices]
        for feat_idx in safe_features[:5]:  # test sample 5 features
            r = result[:, -active_window:, feat_idx]
            o = sample_batch[:, -active_window:, feat_idx]
            assert torch.allclose(r, o), (
                f"Feature {feat_idx} tại vùng active window bị thay đổi sai!"
            )

    def test_output_is_new_tensor_not_same_reference(self, sample_batch):
        """Kết quả trả về phải là tensor mới, không phải cùng object với input."""
        result = apply_curriculum_mask(sample_batch, 15, [0])
        assert result.data_ptr() != sample_batch.data_ptr(), (
            "Output là cùng object với input - nguy cơ reference leak!"
        )


# ==============================================================
# Tiêu chí Bổ sung: resolve_masked_indices
# ==============================================================
class TestResolvemaskedIndices:

    def test_resolve_known_features(self):
        """Chuyển tên feature -> index đúng."""
        features = ["feat_A", "feat_B", "feat_C", "feat_D"]
        masked   = ["feat_A", "feat_C"]
        result   = resolve_masked_indices(features, masked)
        assert result == [0, 2]

    def test_resolve_unknown_feature_ignored(self):
        """Feature không tồn tại sẽ bị bỏ qua (không raise)."""
        features = ["feat_A", "feat_B"]
        masked   = ["feat_A", "UNKNOWN_FEATURE"]
        result   = resolve_masked_indices(features, masked)
        assert result == [0]

    def test_resolve_empty_masked_list(self):
        """Danh sách masked rỗng -> trả về list rỗng."""
        features = ["feat_A", "feat_B"]
        result   = resolve_masked_indices(features, [])
        assert result == []


# ==============================================================
# Validation Error
# ==============================================================
class TestValidation:

    def test_invalid_active_window_too_large(self, sample_batch):
        """active_window > window_size phải raise ValueError."""
        with pytest.raises(ValueError):
            apply_curriculum_mask(sample_batch, WINDOW_SIZE + 1, [])

    def test_invalid_active_window_negative(self, sample_batch):
        """active_window < 0 phải raise ValueError."""
        with pytest.raises(ValueError):
            apply_curriculum_mask(sample_batch, -1, [])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
