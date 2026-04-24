# MÃ TỐT NHẤT CFG_LTC_NY_V3_5

File này lưu trữ mốc baseline (Composite Score tốt nhất) để AI so sánh và quyết định hướng tuning tiếp theo.

---

## 🏆 BASELINE HIỆN TẠI

- **Run ID:** `run_20260423_115300_v3_u`
- **Composite Score:** `0.3758`
- **Epoch đạt điểm tốt nhất:** 7
- **Val Loss:** 0.9150
- **Win Rate @0.53:** 51.3% (5644 signals, Buy:Sell = 2822:2822 — cân bằng hoàn hảo)
- **Win Rate @0.6633:** 55.3% (497 signals)
- **Ngày đạt:** 2026-04-23

## 📋 Config tốt nhất (key params)

```json
{
  "TRAINING": {
    "LEARNING_RATE": 0.0001,
    "BATCH_SIZE": 256,
    "WARMUP_EPOCHS": 20,
    "D_MODEL": 64,
    "NUM_LAYERS": 3
  },
  "MACRO_FEATURES": {
    "BTCUSDT": ["log_ret", "bb_width", "volume", "corr_60"],
    "ETHUSDT": ["log_ret", "volume"],
    "BCHUSDT": ["log_ret"],
    "DOGEUSDT": ["log_ret", "volume"],
    "DXYm": ["log_ret"],
    "XRPUSDT": ["log_ret", "volume"],
    "SOLUSDT": ["log_ret", "volume"],
    "DXY": ["log_ret", "bb_width"],
    "USTEC": ["log_ret", "volume"]
  }
}
```

## 🔑 Key learnings

| Thay đổi | Tác động |
|---|---|
| LR: 0.0001 → 5e-5 | Score giảm từ 0.3758 → 0.166 (tệ hơn) |
| Bỏ BCHUSDT/DOGEUSDT, thêm BNBUSDT | Tín hiệu giảm mạnh (5644 → 41 signals) |
| WARMUP: 20 → 25 | Chưa đủ dữ liệu để kết luận |

## 🚨 Ghi chú Kỹ thuật Máy Cục Bộ (QUAN TRỌNG)

- **MT5 EXNESS không chạy được headless** trên máy này → Mọi MACRO_FEATURES dùng `DXYm`, `USTECm`, `DXY`, `USTEC` đều sẽ FAIL khi crawl/upload
- **Chỉ dùng BINANCE symbols** cho MACRO_FEATURES trong môi trường local: BTCUSDT, ETHUSDT, BCHUSDT, DOGEUSDT, XRPUSDT, SOLUSDT, BNBUSDT

## ⚠️ Thử nghiệm cần tránh lặp lại

- **KHÔNG giảm LR xuống 5e-5** khi chưa cải thiện features — đã thất bại ở run `_x`
- **KHÔNG bỏ BCHUSDT/DOGEUSDT** — 2 altcoin này có tương quan cao với LTC, là leading indicator quan trọng
