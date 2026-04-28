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

### 11. `run_20260428_222500_v4_ny_17`
- **Tham số thay đổi:** Cấu hình chuẩn New Baseline (Pure Macro, `TP=80`, `SL=80`, `MAX_HOLD_BARS=30`). Tinh chỉnh `WINDOW_SIZE` từ 20 lên 30.
- **Kỳ vọng:** Mở rộng tầm nhìn của não bộ từ 20 phút lên 30 phút để tương xứng với thời gian gồng lệnh 30 phút. Hy vọng tăng Composite Score.
- **Kết quả đạt được:** Thất bại. Điểm Composite Score sụt giảm thê thảm xuống **0.349**. Mặc dù Win Rate cao nhất vẫn giữ được ở mức ~59.7%, nhưng mô hình lại dự đoán ra số lượng tín hiệu khổng lồ (1215 tín hiệu ở mức Win Rate 50.2%). Việc nhìn quá khứ quá xa (30 phút) đã khiến mô hình bị nhiễu bởi các "con sóng cũ" và không thể tập trung vào momentum gần nhất của Baseline.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Mốc `WINDOW_SIZE=20` là điểm ngọt (sweet spot) tuyệt đối. Lượt tới (Run 18), ta quay về giữ nguyên 100% của Baseline 15. Lần này Pivot Strategy sang bộ Lọc Nhiễu Nhãn (Noise Filter): Bật `"ZERO_NOISE_TARGET": true`. Trong phiên NY, các pha giật râu quét cả 2 đầu (chạm cả TP và SL trong 30 phút) xảy ra rất thường xuyên. Việc dạy cho não bộ bỏ qua các nến giật 2 đầu này (xoá bỏ các nhãn nhiễu) có thể làm tín hiệu huấn luyện cực kỳ sắc bén.

### 12. `run_20260428_224500_v4_ny_18`
- **Tham số thay đổi:** Cấu hình chuẩn New Baseline (Pure Macro, `TP=80`, `SL=80`, `MAX_HOLD_BARS=30`, `WINDOW=20`). Bật tính năng `"ZERO_NOISE_TARGET": true`.
- **Kỳ vọng:** Bộ lọc nhiễu nhãn sẽ loại bỏ các chuỗi nến giật hai đầu (hit cả TP và SL), giúp mô hình tập trung 100% vào các con sóng một chiều thuần khiết. Hy vọng tăng độ chính xác (Win Rate) và Composite Score.
- **Kết quả đạt được:** Thất bại về mặt tối ưu hoá tổng thể. Mặc dù Win Rate thực tế rất tốt (60.2% - 61.7%), mô hình lại ngừng học (Early Stopping) ngay tại **Epoch 2** với Validation Loss rất cao (1.239). Việc loại bỏ quá nhiều dữ liệu nhiễu bằng `ZERO_NOISE_TARGET` đã khiến tập dữ liệu mất đi tính liên tục, làm mô hình không thể hội tụ đủ sâu. Điểm Composite Score do đó bị phạt nặng, chỉ còn **0.358**.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Việc giữ lại các nến nhiễu (`ZERO_NOISE_TARGET=false`) thực ra giúp mạng nơ-ron học được tính ngẫu nhiên của thị trường để tránh Overfitting. Lượt tới (Run 19), ta quay về 100% của Baseline 15. Lần này Pivot Strategy sang **Tinh chỉnh Kích thước Lô (Batch Size)**: Tăng `BATCH_SIZE` từ 512 lên **1024**. Việc tăng Batch Size giúp hướng đi của Gradient mượt mà hơn, tránh bị giật cục bởi các nến nhiễu đơn lẻ trong phiên NY, kỳ vọng giúp mô hình hội tụ tốt hơn.

