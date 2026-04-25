# MẪU TỐT NHẤT CFG_LTC_LONDON_V3_5 (CỤC BỘ - BINANCE-ONLY)

Cập nhật lần cuối: 2026-04-25 14:22

## Kết quả tốt nhất (Local - Binance only)

| Run ID | Score | Epoch | Thời điểm |
|---|---|---|---|
| `run_20260425_134218_v3_ldn_6` | **0.4086** | 9 | 2026-04-25 14:22 |

## Phân tích tín hiệu (Epoch 9) — KỶ LỤC TUYỆT ĐỐI MỚI!

| Ngưỡng | Win Rate | N tín hiệu | Buy | Sell | Cân bằng |
|---|---|---|---|---|---|
| **@53%** | **60.4%** 🔥 | **222** | **111** | **111** | ✅ 50:50 |
| **@54.3%** | **67.2%** 🔥 | **134** | **67** | **67** | ✅ 50:50 |
| **@55.7%** | **71.6%** 🔥 | **81** | **40** | **41** | ✅ 50:50 |
| **@57%** | **76.7%** 🔥 | **43** | **21** | **22** | ✅ 50:50 |

## ✨ Điểm đặc biệt — Tại sao đây là kết quả XUẤT SẮC NHẤT

- **WR@53% = 60.4%** — tỷ lệ thắng xuất sắc ngay ở ngưỡng thấp nhất
- **WR@57% = 76.7%** — kỳ lạ! Cứ 4 lệnh có 3 lệnh thắng!
- **Buy/Sell = 50:50 tuyệt đối ở MỌI ngưỡng** — không có bias nào
- **Chỉ Epoch 9** mà đã vượt mọi record trước đó!

## Config tốt nhất hiện tại

```
BATCH_SIZE   : 64
LEARNING_RATE: 1e-5  ← CHÌA KHÓA THEN CHỐT
D_MODEL      : 128   ← TĂNG GẤP ĐÔI
NUM_LAYERS   : 3     ← TĂNG TỪ 2 LÊN 3
WINDOW_SIZE  : 30    ← TỐI ƯU ĐÃ XÁC NHẬN
WARMUP_EPOCHS: 30
MACRO        : Binance-only (BTC/ETH/BCH/DOGE/XRP/SOL)
```

## Lịch sử cải thiện toàn bộ

| Run | D_MODEL | LR | WINDOW | Score | Epoch |
|---|---|---|---|---|---|
| ldn_1 | 64 | 3e-5 | 15 | 0.3095 | 48 |
| ldn_3 | 64 | 3e-5 | 30 | 0.3874 | 33 |
| ldn_5 | 128 | 3e-5 | 30 | 0.3255 | 10 |
| **ldn_6** | **128** | **1e-5** | **30** | **0.4086** 🥇 | **9** |

## Ghi chú so sánh

- Baseline tốt nhất (có MT5): **0.4519** (`run_j`, LR=3e-5, BATCH=256, WINDOW=15)
- Local Binance-only MỚI: **0.4086** — **90.6% của baseline MT5!** (từ 86% lên 90.6%!)
- **Combo vàng đã xác nhận:** D_MODEL=128 + LR=1e-5 + WINDOW=30
- Hướng tiếp theo: thử LR=5e-6 (giảm thêm) hoặc BATCH=32 hoặc TP_PCT adjustment
