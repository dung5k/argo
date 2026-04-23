# MÔ TẢ CẤU HÌNH CFG_LTC_ASIAN_V3_5

File này lưu trữ những mô tả cho AI về cấu hình tốt nhất của CFG_LTC_ASIAN_V3_5.

## Nguồn gốc

Kế thừa từ **CFG_LTC_LONDON_V3_5 / run_20260423_183500_v3_j** — run tốt nhất London:
- CompositeScore: **0.4519** (cao nhất)
- WinRate tại threshold 0.63: **71.60%** (162 signals)
- Epoch tốt nhất: 8 (hội tụ nhanh, ít overfit)

## Thay đổi so với London (v3_j)

### Kiến trúc (giữ nguyên từ v3_j):
- D_MODEL=64, N_HEAD=4, NUM_LAYERS=2
- LEARNING_RATE=3e-05, BATCH_SIZE=256

### Điều chỉnh cho Asian session (00:00–07:00 UTC):
| Tham số | London (v3_j) | Asian (base) | Lý do |
|---|---|---|---|
| WINDOW_SIZE | 15 | 20 | Volume thấp, cần context dài hơn |
| MAX_HOLD_BARS | 10 | 12 | Asian ít volatile, nến hội tụ chậm hơn |
| WARMUP_EPOCHS | 20 | 15 | Dataset Asian nhỏ hơn London |
| FREQ_MIN_N | 100 | 80 | Ít tín hiệu hơn trong đêm |
| FREQ_MAX_N | 600 | 500 | Cùng lý do |

### Thay đổi MACRO_FEATURES:
| Symbol | London | Asian | Lý do |
|---|---|---|---|
| USTECm | log_ret | **XÓA** | Thị trường Mỹ đóng cửa |
| DXYm | log_ret | **XÓA** | DXY ít biến động đêm châu Á |
| XRPUSDT | ❌ | **log_ret, volume** | XRP tương quan mạnh với LTC trong phiên châu Á |
| ETHUSDT | log_ret, volume | log_ret, volume, **corr_60** | ETH dẫn dắt thị trường crypto đêm mạnh hơn |
| BTCUSDT | log_ret, bb_width, volume, corr_60 | **giữ nguyên** | BTC là trục chính |
| XAUUSDm | log_ret | **giữ nguyên** | Gold châu Á vẫn active |
