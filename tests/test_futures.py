import os
import sys

print("Khởi chạy test futures!")
from src.core.mt5_data_manager import MT5DataManager
from src.core.sync_historical_data import sync_all_history

# Tạo manager instance test
config = {
    "IS_CFD": False,
    "PREFIX": "Z10Y",
    "CONTRACT_MONTHS": ["H", "M", "U", "Z"]
}
manager = MT5DataManager(log_callback=print, target_sym="XAUUSD")

from datetime import datetime
print("Testing active month for 2026-03-15:")
print(manager.get_front_month_contract(config, datetime(2026, 3, 15))) # Expected: Z10YM26

print("Testing active month for 2026-08-10:")
print(manager.get_front_month_contract(config, datetime(2026, 8, 10))) # Expected: Z10YU26

print("Testing active month for 2026-12-01:")
print(manager.get_front_month_contract(config, datetime(2026, 12, 1))) # Expected: Z10YH27

print("\nChạy thử sync historical data cho symbol mới (10Y Yield & NASDAQ).")
os.environ['TEST_MODE_LIMIT'] = "1"
# Đổi số bars trong code gốc rất cao nên để chạy nhanh cần mock.
