# Nháº­t kÃ½ Huáº¥n luyá»n XAG Asian V5 - Regime-Aware

## ð Báº£ng VÃ ng ThÃ nh TÃ­ch V5 (Top 3)
| Run ID | Win Rate | Score | Đặc điểm |
|---
### [2026-05-19 22:44:00] - TỐI ƯU MOMENTUM & CO THẮT BIÊN ĐỘ (ALPHA SNIPER): run_20260519_224600_v5_asian_alpha_momentum_sniper
- **Kết quả:** Composite Score = **0.5324** | Win Rate = **55.56%** | Early Stopped ở Epoch **99**
- **Trạng thái:** Hoàn tất training và đã sync lên HuggingFace HUB.
- **Phân tích chi tiết & Insight tối cao:**
  - **Lý giải kết quả:** Việc thử nghiệm tăng `TP_PCT` lên 0.0035 và nới rộng `FAST_HIT_BARS=5` trong môi trường thanh khoản siêu mỏng và yên ắng của phiên Á đã làm tăng số lượng lệnh kẹt và dính SL do co thắt biên độ ngắn hạn (volatility squeeze). Win Rate dừng lại ở mức 55.56%, không vượt qua được Champion run `run_20260511_102100_v5_asian_ultimate_sniper` (WR 86.67%).
  - **Kết luận hành động:** Giữ nguyên cấu hình vô địch **`run_20260511_102100_v5_asian_ultimate_sniper`** (Score **0.7840** | Win Rate **86.67%**) làm Champion chính thức cho phiên Asian V5!

---

### [2026-05-11 03:12] - Đánh giá Run: run_20260511_022400_v5_asian_pure_focus
- **Kết quả:** Composite Score = **0.7250** | Best WR = 76.74% | Early Stop @ Epoch 170.
- **Vấn đề phát hiện:** THÀNH CÔNG VƯỢT BẬC. Việc loại bỏ nhiễu Crypto (BTC, ETH) đã chứng minh tính đúng đắn tuyệt đối cho phiên Á. Win Rate tăng vọt lên gần 77%, Score vượt ngưỡng 0.70. Đây là Baseline mới cho phiên Asian.
- **Ý tưởng mới:** "Asian Sniper Calibration" - Giữ nguyên bộ đặc trưng Pure Focus (XAU macro). Thử nghiệm tăng `TP_PCT` lên 0.0040 (từ 0.0035) để tối ưu hóa lợi nhuận trên mỗi nhịp sòng. Giữ nguyên cấu hình D160-L3.
- **Giả thuyết:** Với độ chính xác 76%, việc nới rộng TP một chút sẽ giúp tăng Score đáng kể mà không làm giảm WR quá nhiều.

---
|---|---|---|
| `run_20260511_022400_v5_asian_pure_focus` | 76.7% | **0.725** | Pure Focus XAU |
| `run_20260511_002900_v5_asian_scalper_precision` | 71.4% | 0.699 | Record Break D160 |
| `run_20260508_asian_argo2_reinit` | 74.3% | 0.642 | Regime-Aware Reinit |

---

### [2026-05-11 00:33] - ÄÃ¡nh giÃ¡ Run: run_20260511_002900_v5_asian_scalper_precision
- **Káº¿t quáº£:** Composite Score = **0.6999** | Best WR = 71.43% | Early Stop @ Epoch 106.
- **Váº¥n Äá» phÃ¡t hiá»n:** Ká»¶ Lá»¤C Má»I ÄÆ¯á»¢C THIáº¾T Láº¬P! Viá»c tÄng `D_MODEL` lÃªn 160 giÃºp máº¡ng xá»­ lÃ½ cá»±c tá»t cá»­a sá» 45 náº¿n. Win Rate vÆ°á»£t ngÆ°á»¡ng 70% á» cÃ¡c threshold cao. ÄÃ¢y chÃ­nh lÃ  cáº¥u hÃ¬nh "Sniper" mÃ  chÃºng ta tÃ¬m kiáº¿m.
- **Ã tÆ°á»ng má»i:** "Asian Elite Sniper" - Giá»¯ nguyÃªn cÃ¡c tham sá» ká»· lá»¥c. Thá»­ nghiá»m `POOLING=attention` thay vÃ¬ `mean` Äá» táº­p trung vÃ o cÃ¡c náº¿n Äá»t biáº¿n (volatility spikes) trong 45 náº¿n. TÄng `FOCAL_GAMMA` lÃªn 4.0.
- **Giáº£ thuyáº¿t:** Vá»i ná»n táº£ng Score 0.70, cÆ¡ cháº¿ Attention sáº½ giÃºp mÃ´ hÃ¬nh "báº¯n" chÃ­nh xÃ¡c hÆ¡n ná»¯a vÃ o cÃ¡c thá»i Äiá»m then chá»t cá»§a phiÃªn Ã.

