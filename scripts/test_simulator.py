import os
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

sys.stdout.reconfigure(encoding='utf-8')

from src.simulator.historical_simulator import HistoricalSimulator
from src.simulator.backtest_vtm import BacktestVirtualTradeManager

class MockInferenceEngine:
    def __init__(self, num_features=999):
        self.num_features = num_features
        self.call_count = 0

    def predict(self, tensor):
        self.call_count += 1
        # Bắn lệnh BUY cứng ở nến thứ 10, đóng lệnh/đảo chiều SELL ở nến 30
        if self.call_count == 10:
            return "BUY", 0.05, {"buy": 0.8, "sell": 0.1, "hold": 0.1}
        elif self.call_count == 30:
            return "SELL", 0.05, {"buy": 0.1, "sell": 0.8, "hold": 0.1}
        return "HOLD", 0.01, {"buy": 0.3, "sell": 0.3, "hold": 0.4}

class DeterministicSimulator(HistoricalSimulator):
    def _ensure_engine(self):
        """OVERRIDE: Đánh chặn quá trình load AI thật, nhét con MockEngine vào"""
        self.log("🔧 INJECTING MOCK INFERENCE ENGINE...")
        self._engine = MockInferenceEngine()

# Khi chạy test:
if __name__ == "__main__":
    sim = DeterministicSimulator(config_path="data/bot_config_xag_asian_v5.json", model_path="mocked")
    sim.run("2026-05-14", "asian")
