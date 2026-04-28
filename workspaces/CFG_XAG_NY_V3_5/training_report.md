# Báo cáo Đào tạo (Training Report) - CFG_XAG_NY_V3_5

Tài liệu này ghi lại tóm tắt nội dung và kết quả của các lượt tối ưu (auto-tuning) để dễ dàng theo dõi toàn bộ quá trình phát triển chiến lược cho phiên New York.

### 1. `run_20260428_131755_v4_ny_auto`
- **Tham số thay đổi:** Pure Macro (không dùng Order Flow, Vol Regime), `WINDOW_SIZE=20`, `TP=50, SL=50`, 1 Layer Transformer.
- **Kết quả đạt được:** Composite Score đạt **0.506**, Win Rate **~57.1%**. Đây là một cột mốc Baseline rất tốt.
- **Quyết định tiếp theo:** Test thử thu hẹp TP và tăng SL để xem có tăng Win Rate và Composite Score lên thêm không.

### 2. `run_20260428_135751_v4_ny_auto`
- **Tham số thay đổi:** Giảm `WINDOW_SIZE` xuống 15. Cấu hình TP/SL thành `TP=40, SL=60`.
- **Kết quả đạt được:** Composite Score giảm còn **0.410**. Win Rate cao nhất ở ngưỡng 0.59 là **~58.8%**. Mặc dù thấp hơn run trước đó, nhưng vẫn vượt qua mức Baseline 0.396 cũ.
- **Quyết định tiếp theo:** Điểm số giảm khi hạ Window và thay đổi RR, do đó cần thiết kế một cấu hình hoàn toàn mới để đột phá.

### 3. `run_20260428_085920_v4_ny_9`
- **Tham số thay đổi:** Bật `ZERO_NOISE_TARGET=true`, `ORDER_FLOW=true`, `VOL_REGIME=true`. Tăng `WINDOW_SIZE=30` và giữ `TP=40, SL=60`.
- **Kỳ vọng:** Lọc nhiễu hiệu quả hơn và bắt kịp dòng tiền để tăng Win Rate trong phiên NY biến động.
- **Kết quả đạt được:** Composite Score rớt thảm hại xuống **0.326**. Việc thay đổi quá nhiều tham số cùng lúc khiến mô hình nhiễu loạn hoặc Overfit.
- **Quyết định tiếp theo:** Đã xoá bỏ run này khỏi ổ cứng. Lượt tới sẽ quay về thông số Baseline (`WINDOW=20, TP=50, SL=50`) và **chỉ bật duy nhất** `ZERO_NOISE_TARGET=true` để thực hiện A/B Testing chính xác.

### 4. `run_20260428_200558_v4_ny_10` (Đang tiến hành)
- **Tham số thay đổi:** Cấu hình Baseline (WINDOW=20, TP=50, SL=50, 1 Layer) kết hợp với bật `ZERO_NOISE_TARGET=true`.
- **Kỳ vọng:** Xem việc lọc tín hiệu nhiễu trên Baseline có giúp cải thiện điểm số và Win Rate không.
- **Trạng thái:** Đang trong quá trình cào dữ liệu và chuẩn bị huấn luyện.
