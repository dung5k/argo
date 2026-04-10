"""Unit tests cho llm_supervisor module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

import pytest
from unittest.mock import MagicMock, patch
import torch
import torch.nn as nn


def _make_state(**kwargs):
    from core.training.llm_supervisor import TrainingState
    defaults = dict(
        history=[{"loss": 0.69, "wr": 0.54}] * 5,
        lr=3e-4, base_lr=3e-4, weight_decay=1e-3,
        min_signals=30, cm_active_window=40,
        window_size=60, patience=10,
        label_smoothing=0.15, batch_size=512,
        grad_clip=1.0, masked_features=[],
        totals_t=[100, 80, 60, 40], phoenix_count=0,
    )
    defaults.update(kwargs)
    return TrainingState(**defaults)


class TestLLMSupervisorBuildContext:
    def test_context_has_session_2(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv = LLMSupervisor("", "", "XAUUSD")
        state = _make_state()
        ctx = sv.build_context(state, current_epoch=50)
        assert "2" in ctx

    def test_context_contains_current_lr(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv    = LLMSupervisor("", "", "XAUUSD")
        state = _make_state(lr=1e-4)
        ctx   = sv.build_context(state, current_epoch=50)
        assert ctx["2"]["current_lr"] == pytest.approx(1e-4)

    def test_history_lengths_match(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv    = LLMSupervisor("", "", "XAUUSD")
        state = _make_state()
        ctx   = sv.build_context(state, current_epoch=50)
        assert len(ctx["2"]["avg_val_loss_history"]) == len(state.history)


class TestLLMSupervisorApplyActions:
    def _make_optimizer_scheduler(self):
        m = nn.Linear(10, 2)
        opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-3)
        sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=10)
        return m, opt, sch

    def _make_criterion_factory(self):
        def factory(ls):
            return nn.CrossEntropyLoss(label_smoothing=ls)
        return factory

    def test_apply_new_lr(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv = LLMSupervisor("", "", "XAUUSD")
        _, opt, sch = self._make_optimizer_scheduler()
        state = _make_state()
        resp = {"actions": {"2": {"new_lr": 5e-5}}}
        sv.apply_actions(resp, state, opt, sch,
                          self._make_criterion_factory(),
                          lambda cols, names: [], [], None,
                          torch.device("cpu"), nn)
        assert opt.param_groups[0]["lr"] == pytest.approx(5e-5)

    def test_apply_base_lr(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv    = LLMSupervisor("", "", "XAUUSD")
        _, opt, sch = self._make_optimizer_scheduler()
        state = _make_state(base_lr=3e-4)
        resp  = {"actions": {"2": {"base_lr": 1e-4}}}
        sv.apply_actions(resp, state, opt, sch,
                          self._make_criterion_factory(),
                          lambda cols, names: [], [], None,
                          torch.device("cpu"), nn)
        assert state.base_lr == pytest.approx(1e-4)

    def test_apply_batch_size_sets_reload_flag(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv    = LLMSupervisor("", "", "XAUUSD")
        _, opt, sch = self._make_optimizer_scheduler()
        state = _make_state(batch_size=512)
        resp  = {"actions": {"2": {"batch_size": 256}}}
        sv.apply_actions(resp, state, opt, sch,
                          self._make_criterion_factory(),
                          lambda cols, names: [], [], None,
                          torch.device("cpu"), nn)
        assert state.batch_size == 256
        assert state.need_reload_loader is True

    def test_force_phoenix_sets_flag(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv    = LLMSupervisor("", "", "XAUUSD")
        _, opt, sch = self._make_optimizer_scheduler()
        state = _make_state()
        resp  = {"actions": {"2": {"action_type": "force_phoenix"}}}
        sv.apply_actions(resp, state, opt, sch,
                          self._make_criterion_factory(),
                          lambda cols, names: [], [], None,
                          torch.device("cpu"), nn)
        assert state.force_phoenix is True

    def test_invalid_lr_not_applied(self):
        from core.training.llm_supervisor import LLMSupervisor
        sv    = LLMSupervisor("", "", "XAUUSD")
        _, opt, sch = self._make_optimizer_scheduler()
        original_lr = opt.param_groups[0]["lr"]
        state = _make_state()
        # LR = 99 vượt giới hạn 1e-2
        resp  = {"actions": {"2": {"new_lr": 99.0}}}
        sv.apply_actions(resp, state, opt, sch,
                          self._make_criterion_factory(),
                          lambda cols, names: [], [], None,
                          torch.device("cpu"), nn)
        assert opt.param_groups[0]["lr"] == pytest.approx(original_lr)
