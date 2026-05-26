# 🇺🇸 DIARY: AUTO-TUNING XAG NEW YORK BRAIN V5 — REGIME-AWARE

## 🏆 BẢNG VÀNG THÀNH TÍCH V5 (QUY TẮC: TOP 3 HOẶC WR >= 80%)

| Run ID | Win Rate | Score | Đặc điểm |
|---|---|---|---|
| `run_20260510_140500` | **88.6%** | **0.8595** | Stable Sniper (NEW WORLD RECORD) |
| `run_20260508_171500` | **96.7%** | **0.8425** | Deep Scalp L4 (Former Record) |
| `run_20260508_230000` | **80.6%** | **0.7877** | Sniper LS 0.25 |
| `run_20260508_200000` | **88.0%** | 0.750 | Anti-Overfit (Gamma 3, LS 0.2), 29 feat |
| `run_20260507_253000` | **86.7%** | 0.725 | Macro RSI/Mom, JPY anchor |
| `run_20260508_083000` | **84.8%** | 0.735 | Nitro Overdrive, WD 0.05 |
| `run_20260507_264500` | **82.5%** | **0.760** | Nitro Impulse FHB=5 |
| `run_20260508_073000` | **81.2%** | 0.734 | Nitro Overdrive (LR 2e-5) |
| `run_20260507_243000` | **80.0%** | 0.712 | Macro Plus (JPY anchor) |
| `run_20260508_210000` | 75.0% | 0.750 | Sniper TP6/SL3 |
| `run_20260508_203000` | 77.4% | 0.692 | Stability Anti-Overfit |
| `run_20260508_223000` | 65.1% | 0.632 | Sniper Stable FHB=8 |

---

## 🧠 PHÂN TÍCH CHIẾN LƯỢC PHIÊN NEW YORK (13:00-19:00 UTC)

### Đặc điểm thị trường:
1. **Biến động (Volatility) cực cao:** New York là phiên sôi động nhất, đặc biệt là khi mở cửa (13:00-14:30 UTC).
2. **Đảo chiều giả (Liquidity Sweeps):** Thường xuyên có các đợt quét đỉnh/đáy của phiên London trước khi thiết lập xu hướng thật.
3. **Phản ứng tin tức:** Các chỉ số kinh tế Mỹ (CPI, NFP) tạo ra những cây nến "râu dài" gây nhiễu cho mô hình nếu không có bộ lọc tốt.

### Đề xuất Ý tưởng Tối ưu hóa (Run tiếp theo):
- **Tên ý tưởng:** "Nitro Precision Nano Pulse"
- **Thay đổi:** 
    - Thử nghiệm `FAST_HIT_BARS = 5` để bắt sóng cực nhanh, tránh kẹt trong các đợt đảo chiều muộn.
    - Duy trì `TP/SL = 0.6/0.4` (bắt chước hiệu quả của LTC).
    - Loại bỏ hoàn toàn nhiễu từ JPY/DXY, chỉ tập trung vào mỏ neo Vàng (`XAUUSDm`).
    - Tăng cường Regularization (`Label Smoothing = 0.3`) để chống học vẹt các cú giật giá.

---

### [2026-05-10 14:23] - Đánh giá Run: run_20260510_140500_v5_ny_stable_sniper
- **Kết quả:** Composite Score = **0.8595** (KỶ LỤC MỚI) | Best WR = 88.6% | Early Stop @ Epoch 172.
- **Phân tích:** Tỷ lệ Buy/Sell đạt trạng thái cân bằng lý tưởng (28B/29S). Việc giảm D_MODEL xuống 64 và tăng Focal Gamma lên 5.0 đã chứng minh là "chìa khóa" để giải quyết bài toán bias và overfitting. 
- **Ý tưởng mới:** "Legacy Sniper" - Duy trì cấu hình Stable nhưng tăng FHB lên 10 để bắt các sóng dài hơn, tăng độ ổn định cho lệnh Live.
- **Giả thuyết:** Độ trễ cao hơn sẽ lọc bỏ các cú nhiễu cuối phiên, duy trì WR trên 80% với số lệnh thực tế cao hơn.

