# XAG London V3.5 - Auto-Tuning Report

Báo cáo tiến trình tối ưu hóa bộ não `CFG_XAG_LDN_V3_5` cho phiên London.

## Lịch sử Auto-Tuning

### Khởi động lại kỷ nguyên mới (Dựa trên Thánh Giá NY)
Cấu trúc cũ của London (D32, Layer 2, TP/SL=30/30) đã đem lại kết quả rất tệ ở Run 27 (Composite Score 0.258). Kể từ Run 28, tôi quyết định áp dụng nguyên vẹn triết lý thiết kế đã thành công vang dội ở phiên NY:
- Kiến trúc đơn giản: `D_MODEL=16`, `NUM_LAYERS=1`
- Lọc nhiễu tối đa: `BATCH_SIZE=512`, `LR=1e-05`
- Tầm nhìn: `WINDOW=20`
- Pure Macro: Loại bỏ USTECm, chỉ dùng XAUUSDm và DXYm. Loại bỏ các chỉ báo rườm rà (chop_14, bb_zscore).
- Tỷ lệ Lợi nhuận: Do London dao động hẹp hơn NY, thay vì 80/80, tôi set `TP=50, SL=50` (Tỷ lệ 1:1).

---
# XAG London V3.5 - Auto-Tuning Report

Báo cáo tiến trình tối ưu hóa bộ não `CFG_XAG_LDN_V3_5` cho phiên London.

## Lịch sử Auto-Tuning

### Khởi động lại kỷ nguyên mới (Dựa trên Thánh Giá NY)
Cấu trúc cũ của London (D32, Layer 2, TP/SL=30/30) đã đem lại kết quả rất tệ ở Run 27 (Composite Score 0.258). Kể từ Run 28, tôi quyết định áp dụng nguyên vẹn triết lý thiết kế đã thành công vang dội ở phiên NY:
- Kiến trúc đơn giản: `D_MODEL=16`, `NUM_LAYERS=1`
- Lọc nhiễu tối đa: `BATCH_SIZE=512`, `LR=1e-05`
- Tầm nhìn: `WINDOW=20`
- Pure Macro: Loại bỏ USTECm, chỉ dùng XAUUSDm và DXYm. Loại bỏ các chỉ báo rườm rà (chop_14, bb_zscore).
- Tỷ lệ Lợi nhuận: Do London dao động hẹp hơn NY, thay vì 80/80, tôi set `TP=50, SL=50` (Tỷ lệ 1:1).

---

### 1. `run_20260429_081500_v4_ldn_28` (Đã hoàn thành)
- **Tham số thay đổi:** Thiết lập Baseline mới (D16, W20, TP/SL 50/50, B512).
- **Kỳ vọng:** Kiến trúc siêu việt của phiên NY sẽ chứng minh sức mạnh của nó trên phiên London.
- **Trạng thái:** THẤT BẠI THẢM HẠI. Mô hình không tìm thấy đủ số lượng tín hiệu (N < 40) nên Composite Score bị đánh giá là 0.0. Nguyên nhân: Biên độ TP/SL=50/50 pips là quá rộng so với thanh khoản của phiên London, kết hợp với Window=20 quá chậm khiến mô hình không dám vào lệnh. Thư mục run 28 đã bị xóa để tiết kiệm dung lượng.

### 2. `run_20260429_090000_v4_ldn_29` (Đã hoàn thành)
- **Tham số thay đổi:** Giảm `TP_PIPS` = 30, `SL_PIPS` = 30. Giảm `WINDOW_SIZE` = 15.
- **Kỳ vọng:** Do phiên London có biên độ dao động hẹp hơn NY, việc thu hẹp khoảng cách TP/SL xuống 30 pips và giảm Window xuống 15 phút (phản ứng nhanh hơn) sẽ giúp mô hình "bắt mạch" được nhiều tín hiệu hơn, đồng thời vẫn kế thừa được sức mạnh của bộ não D16 Pure Macro.
- **Trạng thái:** Hoàn thành. Composite Score: 0.252 (Rất thấp). Win Rate chỉ đạt tối đa 47.6%. Mặc dù đã giảm biên độ TP/SL xuống 30/30 pips giúp số lượng tín hiệu tăng lên đáng kể (84 lệnh hợp lệ), nhưng độ chính xác lại nằm dưới mức hòa vốn (50%). Kết luận: Việc chỉ sử dụng dữ liệu vĩ mô tĩnh (Macro) cho phiên London là KHÔNG ĐỦ, vì phiên này bị chi phối nhiều bởi dòng tiền ngắn hạn và thiếu xu hướng dẫn dắt rõ ràng.

### 3. `run_20260429_091500_v4_ldn_30` (Đang tiến hành)
- **Tham số thay đổi:** Bật `ORDER_FLOW=true`, `VOL_REGIME=true`, `ZERO_NOISE_TARGET=true`. Thêm lại `USTECm` vào bộ Macro.
- **Kỳ vọng:** Để bù đắp điểm yếu của dữ liệu Macro tĩnh trong môi trường sideway của London, mô hình sẽ được cung cấp thêm luồng Order Flow (động lượng khối lượng) và Volatility Regime (chế độ biến động) nội tại của XAGUSD. Bộ lọc Zero Noise sẽ chặn các tín hiệu quét hai đầu. Kỳ vọng độ chính xác (Win Rate) sẽ vượt mốc 55%!
- **Trạng thái:** Đang chuẩn bị dữ liệu và huấn luyện.
