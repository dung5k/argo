# MẪU TỐT NHẤT CFG_LTC_LONDON_V3_5 (CỤC BỘ - BINANCE-ONLY)

Cập nhật lần cuối: 2026-04-25 11:12

## Kết quả tốt nhất (Local - Binance only)

| Run ID | Score | Epoch | Thời điểm |
|---|---|---|---|
| `run_20260425_090914_v3_ldn_1` | **0.3095** | 48 | 2026-04-25 11:12 |

## Phân tích tín hiệu (Epoch 48)

| Ngưỡng | Win Rate | N tín hiệu | Buy | Sell | Cân bằng |
|---|---|---|---|---|---|
| @53% | 46.2% | 582 | 291 | 291 | ✅ 50:50 |
| **@57.7%** | **53.8%** | **273** | **136** | **137** | ✅ 50:50 |
| @62.3% | 43.4% | 113 | 56 | 57 | ✅ |
| @67% | 45.5% | 33 | 16 | 17 | ✅ |

## ⚠️ Cảnh báo — Epoch 49

Epoch 49: Val Score=0.290, Bias Sell xuất hiện (Bal=0.79). Cần theo dõi xem đây là dao động nhất thời hay bắt đầu overfit.

## Config tốt nhất

```
BATCH_SIZE   : 64
LEARNING_RATE: 3e-5 (đang ở ~1.88e-6 tại epoch 49, giai đoạn cuối)
WINDOW_SIZE  : 15
MACRO        : Binance-only (BTC/ETH/BCH/DOGE/XRP/SOL)
```

## Lịch sử cải thiện

| Epoch | Score | Ghi chú |
|---|---|---|
| 10 | 0.1518 | Khởi đầu, Buy/Sell cân bằng ngay |
| 22 | 0.2880 | Nhảy vọt |
| 36 | 0.3003 | Vượt ngưỡng 0.30 |
| 48 | **0.3095** | Kỷ lục mới, WR@57%=53.8% |

## Ghi chú so sánh

- Baseline tốt nhất (có MT5): **0.4519** (`run_j`, LR=3e-5, BATCH=256, WINDOW=15)
- Local Binance-only hiện tại: **0.3095** — tương đương ~69% baseline MT5
- Run NY tốt nhất local: **0.2201** (`run_aa`) — London đang vượt xa!
