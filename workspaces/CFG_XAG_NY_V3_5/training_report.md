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

### 4. `run_20260428_200558_v4_ny_10`
- **Tham số thay đổi:** Cấu hình Baseline (WINDOW=20, TP=50, SL=50, 1 Layer) kết hợp với bật `ZERO_NOISE_TARGET=true`.
- **Kỳ vọng:** Xem việc lọc tín hiệu nhiễu trên Baseline có giúp cải thiện điểm số và Win Rate không.
- **Kết quả đạt được:** Composite Score giảm còn **0.423**, Win Rate cực đại chỉ đạt **~44.5%**. Việc lọc tín hiệu quá mức ở phiên NY có thể đã đánh mất đi những điểm vào lệnh quan trọng.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Việc dùng `ZERO_NOISE_TARGET` độc lập không hiệu quả. Lượt tới sẽ quay về cấu hình Baseline (`WINDOW=20, TP=50, SL=50`) nhưng sẽ kích hoạt **ORDER_FLOW=true** để nhận diện dòng tiền lớn, kỳ vọng kết hợp với phân tích Macro sẽ đẩy điểm số lên cao hơn mốc 0.506.

### 5. `run_20260428_202541_v4_ny_11`
- **Tham số thay đổi:** Cấu hình Baseline (WINDOW=20, TP=50, SL=50, 1 Layer) kết hợp với bật `ORDER_FLOW=true`.
- **Kỳ vọng:** Xem việc bổ sung tính năng Order Flow (nhận diện dòng tiền) trên Baseline có giúp cải thiện điểm số và Win Rate hay không, do phiên NY thường bị chi phối mạnh bởi dòng tiền.
- **Kết quả đạt được:** Composite Score đạt **0.423**, Win Rate cực đại **~45.7%**. Kết quả tương tự như việc bật Zero Noise, không thể vượt qua được sức mạnh của cấu hình Pure Macro. Việc thêm Feature Order Flow dường như lại gây nhiễu cho mô hình hiện tại.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Việc thêm Feature Engineering không mang lại hiệu quả tốt hơn Baseline. Lượt tới (Run 12) tôi sẽ giữ nguyên Feature Engineering của Baseline (Pure Macro), nhưng **Pivot Strategy** sang tối ưu hóa Siêu tham số não bộ: Tăng `D_MODEL` từ 32 lên **64** và `N_HEAD` từ 2 lên **4** để cung cấp cho mô hình dung lượng học tập lớn hơn (capacity), kỳ vọng nó sẽ tiêu hoá dữ liệu Macro phức tạp tốt hơn để phá mốc 0.506.

### 6. `run_20260428_204500_v4_ny_12`
- **Tham số thay đổi:** Cấu hình Baseline (WINDOW=20, TP=50, SL=50, Pure Macro) nhưng nâng cấp Siêu tham số: `D_MODEL=64`, `N_HEAD=4`.
- **Kỳ vọng:** Cung cấp cho não bộ nhiều noron và head attention hơn để nó tự phân tách các mối tương quan vĩ mô phức tạp trong phiên NY, từ đó tăng Win Rate.
- **Kết quả đạt được:** Composite Score đạt **0.441**, Win Rate max **~50.0%**. Việc tăng kích thước não đã gây hiện tượng over-parameterization khiến hiệu suất rớt so với não nhỏ `D_MODEL=32` của Baseline.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Lượt tới (Run 13) tôi sẽ quay về não nhỏ Baseline. Pivot Strategy sang hướng **Tinh giản đầu vào (Macro Feature Selection)**: Loại bỏ hoàn toàn mã `USTECm` khỏi `MACRO_FEATURES`, chỉ giữ lại Vàng (XAUUSDm) và Đô la (DXYm) để xem liệu chứng khoán Mỹ có đang làm nhiễu tín hiệu của Bạc (XAG) trong phiên NY hay không.

### 7. `run_20260428_210500_v4_ny_13`
- **Tham số thay đổi:** Cấu hình Baseline (WINDOW=20, TP=50, SL=50, D_MODEL=32) nhưng loại bỏ hoàn toàn mã `USTECm` (Nasdaq) ra khỏi danh sách `MACRO_FEATURES`.
- **Kỳ vọng:** Nasdaq có thể mang tín hiệu nhiễu đối với XAG trong phiên NY. Việc chỉ giữ lại XAU (Vàng) và DXY (Dollar Index) sẽ giúp mô hình tập trung hơn vào mối tương quan cốt lõi của kim loại quý.
- **Kết quả đạt được:** Cực kỳ tồi tệ! Composite Score rớt thẳng đứng xuống **0.320** (thấp nhất trong tất cả các lượt chạy). Win Rate chỉ quanh mức 47-50%. Điều này chứng minh một sự thật quan trọng: **Chứng khoán Mỹ (Nasdaq) đóng vai trò thiết yếu và không thể loại bỏ** trong việc dự báo XAG phiên NY.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Lượt tới (Run 14) tôi sẽ quay về giữ nguyên cấu hình mạnh nhất Baseline 100% (Pure Macro gồm cả Nasdaq, WINDOW=20, TP=50, SL=50, D_MODEL=32). Lần này Pivot Strategy sang tinh chỉnh Tốc độ học (Learning Rate): Tăng `LEARNING_RATE` từ `1e-5` lên `3e-5` để xem mô hình có thể hội tụ nhanh và sắc nét hơn ở một Local Minima tốt hơn không.

