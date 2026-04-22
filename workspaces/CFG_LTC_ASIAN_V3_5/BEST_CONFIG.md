# BÁO CÁO CẤU HÌNH TỐI ƯU NHẤT (BEST CONFIG) - LTC ASIAN BRAIN

Dựa trên quá trình Auto-Tuning và phân tích toán học Định lượng, đây là tài liệu mô tả về cấu hình đã được tối ưu hóa cho phiên Á (Asian Session) của cặp giao dịch `LTCUSDT` (`CFG_LTC_ASIAN_V3_5`).

## 1. Triết Lý Lọc Nhiễu (Noise Cancellation)
Trong môi trường thanh khoản mỏng của phiên Á, dòng tiền Crypto mang tính nội bộ cao và thường luân chuyển chéo giữa các Altcoin lớn (LTC, DOGE, BCH, ETH) và Bitcoin. Việc sử dụng các chỉ số hệ thống toàn cầu như Vàng hay Tỷ giá Dollar không đem lại giá trị dự đoán mà ngược lại tạo *"ảo giác suy luận"* (overfitting noise) cho mô hình.

- **Vectơ Đặc Trưng (Input Channels):** Đã tinh giản từ 39 chiều xuống **36 chiều**. 
- **Loại bỏ Macro:** `DXYm` (US Dollar Index) và `XAUUSDm` (Vàng) đã bị lọc vĩnh viễn khỏi chuỗi cấp liệu đầu vào.

## 2. Các Tham Số Giao Dịch Định Lượng (Hyperparameters)
Cấu trúc quản trị lệnh đã được mở rộng nhằm tạo không gian thở cho lệnh trong một thị trường đi ngang:

- **WINDOW_SIZE (30 phút):** Tăng từ 20 lên 30. Mô hình giờ đây nhìn về quá khứ tận 30 phút để thiết lập Momentum chắc chắn, tránh các ngọn nến bẫy (wicks) ngắn hạn.
- **MAX_HOLD_BARS (15 phút):** Tăng sức gồng lệnh từ 10 thành 15 phút. Nới lỏng không gian thời gian để các xung lực nhỏ từ từ đạt đến mức TP (0.3%).
- **Tỷ lệ RR (TP/SL):** Cố định ở mốc 0.3% / 0.3%. Lựa chọn tỷ lệ này được chốt hạ sau khi khảo sát hàm Loss nhằm duy trì Expected Value (Kỳ vọng) dương.

## 3. Khuyến nghị Kế thừa Mô hình
- Quá trình training hiện tại (với 36 Input channels) đã được đánh giá vượt trội hơn nhiều so với phiên bản chứa DXY/XAU trước đó. 
- Mọi client mới khi join vào quá trình training hoặc inference cần pull bản cấu hình này. Hệ thống Tensor của model mới không tương thích với trọng số mô hình cũ (39 channels).
