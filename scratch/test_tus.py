import torch
from src.training_v3.evaluator_v3 import WinRateEvaluatorV3

# Tạo dummy signals cho 5 ngày (5 chunks, mỗi chunk 400 = 2000 mẫu)
# Ngày 1: 50 lệnh
# Ngày 2: 50 lệnh
# Ngày 3: 50 lệnh
# Ngày 4: 50 lệnh
# Ngày 5: 50 lệnh -> Đều tăm tắp
buy_mask_even = torch.zeros(2000, dtype=torch.bool)
for i in range(5):
    buy_mask_even[i*400 : i*400 + 50] = True
sell_mask = torch.zeros(2000, dtype=torch.bool)

tus_even = WinRateEvaluatorV3.calculate_distribution_penalty(buy_mask_even, sell_mask, chunk_size=400)
print(f"TUS Đều: {tus_even:.4f}")

# Ngày 1: 250 lệnh
# Ngày 2..5: 0 lệnh -> Co cụm
buy_mask_clustered = torch.zeros(2000, dtype=torch.bool)
buy_mask_clustered[0:250] = True

tus_clustered = WinRateEvaluatorV3.calculate_distribution_penalty(buy_mask_clustered, sell_mask, chunk_size=400)
print(f"TUS Co cụm: {tus_clustered:.4f}")

# Hơi co cụm: 200 lệnh ngày 1, 50 lệnh ngày 2
buy_mask_mild = torch.zeros(2000, dtype=torch.bool)
buy_mask_mild[0:200] = True
buy_mask_mild[400:450] = True

tus_mild = WinRateEvaluatorV3.calculate_distribution_penalty(buy_mask_mild, sell_mask, chunk_size=400)
print(f"TUS Hơi co cụm: {tus_mild:.4f}")
