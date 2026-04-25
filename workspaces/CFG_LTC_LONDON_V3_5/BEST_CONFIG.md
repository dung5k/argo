# MẪU TỐT NHẤT CFG_LTC_LONDON_V3_5 (CỤC BỘ - BINANCE-ONLY)

Cập nhật lần cuối: 2026-04-25 12:22

## Kết quả tốt nhất (Local - Binance only)

| Run ID | Score | Epoch | Thời điểm |
|---|---|---|---|
| `run_20260425_115216_v3_ldn_3` | **0.3870** | 27 | 2026-04-25 12:22 |

## Phân tích tín hiệu (Epoch 27) — KỶ LỤC TUYỆT ĐỐI MỚI!

| Ngưỡng | Win Rate | N tín hiệu | Buy | Sell | Cân bằng |
|---|---|---|---|---|---|
| @53% | 48.6% | 455 | 227 | 228 | ✅ 50:50 |
| **@57.7%** | **50.4%** | **280** | **140** | **140** | ✅ 50:50 |
| **@62.3%** | **54.6%** | **130** | **65** | **65** | ✅ 50:50 |
| **@67%** | **66.7%** | **30** | **15** | **15** | ✅ 50:50 |

## ✨ Điểm đặc biệt — Tại sao đây là kết quả xuất sắc nhất

- **WR@67% = 66.7%** — tỷ lệ thắng CỰC KỲ cao ở ngưỡng tin cậy cao nhất
- **WR@62% = 54.6%** — vượt 50% đáng kể, có lợi thế thống kê mạnh
- **Buy/Sell cân bằng hoàn hảo TẤT CẢ ngưỡng** — không có bias nào
- **Epoch 27** đã đạt Score=0.387 (ldn_1 cần đến Epoch 48 mới đạt 0.310!)

## Config tốt nhất

```
BATCH_SIZE   : 64
LEARNING_RATE: 3e-5 (đang ở ~7.5e-6 tại epoch 28)
WINDOW_SIZE  : 30  ← CHÌA KHÓA THÀNH CÔNG
MACRO        : Binance-only (BTC/ETH/BCH/DOGE/XRP/SOL)
```

## Lịch sử cải thiện toàn bộ

| Run | BATCH | WINDOW | Score tốt nhất | Epoch |
|---|---|---|---|---|
| ldn_1 | 64 | 15 | 0.3095 | 48 |
| ldn_2 | 128 | 15 | 0.1931 | 13 |
| **ldn_3** | **64** | **30** | **0.3870** 🥇 | **27** |

## Ghi chú so sánh

- Baseline tốt nhất (có MT5): **0.4519** (`run_j`, LR=3e-5, BATCH=256, WINDOW=15)
- Local Binance-only: **0.3870** — tương đương **86% baseline MT5** (từ 69% lên 86%!)
- **WINDOW=30, BATCH=64 là combo vàng** cho phiên London Binance-only
- Hướng tiếp theo: thử WINDOW=60 để xem có cải thiện thêm không