---

### [2026-05-10 14:05] - Đánh giá Run: run_20260510_135600_v5_ny_nitro_pulse
- **Kết quả:** Composite Score = 0.488 | Best WR = 50% (N=44) | Early Stop @ Epoch 95.
- **Vấn đề phát hiện:** Xuất hiện Buy Bias cực nặng ở các epoch cuối (222B/14S). FHB=5 có vẻ quá gấp gáp, khiến mô hình chỉ bắt được các sóng xu hướng ngắn hạn mà bỏ qua chất lượng lệnh.
- **Ý tưởng mới:** "Stable Sniper" - Quay lại FHB=8, giảm D_MODEL xuống 64 để tăng tính tổng quát, và tăng Focal Gamma lên 5.0 để trừng phạt lỗi bias.
- **Giả thuyết:** Giảm dung lượng não và tăng độ khó của Loss sẽ giúp mô hình lọc nhiễu tốt hơn và cân bằng tỷ lệ Buy/Sell.

---

### [2026-05-10 13:56] - Khởi động lại hệ thống sau đợt dọn dẹp tổng thể
- **Trạng thái:** Hoàn thành run đầu tiên. Score đạt 0.488.
- **Mục tiêu:** Tiếp tục tối ưu hóa để vượt ngưỡng 0.60.

---

### [2026-05-26 22:00:00] - Đánh giá Toàn cục (State 0) & Khởi chạy Run: run_20260526_220000_v5_ny_liquidity_shield
- **Đánh giá Toàn cục:** Kết quả huấn luyện của cả 3 phiên XAG V5 cho thấy: London V5 (Score 20.9032) và Asian V5 (Score 5.0062) đều đã thiết lập kỷ lục vô địch thế giới mới. Phiên New York V5 hiện tại (Score 0.8595) đang là điểm yếu nhất và lệch pha nghiêm trọng so với hai phiên còn lại. Hệ thống quyết định chọn New York làm tiêu điểm tối ưu hóa vòng này.
- **Ý tưởng cải tiến tối thượng (New York Liquidity Shield):**
  - **Lọc nhiễu vĩ mô tối giản:** Kế thừa thành tựu của London và Asian, loại bỏ hoàn toàn Crypto (BTC, ETH) khỏi `MACRO_FEATURES`, chỉ neo chặt vào cặp đôi Vàng (`XAUUSDm`) và DXY (`DXYm`).
  - **Lá chắn thanh khoản (Liquidity Shield):** Ở phiên Mỹ, volatility cực cao và Market Maker liên tục tung ra các cú quét thanh khoản giả (liquidity sweeps) đảo chiều mạnh mẽ. SL=0.0040 ở baseline cũ quá chật khiến AI dễ bị quét sạch. Quyết định tăng `SL_PCT` lên **0.0060** (60 pips) và giữ `TP_PCT` ở mức **0.0045** (45 pips) làm lá chắn thép cho lệnh.
  - **Mở rộng cơ hội & Bắt sóng dài:** Đẩy `FAST_HIT_BARS` lên **10** (từ 5) để bắt trọn sóng, đồng thời nới `MSE_GATE_PERCENTILE` lên **0.08** (từ 0.0) để tăng số lượng lệnh chất lượng thực tế (N).
  - **Bảo vệ phần cứng cực hạn:** Đặt `BATCH_SIZE` = **32** và chạy hoàn toàn trên **CPU** (`CUDA_VISIBLE_DEVICES="-1"`) với `OMP_NUM_THREADS=1` và `MKL_NUM_THREADS=1` để triệt tiêu lỗi Virtual Memory OOM trên máy local.
- **Giả thuyết:** Khoảng đệm SL 0.0060 rộng rãi kết hợp cổng lọc MSE 0.08 và FHB=10 sẽ giải phóng sức mạnh của mạng Transformer D128-L3, giúp lệnh sống sót vững vàng qua các pha giật giá của phiên Mỹ và công phá mục tiêu TP 0.0045, nâng Composite Score vượt mốc 2.0.