---

### [2026-05-11 00:28] - ÄÃ¡nh giÃ¡ Run: run_20260511_002500_v5_asian_scalper_pivot
- **Káº¿t quáº£:** Composite Score = **0.6268** | Best WR = 64.86% | Early Stop @ Epoch 110.
- **Váº¥n Äá» phÃ¡t hiá»n:** THÃNH CÃNG Lá»N. Viá»c káº¿t há»£p `FAST_HIT_BARS=7` vÃ  `WINDOW_SIZE=45` ÄÃ£ mang láº¡i hiá»u suáº¥t vÆ°á»£t trá»i, tiá»m cáº­n má»©c ká»· lá»¥c cao nháº¥t (0.642). Cá»­a sá» 45 náº¿n dÆ°á»ng nhÆ° ÄÃ£ lá»c bá» hiá»u quáº£ cÃ¡c vÃ¹ng dá»¯ liá»u pháº³ng khÃ´ng cÃ³ xu hÆ°á»ng.

---

### [2026-05-11 00:14] - ÄÃ¡nh giÃ¡ Run: run_20260511_000500_v5_asian_fresh_rebuild
- **Káº¿t quáº£:** Composite Score = **0.6055** | Best WR = 65.62% | Early Stop @ Epoch 209.
- **Váº¥n Äá» phÃ¡t hiá»n:** Viá»c lÃ m sáº¡ch toÃ n bá» workspace vÃ  quay láº¡i tham sá» máº·c Äá»nh (`WINDOW_SIZE=60`, `FHB=8`) ÄÃ£ mang láº¡i sá»± á»n Äá»nh rÃµ rá»t.

---

### [2026-05-11 01:23] - Ðánh giá Run: run_20260511_003400_v5_asian_elite_sniper
- **K?t qu?:** Composite Score = **0.4307** | Best WR = 47.13% | Early Stop @ Epoch 108.
- **V?n d? phát hi?n:** TH?T B?I. Co ch? ttention và FOCAL_GAMMA=4.0 không mang l?i hi?u qu? nhu k? v?ng, trái l?i làm gi?m m?nh Score. Có v? mean pooling v?n là l?a ch?n t?i uu nh?t d? ?n d?nh tín hi?u trong phiên Á bi?n d?ng th?p.
- **Ý tu?ng m?i:** "Asian Deep Sniper" - Quay l?i c?u hình k? l?c (Mean pooling, Focal 2.0). Tang chi?u sâu m?ng lên LAYERS=4 (t? 3) và D_MODEL=192. Si?t LABEL_SMOOTHING xu?ng 0.05.
- **Gi? thuy?t:** V?i c?a s? 45 n?n, m?t m?ng sâu hon và r?ng hon có th? h?c du?c các m?u hình vi mô tinh vi hon mà m?ng 3 l?p b? l?.

---

### [2026-05-11 01:27] - ÄÃ¡nh giÃ¡ Run: run_20260511_012400_v5_asian_deep_sniper
- **Káº¿t quáº£:** Composite Score = **0.6957** | Best WR = 71.13% | Early Stop @ Epoch 72.
- **Váº¥n Äá» phÃ¡t hiá»n:** Hiá»u suáº¥t ráº¥t cao nhÆ°ng khÃ´ng vÆ°á»£t qua ÄÆ°á»£c ká»· lá»¥c (0.699). Viá»c tÄng thÃªm Äá» sÃ¢u (4 lá»p) vÃ  Äá» rá»ng (192) báº¯t Äáº§u cÃ³ dáº¥u hiá»u bÃ£o hÃ²a vÃ  overfit sá»m hÆ¡n (Epoch 72). Vá»i táº­p dá»¯ liá»u 11.8k, cáº¥u hÃ¬nh D160-L3 váº«n lÃ  tá»i Æ°u nháº¥t.
- **Ã tÆ°á»ng má»i:** "Asian Hybrid Loss" - Quay láº¡i cáº¥u hÃ¬nh ká»· lá»¥c D160-L3. Thá»­ nghiá»m tÄng `mse_gate` lÃªn 0.2 vÃ  giáº£m `LEARNING_RATE` xuá»ng 3e-5.
- **Giáº£ thuyáº¿t:** Ãp mÃ´ hÃ¬nh há»c song song cáº£ classification vÃ  regression (mse_gate) cháº·t cháº½ hÆ¡n sáº½ giÃºp lá»c bá» cÃ¡c tÃ­n hiá»u "biÃªn" (marginal signals), tá»« ÄÃ³ cÃ´ng phÃ¡ ngÆ°á»¡ng 0.75.

