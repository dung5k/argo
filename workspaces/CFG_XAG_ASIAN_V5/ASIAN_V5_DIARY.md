# 🏯 DIARY: AUTO-TUNING XAG ASIAN BRAIN V5 — REGIME-AWARE

## 🏆 BẢNG VÀNG THÀNH TÍCH V5 (QUY TẮC: TOP 3 HOẶC WR >= 80%)

| Run ID | Win Rate | Score | Đặc điểm |
|---|---|---|---|
| `run_20260508_asian_argo2_reinit` | 74.3% | **0.642** | Regime-Aware Reinit |
| `run_20260507_040000` | 73.8% | 0.626 | Layer Drop 0.2, Mean |
| `run_20260507_030000` | 61.7% | 0.562 | Baseline Asian V5 |

---

## 🧠 PHÂN TÍCH CHIẾN LƯỢC PHIÊN ASIAN (00:00-07:00 UTC)

### Đặc điểm thị trường:
1. **Thanh khoản mỏng:** XAG trong phiên Á thường dao động hẹp, dễ bị quét stop loss bởi các cú giật giả.
2. **Biến động Crypto Macro:** Chịu ảnh hưởng gián tiếp từ sự biến động của BTC/ETH trong khung giờ này.
3. **Mục tiêu:** Cần Win Rate cao (>65%) để bù đắp cho tần suất lệnh thấp.

---

### [2026-05-10 21:42] - Khởi chạy Run: run_20260510_214200_v5_asian_sniper_pulse
- **Ý tưởng:** "Asian Sniper Pulse"
- **Thay đổi:** 
    - `FAST_HIT_BARS = 5` (Giảm từ 8 để bắt sóng nhạy hơn).
    - `TP_PCT = 0.004 / SL_PCT = 0.003` (Tỷ lệ 1.33).
- **Giả thuyết:** Rút ngắn thời gian giữ lệnh sẽ giúp tránh các đợt đảo chiều không mong muốn trong phiên Á và tối ưu hóa lợi nhuận trên mỗi lệnh thắng.
