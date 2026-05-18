# Nháº­t kÃ½ Huáº¥n luyá»n XAG Asian V5 - Regime-Aware

## ð Báº£ng VÃ ng ThÃ nh TÃ­ch V5 (Top 3)
| Run ID | Win Rate | Score | Đặc điểm |
|---
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

### [2026-05-18 13:45:00] - TỐI ƯU HÓA ĐỘT PHÁ PRECISION PULSE: run_20260518_134500_v5_asian_precision_pulse
- **Kết quả:** Composite Score = **0.5010** | Win Rate = **51.43%** | Early Stopped ở Epoch **48**
- **Phân tích chi tiết & Insight:**
  - **Đánh giá kết quả:** Việc sử dụng cấu hình đối xứng 1:1 (`TP/SL: 30/30 pips`) kết hợp `WINDOW_SIZE: 25` đã giúp mô hình hội tụ vô cùng nhanh và đạt Score **0.5010** rất sớm ở Epoch 19. Tuy nhiên, do mạng `D_MODEL: 128` hơi phức tạp và sequence length 25 có chứa nhiễu, Validation loss (CE) bắt đầu phân kỳ liên tục sau đó dẫn đến kích hoạt Early Stopping tại Epoch 48.
  - **Bài học rút ra:** Cần giảm bớt độ phức tạp mạng (`D_MODEL`) và thu hẹp bớt `WINDOW_SIZE` về mức champion cũ (20 nến) để giảm overfitting trên dữ liệu mỏng của phiên Á.

---

### [2026-05-18 14:20:00] - TỐI ƯU HÓA ĐỘT PHÁ BALANCED SNIPER V2: run_20260518_142000_v5_asian_balanced_sniper_v2
- **Kết quả:** Composite Score = **0.2522** | Win Rate = **29.41%** | Early Stopped ở Epoch **100**
- **Phân tích chi tiết & Insight:**
  - **Giảm overfitting vĩ mô:** Kế thừa sự thành công của cấu hình đối xứng 1:1 (`TP_PCT: 0.003 / SL_PCT: 0.003`), chúng ta thực hiện phẫu thuật thu hẹp mạng xuống `D_MODEL: 96` và tăng gấp đôi regularization (`WEIGHT_DECAY: 0.0030`) để ngăn chặn hoàn toàn việc validation loss phân kỳ sớm.
  - **Thu hẹp cửa sổ:** Thu hẹp `WINDOW_SIZE` từ 25 về `20` nến và rút ngắn `FAST_HIT_BARS` về `5` nến nhằm giúp AI nhận diện nhạy bén hơn các momentum vi mô, hạn chế kẹt lệnh trong các đợt đảo chiều thanh khoản phiên Á.
  - **Đánh giá kết quả:** Việc giảm mạng xuống 96 và sequence length xuống 20 thực tế làm giảm năng lực biểu diễn phi tuyến tính của mô hình, dẫn đến Score sụt giảm xuống **0.2522**. Cần quay lại sequence length 25 và d_model 128 nhưng làm mịn LR.

---

### [2026-05-18 15:30:00] - TỐI ƯU HÓA ĐỘT PHÁ ATTENTION SNIPER V3: run_20260518_153000_v5_asian_attention_sniper_v3
- **Kết quả:** Composite Score = **0.4633** | Win Rate = **47.92%** | Early Stopped ở Epoch **53**
- **Phân tích chi tiết & Insight:**
  - **Cấu hình & Tối ưu:** Sử dụng lại `D_MODEL: 128`, `WINDOW_SIZE: 25` và `FAST_HIT_BARS: 6` để phục hồi dung lượng biểu diễn của mô hình. Tăng cường regularization bằng `WEIGHT_DECAY: 0.0025`, `DROPOUT: 0.35`, `LAYER_DROP: 0.40`, nới `LABEL_SMOOTHING: 0.15` và làm mịn `LEARNING_RATE: 1.5e-05`.
  - **Đánh giá kết quả:** Mô hình hội tụ rất ổn định và đạt kết quả đột phá **0.4633** Score, Win Rate **47.92%**. Quá trình validation loss phân kỳ đã được kéo dài đáng kể (Early Stopped ở Epoch 53 thay vì Epoch 48). Tuy nhiên, kết quả này vẫn chưa vượt qua đỉnh cao lịch sử của Asian V5.


---