---

### [2026-05-11 02:23] - Ðánh giá Run: run_20260511_012800_v5_asian_hybrid_loss
- **K?t qu?:** Composite Score = **0.5006** | Best WR = 56.67% | Early Stop @ Epoch 82.
- **V?n d? phát hi?n:** Hi?u su?t gi?m m?nh. Vi?c tang MSE_GATE lên 0.2 làm mô hình quá t?p trung vào sai s? h?i quy, làm loãng kh? nang phân lo?i xu hu?ng. T?c d? h?c 3e-5 cung có v? quá ch?m, khi?n mô hình b? k?t ? các c?c ti?u d?a phuong.
- **Ý tu?ng m?i:** "Asian Pure Focus" - Quay l?i c?u hình k? l?c D160-L3. Th? nghi?m lo?i b? các mã Macro không liên quan (XRP, BCH, DOGE) d? gi?m nhi?u, ch? gi? l?i XAU và DXY làm tham chi?u Macro. Gi? LABEL_SMOOTHING=0.08.
- **Gi? thuy?t:** Trong phiên Á, các d?ng Crypto ít ?nh hu?ng d?n XAG hon so v?i phiên M?. Vi?c lo?i b? chúng s? giúp AI t?p trung vào các d?c tính thu?n túy c?a kim lo?i quý.

---

### [2026-05-11 03:17] - Đánh giá Run: run_20260511_031300_v5_asian_sniper_calibration
- **Kết quả:** Composite Score = 0.6337 | Best WR = 66.67% | Early Stop @ Epoch 131.
- **Vấn đề phát hiện:** Hiệu suất giảm so với bản Pure Focus. Việc nới TP lên 0.0040 khiến lệnh phải giữ lâu hơn trong phiên Á flat, làm tăng rủi ro đảo chiều và giảm Win Rate. Điểm 0.0035 vẫn là "TP Vàng" cho Sniper.
- **Ý tưởng mới:** "Asian Entropy Shield" - Quay lại cấu hình kỷ lục (Pure Focus, TP 0.0035). Thử nghiệm tăng cường Regularization: `WEIGHT_DECAY=0.0005` và `LABEL_SMOOTHING=0.10`.
- **Giả thuyết:** Với Win Rate 76%, mô hình có thể đang hơi overfit vào một số pattern cụ thể. Việc tăng regularization sẽ giúp mô hình bền bỉ hơn qua các tháng khác nhau trong bộ Val.

---

### [2026-05-11 03:32] - Đánh giá Run: run_20260511_031800_v5_asian_entropy_shield
- **Kết quả:** Composite Score = 0.4537 | Best WR = 46.67% | Early Stop @ Epoch 82.
- **Vấn đề phát hiện:** THẤT BẠI. Việc tăng cường Regularization quá mạnh đã phá hủy các đặc trưng tinh vi mà mô hình kỷ lục bắt được. Phiên Á cần sự nhạy bén cực cao, over-regularization làm mô hình trở nên "mù quáng".
- **Ý tưởng mới:** "Asian Micro Pulse" - Quay lại cấu hình kỷ lục. Thử nghiệm rút ngắn `WINDOW_SIZE` xuống 30 (từ 45) để AI phản ứng nhanh hơn với các nhịp "đập" của thị trường. Giữ nguyên Pure Focus và D160-L3.
- **Giả thuyết:** Trong môi trường thanh khoản mỏng, các mẫu hình 30 nến (30 phút) có thể chứa ít nhiễu hơn và phản ánh momentum hiện tại chính xác hơn 45 nến.

---

