# ĐỊNH HƯỚNG CHIẾN LƯỢC VÀ KIẾN TRÚC HỆ THỐNG QTS-V7
*(Quantitative Trading System - Version 7)*

## 1. Tầm Nhìn Chiến Lược (Strategic Vision)
Phiên bản V7 được xây dựng với mục tiêu chuyển đổi từ mô hình "Học Tĩnh" (Static Learning) sang **"Học Liên Tục" (Continual Walk-Forward Learning)**. Thay vì đào tạo một bộ não duy nhất hy vọng nó sẽ chiến thắng thị trường mãi mãi, V7 chấp nhận sự thật rằng **thị trường luôn thay đổi (Concept Drift)**. 
Hệ thống liên tục tịnh tiến cửa sổ thời gian (Sliding Window), tự động quét lại các tham số tương quan (Dynamic Lag) và Fine-tune (tinh chỉnh) lại bộ não mỗi tuần.

## 2. Các Trụ Cột Kiến Trúc (Core Pillars)

### 2.1. Walk-Forward Continual Learning
- **Foundation Training (Đào tạo nền tảng)**: Khởi tạo bộ não ban đầu trên một tập dữ liệu lớn (ví dụ: 28 ngày).
- **Finetuning Sliding Window**: Tịnh tiến cửa sổ lên phía trước (ví dụ: 7 ngày). Bộ não sử dụng trọng số từ tuần trước để học nhẹ nhàng (Learning rate rất nhỏ) các mẫu hình mới của tuần này. Nhờ đó, AI không bao giờ bị lỗi thời.

### 2.2. Dynamic Lags & Cross-Asset Correlation
- Sử dụng nhiều tài sản dẫn dắt (Leader Symbols như BTCUSD, ETHUSD) để dự đoán tài sản mục tiêu (Follower Symbol như LTCUSD).
- Áp dụng thuật toán Cross-Correlation để tìm ra **độ trễ động (Dynamic Lag)** tốt nhất tại mỗi chặng thay vì fix cứng một độ trễ cố định.

### 2.3. AI-Driven Hyperparameter Optimization
- Tích hợp mô hình Ngôn ngữ Lớn (LLM - Gemini) vào thẳng vòng lặp Backtest. 
- Sau mỗi chặng đánh giá, hệ thống gửi báo cáo (Win Rate, Profit Factor, PnL) cho AI. AI sẽ đóng vai trò như một chuyên gia tài chính để đề xuất điều chỉnh siêu tham số (TP, SL, Max Hold Bars) cho chặng tiếp theo.

## 3. Triết Lý Chống Quá Khớp (Anti-Overfitting Philosophy)
Dữ liệu tài chính, đặc biệt là nến M1, chứa 99% là nhiễu (Noise). Nếu ép mô hình Machine Learning học quá sâu, nó sẽ thuộc lòng nhiễu và phá sản khi ra thực tế. 
Phiên bản V7 áp dụng các biện pháp phẫu thuật thuật toán khắt khe nhất:

1. **Validation Early Stopping**: Quyết định dừng huấn luyện **TUYỆT ĐỐI** dựa trên Validation Loss (Tập dữ liệu chưa từng thấy), không dựa trên Training Loss.
2. **Ép Buộc Vượt Ngưỡng Trì Trệ (Minimum Epochs)**: Bắt buộc mô hình phải học tối thiểu 20 Epochs đầu tiên để tránh việc kích hoạt Early Stopping quá sớm do tín hiệu mờ nhạt ban đầu.
3. **CrossEntropy + Class Weights**: Phạt nặng mô hình nếu nó "lười biếng" chỉ đoán 1 chiều (Hold) bằng trọng số cân bằng lớp. (Loại bỏ Focal Loss vì Focal Loss ép mô hình học các cây nến đột biến - vốn dĩ đa phần là nhiễu).
4. **L2 Regularization (Weight Decay)**: Sử dụng chuẩn 1e-4 để giữ trọng số mạng nơ-ron không bị bùng nổ, nhưng cũng không bị triệt tiêu hoàn toàn về 0.
5. **Đánh Giá Lũy Kế (Cumulative Evaluation)**: Một bộ não chỉ được coi là thành công nếu Lợi nhuận Ròng (Cumulative PnL) của nó **ổn định và dương xuyên suốt toàn bộ vòng lặp Walk-Forward**, nghiêm cấm việc đánh giá chắp vá từng tuần đơn lẻ.

---
*V7 là sự kết hợp giữa Deep Learning, Phân tích Lượng tử và Trí tuệ Nhân tạo Tạo sinh, hướng tới một cỗ máy giao dịch lạnh lùng, khách quan và không ngừng tiến hóa.*
