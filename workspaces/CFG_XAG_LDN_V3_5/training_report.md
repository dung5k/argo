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

### 3. `run_20260429_091500_v4_ldn_30` (Đã hoàn thành)
- **Tham số thay đổi:** Bật `ORDER_FLOW=true`, `VOL_REGIME=true`, `ZERO_NOISE_TARGET=true`. Thêm lại `USTECm` vào bộ Macro.
- **Kỳ vọng:** Để bù đắp điểm yếu của dữ liệu Macro tĩnh trong môi trường sideway của London, mô hình sẽ được cung cấp thêm luồng Order Flow (động lượng khối lượng) và Volatility Regime (chế độ biến động) nội tại của XAGUSD. Bộ lọc Zero Noise sẽ chặn các tín hiệu quét hai đầu. Kỳ vọng độ chính xác (Win Rate) sẽ vượt mốc 55%!
- **Trạng thái:** Hoàn thành. Composite Score: 0.247. Win Rate cao nhất đạt 48.7%. Việc bổ sung Microstructure và Nasdaq không giúp cải thiện tình hình, chứng tỏ thị trường London quá nhiễu và những features này không mang lại Alpha.

### 4. `run_20260429_093000_v4_ldn_31` (Đã hoàn thành)
- **Tham số thay đổi:** Nâng `WINDOW_SIZE` từ 15 lên 60. Lọc bỏ hoàn toàn `DXYm` và `USTECm`, chỉ giữ duy nhất `XAUUSDm` (Vàng) làm Macro Feature.
- **Kỳ vọng:** Loại bỏ tối đa nhiễu từ các thị trường không hoạt động mạnh trong phiên London. Việc nới rộng tầm nhìn (Window=60) kết hợp với duy nhất tương quan Vàng-Bạc (XAU-XAG) hy vọng sẽ giúp mô hình nhìn ra được trend dài hạn của phiên thay vì bị nhiễu bởi các dao động siêu ngắn.
- **Trạng thái:** Hoàn thành. Composite Score: 0.274. Win Rate cao nhất: 48.9%. Đây là một bước tiến RẤT LỚN (phá vỡ kỷ lục Baseline cũ 0.258). Việc nới rộng tầm nhìn lên 60 phút và cắt giảm nhiễu Macro đã giúp nơ-ron hoạt động mượt mà hơn, tránh bị nhiễu bởi noise ngắn hạn.

### 5. `run_20260429_094500_v4_ldn_32` (Đã hoàn thành)
- **Tham số thay đổi:** Nâng `WINDOW_SIZE` từ 60 lên 90.
- **Kỳ vọng:** Do việc tăng Window từ 15 lên 60 đã giúp tăng Composite Score đáng kể (từ 0.247 lên 0.274), giả thuyết đặt ra là phiên London dao động rất chậm chạp. Việc nới rộng tầm nhìn lên 90 phút (1 tiếng rưỡi) sẽ giúp bộ não D16 nhìn thấy toàn bộ hành vi giá của thị trường kể từ lúc mở cửa phiên Frankfurt, từ đó củng cố độ chính xác và đưa Win Rate vượt mốc 50% hòa vốn.
- **Trạng thái:** THẤT BẠI THẢM HẠI. Mô hình hoàn toàn mất phương hướng và không dám đưa ra bất kỳ dự đoán nào (Composite Score 0.0, N=0 tín hiệu). Cửa sổ 90 nến là quá dài đối với bộ não nhỏ bé D16, khiến tín hiệu hoàn toàn bị "loãng" vào nhiễu. Thư mục đã bị xóa.

### 6. `run_20260429_100000_v4_ldn_33` (Đang tiến hành)
- **Tham số thay đổi:** Hạ `WINDOW_SIZE` về lại mốc lý tưởng 60. Thu hẹp biên độ `TP_PIPS` = 20, `SL_PIPS` = 20.
- **Kỳ vọng:** Quay về với "điểm ngọt" Window 60. Việc giảm biên độ ăn/thua xuống 20 pips sẽ chuyển đổi chiến thuật thành Micro-Scalping (ăn mỏng, cắt nhanh), hoàn toàn phù hợp với môi trường sideway chậm chạp của London. Kỳ vọng Win Rate sẽ chính thức vượt xa mốc 50% để sinh lời dương.
- **Trạng thái:** Đang chuẩn bị dữ liệu và huấn luyện.