### [2026-05-11 04:32] - Đánh giá Run: run_20260511_033300_v5_asian_micro_pulse
- **Kết quả:** Composite Score = 0.6817 | Best WR = 68.29% | Early Stop @ Epoch 118.
- **Vấn đề phát hiện:** Hiệu suất tốt nhưng không vượt qua được kỷ lục WS=45. Cửa sổ 30 nến có vẻ hơi ngắn để AI nhận diện đầy đủ bối cảnh thị trường ngay cả trong phiên Á flat. 45 nến vẫn là "điểm ngọt" về Lookback.
- **Ý tưởng mới:** "Asian Steady Sniper" - Quay lại cấu hình kỷ lục (WS45, Pure Focus). Thử nghiệm tăng `BATCH_SIZE` lên 512 (từ 256) để làm mượt gradient và ổn định quá trình hội tụ. Giảm `LABEL_SMOOTHING` xuống 0.06.
- **Giả thuyết:** Với tập dữ liệu cực sạch (Pure Focus), việc tăng batch size sẽ giúp mô hình học các đặc trưng ổn định hơn, tránh các nhịp nhiễu cục bộ trong batch nhỏ.

---

### [2026-05-11 04:35] - Đánh giá Run: run_20260511_043300_v5_asian_steady_sniper
- **Kết quả:** Composite Score = 0.5434 | Best WR = 57.45% | Early Stop @ Epoch 70.
- **Vấn đề phát hiện:** THẤT BẠI. Việc tăng Batch Size lên 512 làm mượt gradient quá mức, khiến mô hình bỏ lỡ các pattern sắc nét. Giảm Smoothing xuống 0.06 cũng làm mô hình kém linh hoạt hơn. BATCH_SIZE=256 và Smoothing=0.08 vẫn là cấu hình chuẩn.
- **Ý tưởng mới:** "Asian Precision Drift" - Quay lại cấu hình kỷ lục (Pure Focus, BS256). Thử nghiệm giảm `LEARNING_RATE` xuống 5e-6 (từ 1e-5) để mô hình hội tụ chậm và sâu hơn vào các cực tiểu địa phương chất lượng cao.
- **Giả thuyết:** Với tập dữ liệu mỏng của phiên Á, tốc độ học chậm hơn sẽ giúp mô hình "thấm" dần các đặc trưng mà không bị lướt qua các điểm tối ưu.

---

### [2026-05-11 05:32] - Đánh giá Run: run_20260511_043600_v5_asian_precision_drift
- **Kết quả:** Composite Score = 0.5482 | Best WR = 58.06% | Early Stop @ Epoch 168.
- **Vấn đề phát hiện:** THẤT BẠI. Việc giảm Learning Rate xuống 5e-6 không giúp mô hình hội tụ tốt hơn mà trái lại làm mô hình bị kẹt ở các vùng loss cao quá lâu. 1e-5 vẫn là tốc độ học cân bằng nhất cho kiến trúc D160-L3.
- **Ý tưởng mới:** "Asian Core Sniper" - Thu hẹp khung giờ giao dịch xuống 01:00 - 06:00 UTC (bỏ 1 tiếng đầu và 1 tiếng cuối phiên). Giữ nguyên cấu hình kỷ lục.
- **Giả thuyết:** Giờ mở cửa (00:00) thường có spread cao và gap nhiễu, giờ cuối phiên (06:00) bắt đầu chịu ảnh hưởng từ London pre-market. Việc tập trung vào "lõi" của phiên Á sẽ giúp AI bắt được các pattern ổn định nhất.

---

### [2026-05-11 05:44] - Đánh giá Run: run_20260511_053300_v5_asian_core_sniper
- **Kết quả:** Composite Score = 0.5881 | Best WR = 61.54% | Early Stop @ Epoch 74.
- **Vấn đề phát hiện:** Việc thu hẹp session quá mức (01:00-06:00) làm giảm số lượng mẫu huấn luyện, khiến mô hình khó học được các pattern tổng quát. Khung giờ 00:00-07:00 vẫn cung cấp đủ dữ liệu nền tảng tốt nhất.
- **Ý tưởng mới:** "Asian Deep Pure Focus" - Kết hợp kiến trúc sâu (D192, L4) với bộ đặc trưng Pure Focus (XAU macro).
- **Giả thuyết:** Trước đây kiến trúc D192-L4 bị loãng do nhiễu Crypto. Với tập dữ liệu Pure Focus cực sạch, kiến trúc sâu hơn có thể khai thác được các tương quan phức tạp hơn để công phá ngưỡng Score 0.75.

---

