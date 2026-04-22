
import time
import os
import re

log_file = "data/logs/trade_bot_master_20260420.log"
print("Waiting 30 seconds to collect data...")
time.sleep(30)

with open(log_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

print("\n--- PHÂN TÍCH LOG ---")
tensor_sums = []
mses = []
for line in lines[-100:]:
    if "[DEBUG DATA] Tensor Sum:" in line:
        print(line.strip())
        m = re.search(r"Sum: ([\d\.]+)", line)
        if m: tensor_sums.append(float(m.group(1)))
    elif "MSE_Loss=" in line:
        print(line.strip())
        m = re.search(r"MSE_Loss=([\d\.]+)", line)
        if m: mses.append(float(m.group(1)))

print("\n--- KẾT LUẬN ---")
print(f"Số lượng sum: {len(tensor_sums)}")
if len(tensor_sums) > 1:
    diff = max(tensor_sums) - min(tensor_sums)
    print(f"Chênh lệch cực đại Tensor Sum: {diff}")
else:
    print("Vui lòng đợi thêm log")

print(f"Số lượng MSE: {len(mses)}")
if len(mses) > 1:
    diff = max(mses) - min(mses)
    print(f"Chênh lệch cực đại MSE: {diff}")


