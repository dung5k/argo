# NHIỆM VỤ ĐỊNH KỲ (GH): AUTO-TUNING XAG NY BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `xag_ny_auto_tuning`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy GH** để tìm cấu hình tốt nhất cho bộ não `CFG_XAG_NY_V3_5`. 

## BƯỚC 1: Phân tích Lịch sử & Tư duy Tối ưu hóa (Quant/ML Expert)

Thay vì đoán mò ngẫu nhiên, bạn phải phân tích có hệ thống dựa trên lịch sử để tìm ra hướng tối ưu (Gradient of Improvement).

1. **Thu thập Ngữ cảnh (Context Gathering):**
   - Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_XAG_NY_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
   - Nếu có, HÃY KIỂM TRA file ghi nhận kết quả tốt nhất (ví dụ các run tốt nhất trong quá khứ) để lấy mốc so sánh (Baseline).

2. **Phân tích Hiệu suất (Performance Analysis):**
   - So sánh `Composite Score`, `Win Rate`, `Loss` của lượt mới nhất với Baseline. 
   - Đánh giá phân phối tín hiệu: Mô hình có đang bị bias (thiên lệch) mua/bán quá nhiều không? Có bị overfit không (Train loss giảm nhưng Val loss tăng)?

3. **Đánh giá & Điều chỉnh Features (Feature Engineering):**
   - **Phiên NY (New York):** XAG (Bạc) chịu ảnh hưởng mạnh bởi tin tức vĩ mô Mỹ, biến động của DXY và sự tương quan đồng điệu với XAU (Vàng). 
   - Các chỉ số đang có: XAUUSD, USTEC, DXY... Hãy tự đánh giá sự đóng góp của chúng. 
   - *Chiến lược:* Nếu mô hình đang chững lại, hãy thử **THÊM** các features đo lường biến động (Volatility) hoặc tương quan (corr) vào `config.json`; HOẶC **LOẠI BỎ** các features có vẻ gây nhiễu. Đừng giữ nguyên một bộ features nếu điểm số không tăng.

4. **Ra quyết định Siêu tham số (Hyperparameter Strategy):**
   - Không gian tìm kiếm (Search Space) gợi ý:
     + `WINDOW_SIZE` (độ dài chuỗi thời gian nhìn lại): Thử các mốc 30, 60, 90.
     + `D_MODEL`, `NUM_LAYERS`, `N_HEAD`: Chỉnh kích thước bộ não để tránh overfit/underfit.
     + `BATCH_SIZE`: 256, 512...
     + `LEARNING_RATE`: Thử tinh chỉnh trong khoảng 1e-5 đến 5e-5.
     + `TP_PIPS`, `SL_PIPS`: Chỉnh biên độ ăn/thua cho phù hợp độ bốc của phiên NY.
   - **NGUYÊN TẮC TỐI THƯỢNG:** Trong lượt tạo config tiếp theo, **CHỈ THAY ĐỔI 1 ĐẾN TỐI ĐA 2 THAM SỐ (Variables)** so với lượt trước đó để có thể đo lường chính xác tác động (A/B Testing). Hãy ghi chú rõ ràng lý do bạn đổi tham số này vào file cấu hình hoặc logs.

5. **Early Stopping (Dừng Task):**
   - Nếu đã thử thay đổi tuần tự các tham số nhưng `Composite Score` không vượt qua được mốc cao nhất trong 25 lượt gần nhất, hãy tắt task bằng cách mở `.agent/tasks.json`, tìm id `xag_ny_auto_tuning` và đặt `"enabled": false`. 

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
python src/training_v3/train_v3.py --config workspaces/CFG_XAG_NY_V3_5/runs/<RUN_ID>/config.json --session ny --scratch --run-id <RUN_ID>; python .agent/notify_done.py xag_ny_training_done
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
