"""
Checkpoint Manager.

Trách nhiệm: Tìm kiếm, load, save checkpoint và đồng bộ HuggingFace.
Input : paths, model, metadata
Output: trạng thái model đã cập nhật (hoặc không thay đổi nếu không tìm thấy ckpt)
"""
from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional

import torch
import torch.nn as nn


class CheckpointManager:
    """
    Quản lý lifecycle checkpoint của một training run.

    Args:
        run_dir    : Thư mục lưu kết quả run hiện tại.
        runs_base  : Thư mục cha chứa tất cả các run (C:/argo/logs/runs).
        target_name: Tên target viết thường (vd: 'xauusd').
        cfg_id     : CONFIG_ID dùng để lọc checkpoint cùng cấu hình.
        device     : Torch device.
    """

    def __init__(
        self,
        run_dir: str,
        runs_base: str,
        target_name: str,
        cfg_id: str,
        device: torch.device,
    ):
        self.run_dir     = run_dir
        self.runs_base   = runs_base
        self.target_name = target_name
        self.cfg_id      = cfg_id
        self.device      = device

    def find_candidates(self) -> List[Path]:
        """
        Tìm các checkpoint phù hợp với target_name và cfg_id.

        Returns:
            Danh sách Path đã sort theo tên thư mục cha giảm dần (mới nhất trước).
        """
        base = Path(self.runs_base)
        if not base.exists():
            return []
        candidates = sorted(
            [
                p for p in base.glob(f"**/{self.target_name}_unified_weights*.pth")
                if "old" not in p.parts and self.cfg_id in str(p)
            ],
            key=lambda p: p.parent.name,
            reverse=True,
        )
        return candidates

    def delete_candidates(self, candidates: List[Path]) -> None:
        """Xóa toàn bộ thư mục cha của checkpoint candidates (dùng cho --reset)."""
        import shutil
        for ckpt in candidates:
            try:
                shutil.rmtree(ckpt.parent)
                print(f"   Đã xóa: {ckpt.parent.name}")
            except Exception as e:
                print(f"   Không thể xóa {ckpt.parent.name}: {e}")

    def load_transfer(self, model: nn.Module, checkpoint_path: Path) -> bool:
        """
        Load transfer learning từ checkpoint, lọc các layer bị shape mismatch.

        Args:
            model          : Model cần load trọng số vào.
            checkpoint_path: Đường dẫn tới file .pth.

        Returns:
            True nếu load thành công, False nếu thất bại.
        """
        try:
            state = torch.load(str(checkpoint_path), map_location=self.device, weights_only=True)
            current = model.state_dict()
            matched = {}
            for k, v in state.items():
                if k in current and current[k].shape == v.shape:
                    matched[k] = v
                else:
                    print(f"    ⚠️ Bỏ qua layer: {k} (kích thước đổi)")
            current.update(matched)
            model.load_state_dict(current)
            print(f"    ✅ TRANSFER LEARNING: Kế thừa từ {checkpoint_path.parent.name}")
            return True
        except Exception as e:
            print(f"    ⚠️ Không thể load checkpoint ({e}) → Khởi tạo model mới.")
            return False

    def save_ranked_weights(self, model: nn.Module, strategy_name: str) -> None:
        """Lưu trọng số theo tên chiến thuật."""
        path = os.path.join(self.run_dir, f"{self.target_name}_unified_weights_{strategy_name}.pth")
        torch.save(model.state_dict(), path)

    def save_best_weights(self, state_dict: dict) -> None:
        """Lưu bản trọng số tốt nhất (unified_weights.pth)."""
        path = os.path.join(self.run_dir, f"{self.target_name}_unified_weights.pth")
        torch.save(state_dict, path)

    def save_blackbox(
        self,
        epoch_num: int,
        global_best_score: float,
        global_best_val_loss: float,
        best_max_thresh: float,
        best_thresholds: List[float],
        best_wrs: List[float],
        best_totals: List[int],
        top_configs: Dict,
        target_prefix: str,
        is_interrupted: bool = False,
    ) -> None:
        """
        Ghi trạng thái training vào training_metrix.json và đồng bộ HF bất đồng bộ.
        """
        top_configs_meta = []
        for s_name, cfg_entry in top_configs.items():
            if cfg_entry is not None:
                top_configs_meta.append({
                    "strategy":  s_name,
                    "score":     cfg_entry["score"] * 100,
                    "epoch":     cfg_entry.get("epoch", -1),
                    "max_thresh": cfg_entry["max_thresh"],
                    "thresholds": cfg_entry["thresholds"],
                    "win_rates":  [wr * 100 for wr in cfg_entry["wrs"]],
                    "totals":     cfg_entry["totals"],
                })

        data = {
            "target":           self.target_name,
            "status":           "STOPPED" if is_interrupted else "RUNNING_OR_DONE",
            "epochs_trained":   epoch_num,
            "best_winrate":     global_best_score * 100,
            "best_val_loss":    global_best_val_loss,
            "best_max_thresh":  best_max_thresh,
            "thresholds":       best_thresholds,
            "win_rates":        [wr * 100 for wr in best_wrs],
            "totals":           best_totals,
            "top_configs_saved": top_configs_meta,
        }

        blackbox_file = os.path.join(self.run_dir, "training_metrix.json")
        try:
            with open(blackbox_file, "w", encoding="utf-8") as bf:
                json.dump(data, bf, indent=4, ensure_ascii=False)
        except Exception:
            pass

        threading.Thread(target=self._push_hf_async, daemon=True).start()

    def _push_hf_async(self) -> None:
        """Đồng bộ trọng số lên HuggingFace trong background thread."""
        try:
            base_dir = os.path.dirname(os.path.dirname(self.run_dir))
            orch_dir = os.path.join(base_dir, "src", "orchestration")
            import sys
            if orch_dir not in sys.path:
                sys.path.insert(0, orch_dir)
            from hf_sync import push_runs
            ok = push_runs()
            if ok:
                print("    [HF] Đã đồng bộ trọng số mới lên HuggingFace.")
        except Exception:
            pass
