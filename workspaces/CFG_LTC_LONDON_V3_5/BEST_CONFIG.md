# MẪU TỐT NHẤT CFG_LTC_LONDON_V3_5 (CỤC BỘ - BINANCE-ONLY)

Cập nhật lần cuối: 2026-04-25 10:52

## Kết quả tốt nhất (Local - Binance only)

| Run ID | Score | Epoch | Thời điểm |
|---|---|---|---|
| `run_20260425_090914_v3_ldn_1` | **0.2880** | 22 | 2026-04-25 |

## Phân tích tín hiệu (Epoch 22)

| Ngưỡng | Win Rate | N tín hiệu | Buy | Sell | Cân bằng |
|---|---|---|---|---|---|
| @53% | 50.5% | 382 | 191 | 191 | ✅ 50:50 |
| **@56%** | **55.8%** | **224** | **112** | **112** | ✅ 50:50 |
| @59% | 48.1% | 106 | 53 | 53 | ✅ 50:50 |
| @62% | 27.3% | 33 | 16 | 17 | ✅ |

## Config tốt nhất

```
BATCH_SIZE   : 64
LEARNING_RATE: 3e-5 (giảm xuống 1.5e-5 tại Epoch 23)
WINDOW_SIZE  : 15
MACRO        : Binance-only (BTC/ETH/BCH/DOGE/XRP/SOL)
```

## Ghi chú so sánh

- Baseline tốt nhất (có MT5): **0.4519** (`run_j`, LR=3e-5, BATCH=256, WINDOW=15)
- Local Binance-only hiện tại: **0.2880** — tương đương ~64% của baseline MT5
- Run NY tốt nhất local: **0.2201** (`run_aa`) — London đang vượt NY!
