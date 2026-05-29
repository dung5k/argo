"""
phoenix_v2.py — Phoenix Restart V2 (Magnitude-aware Perturbation)
==================================================================
Cải tiến so với V1:

    V1 (Chiến lược B):
        noise = randn() × σ   (σ ∈ [0.001, 0.005])
    Vấn đề:
        Mạng Transformer có phương sai trọng số khác nhau giữa các layer.
        1 σ tĩnh có thể "muối bỏ bể" với layer này hoặc "sóng thần" layer khác.

    V2 (Chiến lược B mới):
        noise = randn() × |w| × α   (α ∈ [0.02, 0.08])
    Toán học:
        Δw ~ N(0, (α · ||w||)²)
    Tính chất:
        - Nhiễu tỷ lệ với độ lớn của chính tham số đó.
        - Bảo toàn cấu trúc ma trận: layer nhỏ nhận nhiễu nhỏ, layer lớn nhận nhiễu lớn.
        - Attention head không bị phá vỡ bởi nhiễu bất tương xứng.
"""

import copy
import random
import torch
import torch.optim as optim
from typing import Callable, Tuple


class PhoenixRestartV2:
    """
    Quản lý Phoenix Restart với 4 chiến lược, trong đó Chiến lược B được nâng cấp
    thành Magnitude-aware Perturbation.

    Parameters
    ----------
    model : torch.nn.Module
        Model đang training.
    base_lr : float
        Learning rate cơ sở dùng để reset sau perturbation.
    weight_decay : float
        Weight decay cho AdamW.
    max_phoenix : int
        Số lần tái sinh tối đa.
    max_stagnate : int
        Số epoch không cải thiện trước khi trigger phoenix.
    min_signals : int
        Số lượng tín hiệu tối thiểu để coi là hợp lệ về mặt thống kê.
    """

    def __init__(
        self,
        model: torch.nn.Module,
        base_lr: float = 1e-4,
        weight_decay: float = 1e-3,
        max_phoenix: int = 40,
        max_stagnate: int = 10,
        min_signals: int = 30,
    ):
        self.model = model
        self.base_lr = base_lr
        self.weight_decay = weight_decay
        self.max_phoenix = max_phoenix
        self.max_stagnate = max_stagnate
        self.min_signals = min_signals

        self.phoenix_count = 0
        self.epochs_no_improve = 0

        # Khởi tạo optimizer và scheduler ban đầu
        self.optimizer = self._make_optimizer(base_lr)
        self.scheduler = self._make_scheduler(self.optimizer)

    # ------------------------------------------------------------------ #
    #  Internal factory methods                                            #
    # ------------------------------------------------------------------ #
    def _make_optimizer(self, lr: float) -> optim.Optimizer:
        return optim.AdamW(
            self.model.parameters(), lr=lr, weight_decay=self.weight_decay
        )

    def _make_scheduler(
        self, optimizer: optim.Optimizer
    ) -> optim.lr_scheduler.ReduceLROnPlateau:
        return optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="max", patience=10, factor=0.5, min_lr=1e-6
        )

    # ------------------------------------------------------------------ #
    #  Perturbation strategies                                             #
    # ------------------------------------------------------------------ #
    def _strategy_a(self) -> bool:
        """LR Spike — thoát local minima bằng tốc độ học lớn nhất thời."""
        spike_lr = random.uniform(2e-4, 8e-4)
        self.optimizer = self._make_optimizer(lr=spike_lr)
        self.scheduler = self._make_scheduler(self.optimizer)
        print(f"  [Phoenix-A] LR Spike → LR={spike_lr:.1e} (thoát local minima)")
        return False  # Không cần reload DataLoader

    def _strategy_b(self) -> bool:
        """
        Magnitude-aware Noise Injection (V2).
        Δw ~ N(0, (α · |w|)²)  →  không phá cấu trúc layer có trọng số nhỏ.
        """
        alpha = random.uniform(0.02, 0.08)
        total_params = 0
        with torch.no_grad():
            for param in self.model.parameters():
                noise = torch.randn_like(param) * param.abs() * alpha
                param.add_(noise)
                total_params += param.numel()
        self.optimizer = self._make_optimizer(lr=self.base_lr)
        self.scheduler = self._make_scheduler(self.optimizer)
        print(
            f"  [Phoenix-B] Magnitude-aware Noise α={alpha:.3f} "
            f"({total_params:,} params nhiễu hóa)"
        )
        return False

    def _strategy_c(self) -> bool:
        """Fine-tune sâu — LR nhỏ + Weight Decay cao để tinh chỉnh precision."""
        fine_lr = random.uniform(5e-5, 2e-4)
        wd = random.uniform(1e-3, 5e-3)
        self.optimizer = optim.AdamW(
            self.model.parameters(), lr=fine_lr, weight_decay=wd
        )
        self.scheduler = self._make_scheduler(self.optimizer)
        print(f"  [Phoenix-C] Fine-tune Sâu LR={fine_lr:.1e}, WD={wd:.4f}")
        return False

    def _strategy_d(self) -> Tuple[bool, int]:
        """Batch Shuffle — đa dạng gradient bằng batch size khác nhau."""
        new_batch = random.choice([128, 256, 384])
        print(f"  [Phoenix-D] Batch Shuffle → batch_size={new_batch}")
        return True, new_batch  # Cần reload DataLoader với batch_size mới

    # ------------------------------------------------------------------ #
    #  Public interface                                                     #
    # ------------------------------------------------------------------ #
    def apply_perturbation(
        self, chosen_state_dict: dict
    ) -> Tuple[bool, int]:
        """
        Áp dụng chiến lược perturbation ngẫu nhiên sau khi phoenix được trigger.

        Parameters
        ----------
        chosen_state_dict : dict
            State dict tốt nhất (hoặc ngẫu nhiên từ top_configs) để restore trước khi perturbation.

        Returns
        -------
        need_reload : bool
            True nếu cần tạo lại DataLoader (Chiến lược D).
        new_batch_size : int
            Batch size mới (chỉ có nghĩa khi need_reload=True).
        """
        self.model.load_state_dict(copy.deepcopy(chosen_state_dict))

        strat = random.choice(["A", "B", "C", "D"])
        if strat == "A":
            need_reload = self._strategy_a()
            return need_reload, 0
        elif strat == "B":
            need_reload = self._strategy_b()
            return need_reload, 0
        elif strat == "C":
            need_reload = self._strategy_c()
            return need_reload, 0
        else:  # D
            need_reload, new_batch = self._strategy_d()
            return need_reload, new_batch

    def notify_improved(self):
        """Gọi khi có cải thiện — reset đếm stagnation."""
        self.epochs_no_improve = 0

    def notify_no_improve(self) -> bool:
        """
        Gọi khi không có cải thiện.

        Returns
        -------
        bool
            True nếu cần trigger phoenix restart.
        """
        self.epochs_no_improve += 1
        if self.epochs_no_improve >= self.max_stagnate:
            self.phoenix_count += 1
            self.epochs_no_improve = 0
            return True
        return False

    @property
    def exhausted(self) -> bool:
        """True nếu đã dùng hết tất cả lần phoenix."""
        return self.phoenix_count > self.max_phoenix

    @property
    def remaining(self) -> int:
        """Số lần phoenix còn lại."""
        return max(0, self.max_phoenix - self.phoenix_count)
