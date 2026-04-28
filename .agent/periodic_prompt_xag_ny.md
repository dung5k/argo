# NHIỆM VỤ ĐỊNH KỲ (GH): AUTO-TUNING XAG NY BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `xag_ny_auto_tuning`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy GH** để tìm cấu hình tốt nhất cho bộ não `CFG_XAG_NY_V3_5`. 

## BƯỚC 1: Phân tích Lịch sử & Tư duy Tối ưu hóa (Quant/ML Expert)

Thay vì đoán mò ngẫu nhiên, bạn phải phân tích có hệ thống dựa trên lịch sử để tìm ra hướng tối ưu (Gradient of Improvement).

1. **Thu thập Ngữ cảnh (Context Gathering):**
   - Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_XAG_NY_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
   - Nếu có, HÃY KIỂM TRA file ghi nhận kết quả tốt nhất (ví dụ các run tốt nhất trong quá khứ) để lấy mốc so sánh (Baseline).

2. **Phân tích Hiệu suất (Performance Analysis) & Dọn dẹp (Cleanup/Push):**
   - So sánh `Composite Score`, `Win Rate`, `Loss` của lượt mới nhất với Baseline. 
   - Đánh giá phân phối tín hiệu: Mô hình có đang bị bias (thiên lệch) mua/bán quá nhiều không? Có bị overfit không (Train loss giảm nhưng Val loss tăng)?
   - **HÀNH ĐỘNG BẮT BUỘC:** NẾU kết quả kém quá (Composite Score thấp hơn nhiều so với Baseline hoặc bị overfit), HÃY XÓA NGAY thư mục run đó (ví dụ dùng lệnh `rm -rf` hoặc `del /s /q`) để dọn dẹp dung lượng. NẾU kết quả ổn, hãy sử dụng lệnh để đồng bộ nó lên Hugging Face (ví dụ chạy `python scratch/sync_hf.py` hoặc thêm cấu hình vào đó rồi chạy).
   - **BÁO CÁO TỔNG QUAN:** HÃY cập nhật một file `training_report.md` (nằm trong thư mục gốc của cấu hình, ví dụ: `workspaces/CFG_XAG_NY_V3_5/training_report.md`). Ghi ngắn gọn tóm tắt nội dung của từng lượt thực hiện (Run ID, tham số thay đổi, kết quả đạt được, và quyết định tiếp theo). Nhớ đẩy file `training_report.md` này lên Hugging Face cùng với các lượt chạy tốt để theo dõi toàn bộ quá trình đào tạo.

3. **Đánh giá & Điều chỉnh Features (Feature Engineering):**
   - **Phiên NY (New York):** XAG (Bạc) chịu ảnh hưởng mạnh bởi tin tức vĩ mô Mỹ, biến động của DXY và sự tương quan đồng điệu với XAU (Vàng). 
   - Các chỉ số đang có: XAUUSD, USTEC, DXY... Hãy tự đánh giá sự đóng góp của chúng. 
   - *Chiến lược mới (Nâng Win Rate):* PHẢI bật `"ZERO_NOISE_TARGET": true` để loại bỏ tín hiệu nhiễu do quét hai chiều. PHẢI bật `"ORDER_FLOW": true` và `"VOL_REGIME": true` để nhận diện dòng tiền lớn.

4. **Ra quyết định Siêu tham số (Hyperparameter Strategy):**
   - Không gian tìm kiếm (Search Space) tập trung TỐI ĐA VÀO WIN RATE:
     + `WINDOW_SIZE` (độ dài chuỗi thời gian nhìn lại): Bắt đầu sử dụng từ mức 30 để có đủ thông tin xu hướng trước khi vào phiên.
     + `TP_PIPS`, `SL_PIPS`: Để tăng Win Rate, thiết lập TP nhỏ hơn hoặc bằng SL (ví dụ: TP 40, SL 60).
     + `D_MODEL`, `NUM_LAYERS`, `N_HEAD`: Chỉnh kích thước bộ não để tránh overfit/underfit.
     + `BATCH_SIZE`: Khuyến nghị duy trì 512.
     + `LEARNING_RATE`: Thử tinh chỉnh trong khoảng 1e-5 đến 5e-5.
   - **NGUYÊN TẮC TỐI THƯỢNG:** Trong lượt tạo config tiếp theo, **CHỈ THAY ĐỔI 1 ĐẾN TỐI ĐA 2 THAM SỐ (Variables)** so với lượt trước đó để có thể đo lường chính xác tác động (A/B Testing). Hãy ghi chú rõ ràng lý do bạn đổi tham số này vào file cấu hình hoặc logs.

