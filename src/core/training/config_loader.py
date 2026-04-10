"""
Training configuration loader.

Trách nhiệm: Đọc config JSON, parse date range và hyperparams.
Input : config_path (str)
Output: TrainingConfig dataclass
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd


@dataclass
class TrainingConfig:
    # Architecture
    window_size: int = 60
    d_model: int = 256
    nhead: int = 8
    num_attn_layers: int = 3
    dropout_rate: float = 0.2

    # Phoenix / Training loop
    epochs: int = 10000
    batch_size: int = 512
    base_lr: float = 3e-4
    max_stagnate: int = 10
    max_phoenix: int = 40
    min_signals: int = 30
    ai_supervisor_interval: int = 50

    # Date range (resolved)
    train_start: Optional[pd.Timestamp] = None
    train_end: Optional[pd.Timestamp] = None
    val_start: Optional[pd.Timestamp] = None
    val_end: Optional[pd.Timestamp] = None

    # Directories — mặc định dùng env hoặc fallback về project data/
    argo_data_dir: str = field(default_factory=lambda: os.environ.get("ARGO_DATA_DIR", "data"))
    argo_logs_dir: str = field(default_factory=lambda: os.environ.get("ARGO_LOGS_DIR", "logs"))

    # Identifiers
    config_id: str = "DEFAULT"
    target_prefix: str = "XAUUSD"

    # Curriculum Masking
    cm_enabled: bool = False
    cm_active_window: int = 60
    cm_masked_features: List[str] = field(default_factory=list)

    # Raw loaded dict (for downstream consumers)
    raw: dict = field(default_factory=dict)

    @staticmethod
    def _find_default_config(base_proj: str) -> Optional[str]:
        """Tìm config file mặc định trong thư mục data/."""
        for candidate in [
            os.path.join(base_proj, "data", "bot_config_xau.json"),
            os.path.join(base_proj, "data", "bot_config.json"),
        ]:
            if os.path.exists(candidate):
                return candidate
        return None

    @classmethod
    def load(cls, config_path: Optional[str] = None, base_proj: Optional[str] = None) -> "TrainingConfig":
        """
        Load TrainingConfig từ JSON file.

        Args:
            config_path: Đường dẫn tuyệt đối tới file JSON. Nếu None, tìm file mặc định.
            base_proj: Thư mục gốc dự án (dùng khi config_path=None).

        Returns:
            TrainingConfig đã được populate đầy đủ.
        """
        cfg = cls()

        raw: dict = {}
        if config_path is None and base_proj:
            config_path = cls._find_default_config(base_proj)

        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        cfg.raw = raw

        # Identifiers
        cfg.config_id = raw.get("CONFIG_ID", "DEFAULT")
        cfg.target_prefix = raw.get("TARGET_PREFIX", "XAUUSD")

        # Architecture from TRAINING block
        training_block = raw.get("TRAINING", {})
        arch = training_block.get("ARCH", {})
        cfg.window_size = arch.get("win", cfg.window_size)
        cfg.d_model = arch.get("d_model", cfg.d_model)
        cfg.nhead = arch.get("heads", cfg.nhead)
        cfg.num_attn_layers = arch.get("layers", cfg.num_attn_layers)
        cfg.dropout_rate = arch.get("dropout", cfg.dropout_rate)
        cfg.batch_size = training_block.get("BATCH_SIZE", cfg.batch_size)

        # Directories
        cfg.argo_data_dir = raw.get("ARGO_DATA_DIR",
                                    os.environ.get("ARGO_DATA_DIR", cfg.argo_data_dir))
        cfg.argo_logs_dir = raw.get("ARGO_LOGS_DIR",
                                    os.environ.get("ARGO_LOGS_DIR", cfg.argo_logs_dir))

        # Curriculum Masking
        cm = raw.get("CURRICULUM_MASKING", {})
        cfg.cm_enabled = cm.get("ENABLE", False)
        cfg.cm_active_window = cm.get("ACTIVE_WINDOW_SIZE", cfg.window_size)
        cfg.cm_masked_features = cm.get("MASKED_FEATURES", [])

        # Date range
        cfg.train_start, cfg.train_end, cfg.val_start, cfg.val_end = cls._resolve_date_range(raw, training_block)

        return cfg

    @staticmethod
    def _resolve_date_range(raw: dict, training_block: dict) -> Tuple[
        pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp
    ]:
        """
        Parse date range từ config.
        Nếu không có config → dùng rolling window mặc định.

        Returns:
            (train_start, train_end, val_start, val_end) — tất cả timezone-aware UTC.
        """
        def _get(key: str) -> Optional[str]:
            return raw.get(key) or training_block.get(key)

        t_start = _get("TRAIN_START") or _get("TRAIN_FROM")
        t_end   = _get("TRAIN_END")   or _get("TRAIN_TO")
        v_end   = _get("VAL_END")     or _get("VAL_TO")

        if t_start and t_end and v_end:
            train_start = pd.Timestamp(t_start, tz="UTC")
            train_end   = pd.Timestamp(t_end, tz="UTC")
            val_start   = train_end
            val_end     = pd.Timestamp(v_end, tz="UTC") + pd.Timedelta(days=1)
        else:
            now_utc     = pd.Timestamp.now(tz="UTC")
            val_end     = now_utc
            val_start   = val_end   - pd.Timedelta(days=4)
            train_end   = val_start
            train_start = train_end - pd.Timedelta(days=90)

        return train_start, train_end, val_start, val_end
