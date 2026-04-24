# NHIỆM VỤ ĐỊNH KỲ (GH): AUTO-TUNING XAG NY BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `xag_ny_auto_tuning`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy GH** để tìm cấu hình tốt nhất cho bộ não `CFG_XAG_NY_V3_5`. 

## BƯỚC 1: Đánh giá kết quả & Phân tích Tương quan (Quant Expert)
1. **Đọc dữ liệu**: Mở file `training_metrics_v3.json` mới nhất trong `workspaces/CFG_XAG_NY_V3_5/runs/` (thường trong thư mục `results/`). Xem xét `Composite Score`, `Win Rate` và phân phối tín hiệu (Buy/Sell).
2. **Phân tích Leading Indicators**: XAG NY có độ trễ nhất định so với các thị trường dẫn dắt. Dựa vào lịch sử các lượt chạy, hãy tự đánh giá xem các chỉ số Macro hiện tại trong `MACRO_FEATURES` (XAUUSD, USTEC, DXY,...) có đang đóng góp hiệu quả cho mô hình không. Nên chủ động **thêm, bớt hoặc thay thế** các chỉ số dẫn dắt trong `config.json` của lượt chạy mới nếu có lý do tin rằng một chỉ số khác sẽ phản ánh tốt hơn tương quan với XAG trong phiên NY.
3. **Đề xuất thay đổi cấu hình**: Dựa trên kết quả thực tế từ các lượt chạy, hãy tự đưa ra giả thuyết và thay đổi siêu tham số phù hợp. Không có công thức cố định — hãy tư duy như một Quant Engineer và chịu trách nhiệm về quyết định cấu hình của lượt tiếp theo.
4. **Dừng Task**: Nếu đã thử mọi cách nhưng Composite Score không cải thiện qua 25 lượt, hãy tắt task này bằng cách sửa file `.agent/tasks.json` (`enabled = false`), báo cáo Telegram và gọi `--done`.

## BƯỚC 2: Chuẩn bị dữ liệu (Hàng Đợi)
Kiểm tra `workspaces/CFG_XAG_NY_V3_5/runs/`. Những thư mục chưa có `training_metrics_v3.json` là Pending Runs.
Nếu hàng đợi rỗng:
1. Tạo `<RUN_ID>` mới (vd: `run_YYYYMMDD_HHMMSS_v3_ny_X`), tạo thư mục và copy `base_config.json` thành `config.json`. **BẮT BUỘC KHÔNG SỬA base_config.json!**
2. Chạy:
```
python scripts/crawl_crypto_v3.py workspaces/CFG_XAG_NY_V3_5/runs/<RUN_ID>/config.json
python scripts/upload_v3_dataset.py --config workspaces/CFG_XAG_NY_V3_5/runs/<RUN_ID>/config.json
```
3. Commit Git `auto-tuning XAG NY data ready: <RUN_ID>`.

## BƯỚC 3: Training Cục bộ
Lấy RUN_ID từ hàng đợi và chạy:
```
python src/training_v3/train_v3.py --config workspaces/CFG_XAG_NY_V3_5/runs/<RUN_ID>/config.json --session ny --scratch --run-id <RUN_ID>
```

## BƯỚC 4: Tự động điều chỉnh lịch trình (Tuỳ chọn)
Nếu bạn nhận thấy quá trình crawling mất nhiều thời gian, hoặc bạn muốn theo dõi kết quả sau 5 phút, 15 phút, bạn có thể tự thay đổi thời gian kích hoạt task tiếp theo bằng cách:
Sửa trường `nextRunTime` của task `xag_ny_auto_tuning` trong file `.agent/tasks.json` thành `(timestamp hiện tại + N * 60) * 1000`. Nếu không sửa, Extension sẽ tự lặp lại theo `intervalMinutes` mặc định.

## BƯỚC 5: Nhả trạng thái rảnh
Sau khi mọi thứ chạy ổn, Gửi Telegram và báo xong (BẮT BUỘC):
```
python .agent/send_to_tele.py "<Báo cáo tình hình>" --done
```