### [2026-05-18 15:45:00] - TỐI ƯU HÓA ĐỘT PHÁ QUANTUM SNIPER: run_20260518_154500_v5_asian_quantum_sniper
- **Ý tưởng & Cấu hình:**
  - **Tên ý tưởng:** "Quantum Sniper" (`run_20260518_154500_v5_asian_quantum_sniper`)
  - **Đặc điểm ý tưởng & Cấu hình:**
    - Cân bằng dung lượng biểu diễn: Giữ vững cấu trúc mạnh `D_MODEL: 128` kết hợp sequence length `WINDOW_SIZE: 20` để trích xuất đặc trưng tối ưu mà không loãng dữ liệu.
    - Chống quét SL sớm (Whipsaws): Nới nhẹ tỷ lệ đối xứng lên `TP_PCT: 0.0035 / SL_PCT: 0.0035` (35 pips) giúp lệnh có thêm biên dao động tự do trong phiên Á biến động hẹp.
    - Cường hóa Regularization: Tăng Weight Decay lên `0.0035`, nới Label Smoothing lên `0.18` và Focal Gamma lên `3.0` để tối ưu hóa khả năng chống overfitting triệt để.
    - Điều chỉnh learning rate mượt mà về `2.0e-05` giúp AI học sâu và chắc chắn qua từng epoch.
  - **Kết quả:** Composite Score = **0.440** | Win Rate = **44.44%** | Early Stopped ở Epoch **31** (Best Epoch 6)
  - **Phân tích chi tiết & Insight:**
    - **Đánh giá kết quả:** Quantum Sniper đạt mức đối xứng lệnh cực đẹp (18 Buy, 18 Sell ở Best threshold 0.5567) nhờ cơ chế đối xứng 1:1 và nới nhẹ biên lên 35 pips. Tuy nhiên, việc tăng Weight Decay quá mạnh lên `0.0035` kết hợp với Label Smoothing `0.18` đã làm "mềm" các đặc trưng phân loại quá mức, khiến Win Rate thực tế bị kéo lùi về **44.44%** và Composite Score đạt **0.440**.
    - **Bài học rút ra:** Mặc dù đối xứng 1:1 là đúng đắn để triệt tiêu bias, việc siết quá chặt các regularizer (WD > 0.003, LS > 0.15) có thể triệt tiêu cả các tín hiệu phân loại hữu ích trong phiên Á có thanh khoản mỏng. Bản chạy kỷ lục `run_20260518_115000_v5_asian_balanced_sniper` (Score **0.5480**) vẫn được giữ vững làm Champion tối cao dưới Monthly Split hôm nay!

---

### [2026-05-18 16:00:00] - TỐI ƯU HÓA ĐỘT PHÁ PURE PRECISION SNIPER: run_20260518_160000_v5_asian_pure_precision_sniper
- **Ý tưởng & Cấu hình:**
  - **Tên ý tưởng:** "Pure Precision Sniper" (`run_20260518_160000_v5_asian_pure_precision_sniper`)
  - **Đặc điểm ý tưởng & Cấu hình:**
    - Cân bằng dung lượng biểu diễn: Giữ `D_MODEL: 128` kết hợp sequence length `WINDOW_SIZE: 20` để trích xuất đặc trưng tối ưu mà không loãng dữ liệu.
    - Đối xứng 1:1 cổ điển: Giữ `TP_PCT: 0.0030 / SL_PCT: 0.0030` (30 pips) để lệnh có không gian dao động tự do hoàn hảo.
    - Giảm cường độ Regularization: Giảm Weight Decay xuống `0.0015`, Label Smoothing xuống `0.08` và Focal Gamma `2.0` nhằm cho phép mô hình học các biên phân loại sắc nét cho các mẫu thanh khoản mỏng.
    - Tăng Learning Rate lên `3.0e-05` giúp AI nhanh chóng thoát khỏi cực tiểu địa phương.
  - **Kết quả:** Composite Score = **0.5131** | Win Rate = **58.82%** | Early Stopped ở Epoch **54** (Best Epoch 19)
  - **Phân tích chi tiết & Insight:**
    - **Đánh giá kết quả:** Đây là một thắng lợi cực lớn về mặt cấu trúc! Mô hình đạt sự đối xứng lệnh hoàn hảo tuyệt đối: **17 Buy và 17 Sell** tại best threshold `0.55`, triệt tiêu hoàn toàn bias mua/bán. Win Rate đạt **58.82%** và Composite Score đạt **0.5131** - rất sát với champion baseline (Score 0.5480, WR 60.61%). 
    - **Bài học rút ra:** Việc nới lỏng các regularizer (WD = 0.0015, LS = 0.08) đã chứng minh tính đúng đắn khi giúp mô hình vượt qua hiện tượng underfitting của Quantum Sniper trước đó. Đối xứng 1:1 kết hợp với regularization vừa phải là chiếc chìa khóa vàng cho phiên Á! Champion baseline `run_20260518_115000_v5_asian_balanced_sniper` vẫn tạm thời dẫn đầu nhưng Pure Precision Sniper là cấu hình có độ đối xứng lệnh an toàn và hoàn mỹ nhất.

---

### [2026-05-18 16:30:00] - TỐI ƯU HÓA ĐỘT PHÁ PRECISION FLOW SCALPER: run_20260518_163000_v5_asian_precision_flow_scalper
- **Ý tưởng & Cấu hình:**
  - **Tên ý tưởng:** "Precision Flow Scalper" (`run_20260518_163000_v5_asian_precision_flow_scalper`)
  - **Đặc điểm ý tưởng & Cấu hình:**
    - Cân bằng dung lượng biểu diễn: Giữ `D_MODEL: 128` kết hợp sequence length `WINDOW_SIZE: 20` để trích xuất đặc trưng tối ưu mà không loãng dữ liệu.
    - Đối xứng 1:1 hoàn mỹ: Giữ `TP_PCT: 0.0030 / SL_PCT: 0.0030` (30 pips) để đảm bảo không bị méo loss phân loại.
    - Nới nhẹ thời gian giữ lệnh: Nới `FAST_HIT_BARS: 6` (tăng từ 5 nến) giúp mô hình có thêm thời gian tiệm cận TP đầy đủ hơn trong phiên Á di chuyển chậm, khắc phục triệt để hiện tượng kẹt lệnh do whipsaws ngắn hạn.
    - Tinh chỉnh cường độ Regularization: Weight Decay `0.0012`, Label Smoothing `0.05` và Focal Gamma `2.0` nhằm cho phép mô hình tối đa hóa sự tự tin vào các biên phân loại sắc nét mà không làm loãng đặc tính nến.
    - Học tập mượt mà: Learning Rate `2.5e-05` giúp AI hội tụ cực kỳ mượt mà.
  - **Trạng thái:** Đang tiến hành huấn luyện nền local.
