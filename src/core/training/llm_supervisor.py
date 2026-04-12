"""
LLM Supervisor — gọi Gemini Flash để tối ưu hyperparams sau mỗi N epochs.

Trách nhiệm:
  - build_context(): Đóng gói trạng thái training thành payload cho LLM.
  - call(): Gọi ai_supervisor.call_llm_meta_optimizer().
  - apply_actions(): Parse JSON response, áp dụng điều chỉnh, trả lại state mới.
  - send_telegram(): Gửi báo cáo lên Telegram.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional


class TrainingState:
    """
    Snapshot trạng thái training tại một epoch — dùng làm input/output cho LLMSupervisor.
    Tất cả field đều mutable — apply_actions() cập nhật trực tiếp.
    """

    def __init__(
        self,
        history: list,
        lr: float,
        base_lr: float,
        weight_decay: float,
        min_signals: int,
        cm_active_window: int,
        window_size: int,
        patience: int,
        label_smoothing: float,
        batch_size: int,
        grad_clip: float,
        masked_features: List[str],
        totals_t: List[int],
        phoenix_count: int,
    ):
        self.history          = history
        self.lr               = lr
        self.base_lr          = base_lr
        self.weight_decay     = weight_decay
        self.min_signals      = min_signals
        self.cm_active_window = cm_active_window
        self.window_size      = window_size
        self.patience         = patience
        self.label_smoothing  = label_smoothing
        self.batch_size       = batch_size
        self.grad_clip        = grad_clip
        self.masked_features  = masked_features
        self.totals_t         = totals_t
        self.phoenix_count    = phoenix_count
        # Flags đặt bởi apply_actions
        self.need_reload_loader = False
        self.force_phoenix      = False


class LLMSupervisor:
    """
    Kết nối với AI supervisor để tối ưu hyperparams trong quá trình training.

    Args:
        ai_supervisor_path: Đường dẫn tuyệt đối tới ai_supervisor.py.
        base_dir          : Thư mục gốc dự án (để đọc tg_config.json).
        target_prefix     : Tên symbol (dùng trong Telegram message).
    """

    def __init__(self, ai_supervisor_path: str, base_dir: str, target_prefix: str):
        self.ai_supervisor_path = ai_supervisor_path
        self.base_dir           = base_dir
        self.target_prefix      = target_prefix

    def _load_ai_supervisor(self):
        """Lazy-load ai_supervisor module theo đường dẫn file."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("ai_supervisor", self.ai_supervisor_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def build_context(self, state: TrainingState, current_epoch: int) -> dict:
        """
        Đóng gói trạng thái training thành format history_buffer cho LLM.

        Returns:
            Dict đúng format mà call_llm_meta_optimizer() mong đợi.
        """
        return {
            "2": {
                "avg_train_loss_history":   [h["loss"] for h in state.history],
                "avg_val_loss_history":     [h["loss"] for h in state.history],
                "win_rate_L4_history":      [h["wr"]   for h in state.history],
                "total_signals_L4_history": [state.totals_t[3]] * len(state.history)
                                             if len(state.totals_t) > 3 else [],
                "phoenix_count":            state.phoenix_count,
                "current_lr":               float(state.lr),
                "current_base_lr":          float(state.base_lr),
                "current_weight_decay":     float(state.weight_decay),
                "current_min_signals":      state.min_signals,
                "current_cm_window":        int(state.cm_active_window),
                "current_cm_max_window":    int(state.window_size),
                "current_patience":         int(state.patience),
                "current_label_smoothing":  float(state.label_smoothing),
                "current_batch_size":       int(state.batch_size),
                "current_grad_clip":        float(state.grad_clip),
                "current_masked_features":  state.masked_features,
            }
        }

    def call(self, context: dict, current_epoch: int) -> Optional[dict]:
        """
        Gọi API LLM và trả về response JSON (hoặc None nếu thất bại/không có API key).
        """
        if not os.path.exists(self.ai_supervisor_path):
            return None
        try:
            sv = self._load_ai_supervisor()
            return sv.call_llm_meta_optimizer(context, current_epoch, base_dir=self.base_dir)
        except Exception as e:
            print(f"🤖 [LLM SUPERVISOR ERR] {e}")
            return None

    def send_telegram(self, message: str) -> None:
        """Gửi message lên Telegram nếu tg_config.json tồn tại và hợp lệ."""
        try:
            import requests
            tg_path = os.path.join(self.base_dir, "tg_config.json")
            if not os.path.exists(tg_path):
                return
            with open(tg_path, "r", encoding="utf-8") as f:
                tg_cfg = json.load(f)
            tok  = tg_cfg.get("bot_token")
            ids  = tg_cfg.get("allowed_user_ids", [])
            if not tok or not ids:
                return
            import socket
            full_msg = f"🤖 <b>[LLM SUPERVISOR - {self.target_prefix} @ {socket.gethostname()}]</b>\n\n{message}"
            for chat_id in ids:
                requests.post(
                    f"https://api.telegram.org/bot{tok}/sendMessage",
                    data={"chat_id": chat_id, "text": full_msg, "parse_mode": "HTML"},
                    timeout=5,
                )
        except Exception as e:
            print(f"  [Telegram Error] {e}")

    def apply_actions(
        self,
        response: dict,
        state: TrainingState,
        optimizer,
        scheduler,
        criterion_factory: Callable,
        resolve_masked_indices: Callable,
        feature_col_names: List[str],
        class_weights,
        device,
        nn_module,
    ) -> TrainingState:
        """
        Áp dụng các điều chỉnh từ LLM response vào state và optimizer/scheduler.

        Args:
            response           : Dict JSON trả về từ call().
            state              : TrainingState hiện tại (sẽ bị mutate).
            optimizer          : AdamW optimizer.
            scheduler          : ReduceLROnPlateau scheduler.
            criterion_factory  : Callable(label_smoothing) → nn.CrossEntropyLoss.
            resolve_masked_indices: Hàm ánh xạ feature name → index.
            feature_col_names  : Danh sách tên features.
            class_weights      : Tensor class weights cho CrossEntropyLoss.
            device             : Torch device.
            nn_module          : torch.nn module (để tạo criterion mới).

        Returns:
            state (đã được mutate).
        """
        act = response.get("actions", {}).get("2", {})
        if not act:
            return state

        if "new_lr" in act:
            v = float(act["new_lr"])
            if 1e-6 <= v <= 1e-2:
                for pg in optimizer.param_groups:
                    pg["lr"] = v
                print(f"  [LLM] Điều chỉnh LR = {v:.1e}")

        if "base_lr" in act:
            v = float(act["base_lr"])
            if 1e-5 <= v <= 1e-3:
                state.base_lr = v
                print(f"  [LLM] Điều chỉnh BASE_LR = {v:.1e}")

        if "weight_decay" in act:
            v = float(act["weight_decay"])
            if 0 <= v <= 0.1:
                for pg in optimizer.param_groups:
                    pg["weight_decay"] = v
                state.weight_decay = v
                print(f"  [LLM] Điều chỉnh WD = {v}")

        if "label_smoothing" in act:
            v = float(act["label_smoothing"])
            if 0.0 <= v <= 0.3:
                new_criterion = criterion_factory(v)
                state.label_smoothing = v
                print(f"  [LLM] Điều chỉnh Label Smoothing = {v}")
                # Trả criterion mới qua attribute của state để caller dùng
                state._new_criterion = new_criterion

        if "min_signals" in act:
            v = int(act["min_signals"])
            if 10 <= v <= 100:
                state.min_signals = v
                print(f"  [LLM] Điều chỉnh MIN_SIGNALS = {v}")

        if "active_window_size" in act:
            v = int(act["active_window_size"])
            if 10 <= v <= state.window_size:
                state.cm_active_window = v
                print(f"  [LLM] Điều chỉnh Curriculum Window = {v} nến")

        if "masked_features" in act:
            v = act["masked_features"]
            if isinstance(v, list):
                state.masked_features = v
                state._new_masked_indices = resolve_masked_indices(feature_col_names, v)
                print(f"  [LLM] Cập nhật Masked Features: {v if v else '(Bỏ mask)'}")

        if "patience" in act:
            v = int(act["patience"])
            if 3 <= v <= 30:
                scheduler.patience = v
                state.patience = v
                print(f"  [LLM] Điều chỉnh Patience = {v}")

        if "batch_size" in act:
            v = int(act["batch_size"])
            if v in [128, 256, 512, 1024]:
                state.batch_size = v
                state.need_reload_loader = True
                print(f"  [LLM] Điều chỉnh Batch Size = {v}")

        if "grad_clip" in act:
            v = float(act["grad_clip"])
            if 0.5 <= v <= 5.0:
                state.grad_clip = v
                print(f"  [LLM] Điều chỉnh Grad Clip = {v}")

        if act.get("action_type") == "force_phoenix":
            print("  [LLM] 🔥 Bắt buộc Phoenix!")
            state.force_phoenix = True

        return state