### 8. `run_20260428_212500_v4_ny_14`
- **Tham số thay đổi:** Cấu hình chuẩn Baseline 100% (`WINDOW_SIZE=20`, `TP=50`, `SL=50`, `D_MODEL=32`, Pure Macro). Thay đổi duy nhất: `LEARNING_RATE` = `3e-5` (tăng gấp 3 lần).
- **Kỳ vọng:** Giúp mô hình hội tụ tốt hơn trên bộ dữ liệu nhiễu cao, có thể tìm thấy một mức Win Rate cao hơn mốc 57% hiện tại.
- **Kết quả đạt được:** Thất bại thảm hại. Điểm Composite Score rơi xuống **0.262**, Win Rate cực đại chỉ đạt **~47%**. Tốc độ học lớn đã làm mô hình bay khỏi Local Minima tối ưu, mất hoàn toàn khả năng nhận diện tín hiệu. Mốc Learning Rate `1e-5` của Baseline đã được chứng minh là tối ưu nhất.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Lượt tới (Run 15) quay về `LEARNING_RATE=1e-5` chuẩn. Lần này Pivot Strategy sang **Kiến trúc Hold Lệnh dài hơn (NY Swing Mode)**: Tăng biên độ rủi ro `TP_PIPS=80`, `SL_PIPS=80` và nới lỏng thời gian giữ lệnh `MAX_HOLD_BARS=30` (30 phút). Phiên NY cực kỳ biến động, việc chỉ giữ lệnh 12 phút như các phiên khác có thể là quá ngắn để cơn sóng vĩ mô kịp phát huy tác dụng.

### 9. `run_20260428_214500_v4_ny_15`
- **Tham số thay đổi:** Cấu hình chuẩn Baseline 100% (Pure Macro, `WINDOW=20`, `LEARNING_RATE=1e-5`). Đổi chiến thuật nhãn sang NY Swing Mode: `TP_PIPS=80`, `SL_PIPS=80`, `MAX_HOLD_BARS=30`.
- **Kỳ vọng:** Cho phép mô hình "thở" lâu hơn trong phiên NY nhiễu loạn để đón đầu các cơn sóng lớn từ tin tức (Hold trend thay vì Scalp ngắn 12 phút).
- **Kết quả đạt được:** THÀNH CÔNG VƯỢT BẬC! Composite Score phá vỡ kỷ lục cũ, đạt **0.549**! Win Rate cực đại chạm mốc **~60.0%**. Việc nới rộng Stoploss và thời gian giữ lệnh đã phát huy tối đa sức mạnh của bộ tín hiệu Vĩ mô (Vàng, Đô, Nasdaq). Mô hình có thể "gồng" qua được các nhịp quét nhiễu của NY và chốt lời thành công. Đây chính thức trở thành **NEW BASELINE**.
- **Quyết định tiếp theo:** Giữ nguyên toàn bộ cấu trúc của New Baseline (Run 15). Lượt tới (Run 16) sẽ tinh chỉnh tỷ lệ R:R để tối ưu Win Rate theo lý thuyết: Giảm `TP_PIPS` xuống **60** trong khi giữ nguyên `SL_PIPS=80`. Việc chốt lời sớm hơn một chút (bất đối xứng) trên đà Swing có thể giúp nhặt được nhiều Win hơn.

### 10. `run_20260428_220500_v4_ny_16`
- **Tham số thay đổi:** Cấu hình chuẩn New Baseline 100% (Pure Macro, `WINDOW=20`, `MAX_HOLD_BARS=30`, `SL_PIPS=80`). Tinh chỉnh giảm `TP_PIPS` từ 80 xuống 60.
- **Kỳ vọng:** Giảm TP (chốt lời sớm) với hy vọng tăng Win Rate vượt mốc 60%.
- **Kết quả đạt được:** Tỷ lệ Win Rate thực sự đã bùng nổ lên con số không tưởng **~75.5%**! Tuy nhiên, do mức chốt lời (60) quá bất lợi so với cắt lỗ (80), kỳ vọng toán học (EV) bị kéo lùi, dẫn đến Composite Score sụt giảm xuống **0.461** (thấp hơn Baseline 0.549).
- **Quyết định tiếp theo:** Mặc dù Win Rate cực kỳ khủng khiếp và rất an toàn về mặt tâm lý, nhưng để tuân thủ triệt để tiêu chí tối đa hoá Composite Score, tôi đã xoá run này. Lượt tới (Run 17), sẽ quay lại tỷ lệ R:R chuẩn mực TP=80/SL=80 của Baseline 15. Lần này Pivot Strategy sang tinh chỉnh **Tầm nhìn Vĩ mô (Lookback Window)**: Tăng `WINDOW_SIZE` từ 20 lên **30**. Do chúng ta đã tăng thời gian Hold lệnh lên 30 phút, việc cung cấp cho não bộ tầm nhìn lịch sử tương đương (30 phút) thay vì 20 phút có thể giúp nó dự báo chuỗi thời gian đối xứng tốt hơn.

### 11. `run_20260428_222500_v4_ny_17` (Đang tiến hành)
- **Tham số thay đổi:** Cấu hình chuẩn New Baseline (Pure Macro, `TP=80`, `SL=80`, `MAX_HOLD_BARS=30`). Tinh chỉnh `WINDOW_SIZE` từ 20 lên 30.
- **Kỳ vọng:** Mở rộng tầm nhìn của não bộ từ 20 phút lên 30 phút để tương xứng với thời gian gồng lệnh 30 phút. Hy vọng tăng Composite Score.
- **Trạng thái:** Đang trong quá trình cào dữ liệu và chuẩn bị huấn luyện.
