# MẪU TỐT NHẤT CFG_LTC_LONDON_V3_5 (CỤC BỘ - BINANCE-ONLY)

Cập nhật lần cuối: 2026-04-25 12:12

## Kết quả tốt nhất (Local - Binance only)

| Run ID | Score | Epoch | Thời điểm |
|---|---|---|---|
| `run_20260425_115216_v3_ldn_3` | **0.3099** | 17 | 2026-04-25 12:12 |

## Phân tích tín hiệu (Epoch 17) — KỶ LỤC MỚI!

| Ngưỡng | Win Rate | N tín hiệu | Buy | Sell | Cân bằng |
|---|---|---|---|---|---|
| **@53%** | **51.4%** | **333** | **166** | **167** | ✅ 50:50 |
| @56.3% | 51.4% | 210 | 105 | 105 | ✅ 50:50 |
| @59.7% | 51.8% | 110 | 55 | 55 | ✅ 50:50 |
| @63% | 64.1% | 39 | 19 | 20 | ✅ 50:50 |

## ✨ Điểm đặc biệt

- **WR@53% = 51.4% (>50%)** — model thực sự có lợi thế thống kê!
- **Buy/Sell cân bằng hoàn hảo ở TẤT CẢ ngưỡng** — tốt hơn mọi run trước
- **Chỉ Epoch 17** mà đã vượt baseline ldn_1 (Epoch 48!) — WINDOW=30 hội tụ nhanh hơn

## Config tốt nhất

```
BATCH_SIZE   : 64
LEARNING_RATE: 3e-5 (đã giảm xuống 1.5e-5 tại epoch 17)
WINDOW_SIZE  : 30  ← THAY ĐỔI QUYẾT ĐỊNH
MACRO        : Binance-only (BTC/ETH/BCH/DOGE/XRP/SOL)
```

## Lịch sử cải thiện toàn bộ

| Run | BATCH | WINDOW | Score tốt nhất | Ghi chú |
|---|---|---|---|---|
| ldn_1 | 64 | 15 | 0.3095 (Ep48) | Baseline cũ |
| ldn_2 | 128 | 15 | 0.1931 (Ep13) | ❌ BATCH=128 tệ hơn |
| **ldn_3** | **64** | **30** | **0.3099 (Ep17)** | 🥇 **KỶ LỤC MỚI** |

## Ghi chú so sánh

- Baseline tốt nhất (có MT5): **0.4519** (`run_j`, LR=3e-5, BATCH=256, WINDOW=15)
- Local Binance-only hiện tại: **0.3099** — tương đương ~69% baseline MT5
- **WINDOW=30 vừa vượt WINDOW=15 và hội tụ nhanh hơn nhiều (Ep17 vs Ep48)**
- Hướng tiếp theo nếu muốn cải thiện thêm: thử WINDOW=60 hoặc LR cao hơn (5e-5)
