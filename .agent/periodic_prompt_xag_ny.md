# NHIỆM VỤ ĐỊNH KỲ (GH): AUTO-TUNING XAG NY BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `xag_ny_auto_tuning`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy GH** để tìm cấu hình tốt nhất cho bộ não `CFG_XAG_NY_V3_5`. 

## BƯỚC 1: Đánh giá kết quả & Phân tích Tương quan (Quant Expert)
1. **Đọc dữ liệu**: Mở file `training_metrics_v3.json` mới nhất trong `workspaces/CFG_XAG_NY_V3_5/runs/` (thường trong thư mục `results/`). Xem xét `Composite Score`, `Win Rate` và phân phối tín hiệu (Buy/Sell).
2. **Phân tích Leading Indicators**: XAG NY là thị trường biến động mạnh và có độ trễ so với các chỉ số dẫn dắt. Hãy tập trung tìm sự phụ thuộc của XAG vào:
   - **XAUUSD (Vàng)**: Thường chạy trước hoặc song song với Bạc.
   - **USTEC (Nasdaq)**: Đại diện cho khẩu vị rủi ro (Risk-on/Risk-off).
   - **DXY (Dollar Index)**: Biến động ngược chiều mạnh.
3. **Giả thuyết cho lượt chạy tiếp theo**: 
   - Nếu Win Rate thấp, có thể do `WINDOW_SIZE` quá ngắn chưa bao quát được độ trễ của chỉ số dẫn dắt (thử tăng 60-120 phút).
   - Xem xét tăng độ phức tạp của bộ não (`D_MODEL`, `NUM_LAYERS`) để nhận diện các mẫu (pattern) biến động phức tạp giữa các mã macro.
   - Thử nghiệm thay đổi `TP/SL` để bắt kịp các con sóng lớn do chỉ số dẫn dắt tạo ra.
4. **Dừng Task**: Nếu đã thử mọi cách (thay đổi Macro, Window, Model size) nhưng Composite Score không cải thiện qua 25 lượt, hãy tắt task này bằng cách sửa file `.agent/tasks.json` (`enabled = false`), báo cáo Telegram và gọi `--done`.

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
