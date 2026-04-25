# MẪU TỐT NHẤT CFG_LTC_LONDON_V3_5 (CỤC BỘ - BINANCE-ONLY)

Cập nhật lần cuối: 2026-04-25 11:02

## Kết quả tốt nhất (Local - Binance only)

| Run ID | Score | Epoch | Thời điểm |
|---|---|---|---|
| `run_20260425_090914_v3_ldn_1` | **0.3003** | 36 | 2026-04-25 11:02 |

## Phân tích tín hiệu (Epoch 36)

| Ngưỡng | Win Rate | N tín hiệu | Buy | Sell | Cân bằng |
|---|---|---|---|---|---|
| @53% | 48.5% | 511 | 255 | 256 | ✅ 50:50 |
| **@57.3%** | **52.8%** | **250** | **125** | **125** | ✅ 50:50 |
| @61.7% | 46.5% | 101 | 50 | 51 | ✅ |
| @66% | 39.4% | 33 | 16 | 17 | ✅ |

## Config tốt nhất

```
BATCH_SIZE   : 64
LEARNING_RATE: 3e-5 (đang giảm dần, hiện ~1.5e-5 tại epoch 36)
WINDOW_SIZE  : 15
MACRO        : Binance-only (BTC/ETH/BCH/DOGE/XRP/SOL)
```

## Lịch sử cải thiện

| Epoch | Score | Ghi chú |
|---|---|---|
| 10 | 0.1518 | Khởi đầu tốt, Buy/Sell cân bằng |
| 22 | 0.2880 | Nhảy vọt lớn |
| 36 | **0.3003** | Vượt ngưỡng 0.30! |

## Ghi chú so sánh

- Baseline tốt nhất (có MT5): **0.4519** (`run_j`, LR=3e-5, BATCH=256, WINDOW=15)
- Local Binance-only hiện tại: **0.3003** — tương đương ~67% baseline MT5, vẫn đang tăng!
- Run NY tốt nhất local: **0.2201** (`run_aa`) — London đang vượt NY!