5. **Chuyển hướng Chiến lược (Pivot Strategy):**
   - NẾU đáp ứng một trong hai điều kiện sau:
     1. Đã thử thay đổi tuần tự các tham số nhưng `Composite Score` không vượt qua được mốc cao nhất trong 10-15 lượt gần nhất.
     2. Bạn ĐÃ CẠN Ý TƯỞNG cho việc thử nghiệm các cấu hình mới khả thi trong giới hạn của chiến lược hiện tại.
   - THÌ BẮT BUỘC KHÔNG ĐƯỢC TẮT TASK. Thay vào đó, hãy **NGHĨ RA MỘT CHIẾN LƯỢC HOÀN TOÀN MỚI** (Ví dụ: tắt/bật `ZERO_NOISE_TARGET`, đổi hẳn các chỉ báo MACRO, thay đổi lớn về tỷ lệ TP/SL, hoặc cách nhìn nhận xu hướng) để tiếp tục vòng lặp thử nghiệm. Hãy ghi rõ vào file `tuning_notes.txt` về sự thay đổi chiến lược này để tiện theo dõi.

## BƯỚC 2: Chuẩn bị dữ liệu (Hàng Đợi)
Kiểm tra `workspaces/CFG_XAG_NY_V3_5/runs/`. Những thư mục chưa có `training_metrics_v3.json` là Pending Runs.
Nếu hàng đợi rỗng:
1. Tạo `<RUN_ID>` mới (vd: `run_YYYYMMDD_HHMMSS_v3_ny_X`), tạo thư mục và copy `base_config.json` thành `config.json`. 
   - Áp dụng các quyết định từ Bước 1.4 vào `config.json` mới. **BẮT BUỘC KHÔNG SỬA base_config.json gốc!**
   - Tạo thêm một file `tuning_notes.txt` trong thư mục run mới này, viết đúng 2-3 câu tóm tắt: "Lượt này thay đổi tham số gì? Kỳ vọng điều gì xảy ra?". Điều này giúp bạn của tương lai đọc lại và hiểu mạch tư duy.
2. Chạy:
```
python scripts/crawl_crypto_v3.py workspaces/CFG_XAG_NY_V3_5/runs/<RUN_ID>/config.json
python scripts/upload_v3_dataset.py --config workspaces/CFG_XAG_NY_V3_5/runs/<RUN_ID>/config.json
```
3. Commit Git `auto-tuning XAG NY data ready: <RUN_ID>`.

## BƯỚC 3: Training Cục bộ
Lấy RUN_ID từ hàng đợi và chạy:
```
python src/training_v3/train_v3.py workspaces/CFG_XAG_NY_V3_5/runs/<RUN_ID>/config.json --session ny --scratch --run-id <RUN_ID>; python .agent/notify_done.py xag_ny_training_done
```
(Lưu ý: Gọi `notify_done.py` sau lệnh training giúp kích hoạt luồng nhận biết training xong để nhận nhiệm vụ tiếp theo ngay lập tức).

## BƯỚC 4: Tự động điều chỉnh lịch trình (Tuỳ chọn)
Nếu bạn nhận thấy quá trình crawling mất nhiều thời gian, hoặc bạn muốn theo dõi kết quả sau 5 phút, 15 phút, bạn có thể tự thay đổi thời gian kích hoạt task tiếp theo bằng cách:
Sửa trường `nextRunTime` của task `xag_ny_auto_tuning` trong file `.agent/tasks.json` thành `(timestamp hiện tại + N * 60) * 1000`. Nếu không sửa, Extension sẽ tự lặp lại theo `intervalMinutes` mặc định.

## BƯỚC 5: Nhả trạng thái rảnh
Sau khi mọi thứ chạy ổn, Gửi Telegram và báo xong (BẮT BUỘC):
```
python .agent/send_to_tele.py "<Báo cáo tình hình>" --done
```