### 13. `run_20260428_230500_v4_ny_19`
- **Tham số thay đổi:** Cấu hình chuẩn New Baseline (Pure Macro, `TP=80`, `SL=80`, `MAX_HOLD_BARS=30`, `WINDOW=20`). Tinh chỉnh `BATCH_SIZE` từ 512 lên 1024.
- **Kỳ vọng:** Tăng kích thước Batch Size giúp ổn định quá trình tối ưu hóa Gradient Descent, giảm thiểu tác động nhiễu từ các nến giật đơn lẻ, từ đó giúp mô hình tìm được Local Minima tốt hơn (tăng Composite Score).
- **Kết quả đạt được:** Một mô hình "Bắn tỉa" (Sniper) xuất hiện. Win Rate bùng nổ lên mức **66.6%** khi training hội tụ rất sâu ở Epoch 127. Tuy nhiên, việc Batch Size quá lớn đã triệt tiêu độ nhạy của mô hình, khiến nó trở nên cực kỳ bảo thủ. Số lượng tín hiệu dự đoán giảm sút nghiêm trọng (chỉ có 30 tín hiệu trong hơn 2 năm). Do đó, điểm Composite Score bị thuật toán phạt nặng, chỉ còn **0.390**.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Chúng ta cần một mô hình cân bằng giữa Tần suất và Win Rate. `BATCH_SIZE=512` đã được chứng minh là điểm cân bằng hoàn hảo. Lượt tới (Run 20), ta đưa về 100% của Baseline 15. Lần này Pivot Strategy sang **Kiến trúc Features**: Bật `"ORDER_FLOW": true` và `"VOL_REGIME": true`. Việc bổ sung cấu trúc khối lượng giao dịch và sự mất cân bằng luồng lệnh sẽ là vũ khí tối thượng để định vị dòng tiền "Smart Money" trong phiên New York.

### 14. `run_20260428_232500_v4_ny_20`
- **Tham số thay đổi:** Cấu hình chuẩn New Baseline (Pure Macro, `TP=80`, `SL=80`, `MAX_HOLD_BARS=30`, `WINDOW=20`). Bật `ORDER_FLOW=true` và `VOL_REGIME=true`.
- **Kỳ vọng:** Bộ siêu tính năng về Dòng Tiền (Order Flow/Volume) sẽ kết hợp cùng sức mạnh Vĩ mô (Macro) của New York để lọc bỏ các cú lừa (Fakeout) thiếu thanh khoản. Kỳ vọng Win Rate và Composite Score sẽ phá mốc kỷ lục 0.549.
- **Kết quả đạt được:** Thất bại thảm hại. Mặc dù Win Rate ở mức tín hiệu khắt khe đạt 65.1%, nhưng ở ngưỡng cơ bản, Win Rate sụp đổ xuống **47.1%** với một lượng tín hiệu khổng lồ (961 signals). Điều này chỉ ra rằng, dữ liệu Order Flow và Volume nội tại của XAG (Bạc) chứa đầy các lệnh thao túng rác (Spoofing) từ các thuật toán HFT, khiến mạng nơ-ron bị đánh lừa hoàn toàn. Điểm EV kéo lùi toàn bộ hệ thống, Composite Score tụt xuống **0.373**.
- **Quyết định tiếp theo:** Đã xoá bỏ run này. Khẳng định tuyệt đối: Trong phiên NY, "Pure Macro" (chỉ nhìn biến động tương quan của Vàng, Đô, Nasdaq) là kim chỉ nam đáng tin cậy nhất cho Bạc. Lượt tới (Run 21), do đã cạn ý tưởng tinh chỉnh vi mô, tôi quyết định tung ra **Chiến lược Hoàn Toàn Mới (Pivot Strategy: NY Long-Swing)**: Khôi phục cấu hình Pure Macro của Baseline 15, nhưng thay đổi triết lý gồng lệnh: Tăng thời gian `MAX_HOLD_BARS` từ 30 lên **60 phút** (1 giờ trọn vẹn). Phiên NY dài 4 tiếng, việc nới rộng thời gian Hold lên 1 tiếng sẽ cho phép xu hướng Vĩ mô có đủ thời gian để tiệm cận mốc TP=80 pips mà không bị Timeout cắt ngang.

### 15. `run_20260428_234500_v4_ny_21` (Đang tiến hành)
- **Tham số thay đổi:** Cấu hình chuẩn New Baseline (Pure Macro, `TP=80`, `SL=80`, `WINDOW=20`). Tinh chỉnh `MAX_HOLD_BARS` từ 30 lên 60.
- **Kỳ vọng:** Chuyển từ Short-Swing (30m) sang Long-Swing (60m). Cung cấp gấp đôi thời gian để lệnh chạy, tối đa hóa xác suất chạm được mốc TP=80 pips, giảm số lệnh bị đóng non do hết thời gian. Hy vọng thiết lập Baseline mới cho Composite Score.
- **Trạng thái:** Đang trong quá trình cào dữ liệu và chuẩn bị huấn luyện.