### [2026-05-11 06:32] - Đánh giá Run: run_20260511_054500_v5_asian_deep_pure_focus
- **Kết quả:** Composite Score = 0.5629 | Best WR = 57.53% | Early Stop @ Epoch 62.
- **Vấn đề phát hiện:** THẤT BẠI. Kiến trúc sâu D192-L4 gây ra hiện tượng overfit nhanh chóng ngay cả với dữ liệu Pure Focus. Độ phức tạp cao không mang lại lợi thế trên tập dữ liệu phiên Á vốn đòi hỏi sự tinh gọn. D160-L3 vẫn là kiến trúc tối ưu nhất.
- **Kết luận Phase:** Sau chuỗi thực nghiệm toàn diện, cấu hình kỷ lục Score 0.725 (Run 022400) được xác định là điểm bão hòa của V5.
- **Hướng đi tiếp theo:** Đóng gói bản kỷ lục làm Baseline cho sản xuất. Chuẩn bị cho V6 với các đặc trưng kỹ thuật mới nếu cần công phá ngưỡng 0.75.

---

### [2026-05-11 09:32] - Đánh giá Run: run_20260511_083500_v5_asian_robust_baseline
- **Kết quả:** Composite Score = **0.4028** | Best WR = 44.10% | Early Stop @ Epoch 111.
- **Vấn đề phát hiện:** THẤT BẠI THẢM HẠI. Tập dữ liệu mở rộng 12k mẫu (bao gồm tháng 05/2026) cho thấy cấu hình "Pure Focus" (chỉ dùng Vàng) không có khả năng tổng quát hóa. Việc thiếu các biến số vĩ mô khác khiến mô hình bị mù quáng trước các thay đổi regime của tháng 5.
- **Ý tưởng mới:** "Asian Diverse Sniper" - Quay lại tập dữ liệu 12k. Đưa các mã Crypto (BTC, ETH) quay trở lại bộ đặc trưng Macro để làm "màng lọc" bối cảnh thị trường toàn cầu. Tăng `LABEL_SMOOTHING` lên 0.10.
- **Giả thuyết:** Trong bối cảnh dữ liệu lớn và nhiễu hơn, việc đa dạng hóa đầu vào macro sẽ giúp mô hình nhận diện được các regime rủi ro cao để né tránh, từ đó cải thiện WR trên tập Val mới.

---

### [2026-05-11 10:14] - Đánh giá Run: run_20260511_093300_v5_asian_diverse_sniper
- **Kết quả:** Composite Score = **0.7405** | Best WR = **84.38%** | Epoch 209.
- **Vấn đề phát hiện:** THÀNH CÔNG VƯỢT BẬC. Việc đưa các mã Crypto quay trở lại không chỉ giúp mô hình lấy lại độ ổn định mà còn đẩy hiệu suất lên một tầm cao mới. Win Rate 84% là con số "trong mơ" cho một mô hình Sniper phiên Á.
- **Kết luận:** Bộ đặc trưng Đa dạng (Diverse) là thiết yếu cho tập dữ liệu dài hạn. Đây chính thức là Bản Kỷ Lục Vàng mới của V5.
- **Ý tưởng mới:** "Asian Ultimate Sniper" - Giữ nguyên cấu hình Diverse. Thử nghiệm tăng nhẹ `WARMUP_EPOCHS` lên 30 và giảm `mse_gate` xuống 0.05 để AI tập trung hơn nữa vào độ chính xác phân loại.

---

### [2026-05-11 10:23] - Đánh giá Run: run_20260511_102100_v5_asian_ultimate_sniper
- **Kết quả:** Composite Score = **0.7840** | Best WR = **86.67%** | Epoch 39.
- **Vấn đề phát hiện:** THÀNH CÔNG RỰC RỠ. Việc áp dụng `MSE Gate 0.05` đã chứng minh sức mạnh trong việc lọc nhiễu. Mô hình chỉ học từ những mẫu dữ liệu "chuẩn mực" nhất, dẫn đến Win Rate tăng vọt lên 86.6%.
- **Kết luận:** Đây chính thức là Đỉnh Cao của V5. Không cần tối ưu thêm hyperparameter, trọng tâm tiếp theo nên là Feature Engineering cho V6 nếu muốn vượt ngưỡng 0.80.
- **Hành động:** Đóng gói bản Ultimate này làm cấu hình sản xuất vĩnh viễn cho Phase V5.

---
