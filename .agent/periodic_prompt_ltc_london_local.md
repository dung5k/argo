# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING LTC LONDON BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `ltc_london_auto_tuning_local`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy Local** để tìm cấu hình tốt nhất cho bộ não `CFG_LTC_LONDON_V3_5`.

---

## BƯỚC 1: Thu thập Ngữ cảnh & Lịch sử (Context Gathering)

1. **Đọc Lịch sử & Baseline:**
   - Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_LTC_LONDON_V3_5/runs/<LATEST_RUN_ID>/results/training_metrics_v3.json`.
   - Đọc `workspaces/CFG_LTC_LONDON_V3_5/LONDON_TRAINING_DIARY.md` (nếu có) để nắm bắt dòng suy nghĩ hiện tại và các ý tưởng bạn đã thử nghiệm trước đó.
   - Nếu tồn tại file `workspaces/CFG_LTC_LONDON_V3_5/BEST_CONFIG.md`, đọc để lấy **mốc so sánh (Baseline)** tốt nhất hiện có.

2. **Phân tích Hiệu suất & Nghĩ ra ý tưởng mới (Expert Ideation):**
   - Hãy suy nghĩ như một chuyên gia: Mô hình đang bị lỗi gì? Overfitting (train loss giảm, val loss tăng)? Tỷ lệ Win Rate thực tế quá thấp? Quá thiên lệch tín hiệu Buy hoặc Sell? Cấu trúc London cần tốc độ (momentum) hay sự ổn định (volatility filtering)? Phiên London thường nhận thanh khoản từ phiên Âu, đặc trưng bởi các cú quét (Judas Swing) và xu hướng mạnh.
   - Từ đó, **Đề xuất ít nhất 1 ý tưởng tối ưu hóa hoàn toàn mới hoặc điều chỉnh logic** (VD: Thêm feature đo biến động bb_width, giảm số lượng lớp ẩn để chống overfit, sử dụng pooling attention, thay đổi khung thời gian, hoặc thử áp dụng LTCBTC để bắt tín hiệu tương đối...).

3. **Cập nhật Nhật ký Ý Tưởng (Training Diary):**
   - Cập nhật thêm nội dung vào cuối file `workspaces/CFG_LTC_LONDON_V3_5/LONDON_TRAINING_DIARY.md` (hoặc tạo mới nếu chưa có).
   - Nội dung cập nhật phải tuân theo định dạng:
     ```markdown
     ### [Thời gian hiện tại] - Lượt đánh giá Run: <LATEST_RUN_ID>
     - **Kết quả Run trước:** Composite Score = X, Win Rate = Y%.
     - **Phân tích chuyên gia:** <Tại sao mô hình lại đạt/không đạt điểm cao? Điều gì đang kìm hãm mô hình ở phiên London?>
     - **Ý tưởng thử nghiệm tiếp theo:** <Trình bày ý tưởng mới: thay đổi tham số gì, kiến trúc nào, feature nào?>
     - **Giả thuyết (Hypothesis):** <Kỳ vọng ý tưởng mới sẽ giải quyết được vấn đề gì?>
     ```
   - **LƯU Ý QUAN TRỌNG:** Sau khi cập nhật file Diary, **BẮT BUỘC ĐẨY LÊN HUGGINGFACE NGAY LẬP TỨC** để người dùng có thể theo dõi tiến trình tư duy của bạn:
     ```
     python scripts/sync_workspaces.py push CFG_LTC_LONDON_V3_5
     ```

4. **Ra quyết định Siêu tham số (Hyperparameter Strategy):**
   Dựa vào ý tưởng vừa chốt trong Diary, tiến hành chọn tham số để thay đổi.
   **KHO VŨ KHÍ:**
   - *Architecture:* `POOLING` ("mean" | "attention"), `CLS_HEAD` ("simple" | "residual"), `LAYER_DROP` (0.0-0.3)
   - *Features:* `MTF_WINDOWS` ([5,15], [15,60]), `ORDER_FLOW` (true/false), `VOL_REGIME` (true/false), Tỷ giá chéo (`LTCBTC`)
   - *Basics:* `WINDOW_SIZE` (15, 30, 45, 60, 90), `LEARNING_RATE` (1e-5 -> 5e-5), `BATCH_SIZE` (64, 128, 256)
   - **NGUYÊN TẮC:** Mỗi lượt mới CHỈ THAY ĐỔI TỐI ĐA 2 THAM SỐ để cô lập tác động! Đừng thay đổi mù quáng.

5. **Chống Early Stopping (Chiến đấu đến cùng):**
   - **TUYỆT ĐỐI KHÔNG TẮT TASK SỚM.** Bạn phải duy trì trạng thái huấn luyện và đưa ra ý tưởng mới liên tục ít nhất cho đến 12:00 PM trưa (giờ Local).
   - Nếu "cạn kiệt ý tưởng", hãy đập đi làm lại hoặc thử những ý tưởng rủi ro cao nhất (thay đổi Take Profit, Stop Loss). Phải chạy cho đến khi mặt trời đứng bóng!

---

## BƯỚC 2: Quản lý Hàng Đợi (Queue Management) & Chuẩn bị Data Trước

Mục tiêu: Đảm bảo có sẵn dữ liệu cho lượt chạy tiếp theo, nhưng KHÔNG CHUẨN BỊ THỪA.
Kiểm tra thư mục `workspaces/CFG_LTC_LONDON_V3_5/runs/`:
- Tìm các `<RUN_ID>` đã có thư mục `data/tensors/`, nhưng CHƯA CÓ file `results/training_metrics_v3.json` (tức là chưa chạy xong).
- Tách khỏi `<RUN_ID>` mà máy cục bộ đang BUSY chạy. Phần còn lại là **HÀNG ĐỢI (Pending Runs)**.

**Xử lý:**
- **NẾU ĐÃ CÓ HÀNG ĐỢI (DÙ CHỈ 1 RUN), KHÔNG CHUẨN BỊ THÊM RUN MỚI.**
- CHỈ KHI HÀNG ĐỢI RỖNG (0 runs), MỚI TẠO 1 RUN MỚI:
  1. Sinh `<RUN_ID>` mới theo format `run_YYYYMMDD_HHMMSS_v4_ldn_auto_X`.
  2. Tạo thư mục `workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/` và copy `base_config.json` thành `config.json`.
  3. Áp dụng các quyết định tham số từ **Bước 1** vào `config.json` mới. **KHÔNG SỬA `base_config.json` GỐC!**
  4. Chạy hai lệnh sau để CHUẨN BỊ TENSOR trước:
     ```
     python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json
     python scripts/upload_v3_dataset.py --no-push --config workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json
     ```

---

---

## BƯỚC 3: Giám sát & Điều phối Huấn Luyện Cục Bộ (Local Dispatching & Monitoring)

1. **Giám sát Tiến trình (Process Monitoring):**
   - Kiểm tra xem có tiến trình `train_v3.py` nào đang chạy không bằng lệnh `Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%train_v3.py%'"`.
   - Nếu có tiến trình đang chạy, hãy kiểm tra file log `train_v3.log` trong thư mục `results/` của lượt chạy đó.
   - **TÌNH HUỐNG GIẢI CỨU:** Nếu tiến trình đã chạy quá 4 giờ hoặc file log không có cập nhật mới trong 20 phút (bị treo/OOM ẩn), hãy:
     1. Kill tiến trình đó bằng lệnh `Stop-Process -Id <PID> -Force`.
     2. Đọc 50 dòng cuối của file log để điều tra nguyên nhân (Lỗi CUDA, OOM, hay lỗi logic).
     3. Báo cáo chi tiết lỗi qua Telegram.
     4. Xóa thư mục run lỗi đó (nếu nó chưa kịp tạo ra kết quả WR > 60%).
     5. Sau đó mới tiếp tục các bước dưới đây để hàng đợi được thông suốt.

2. **Điều phối (Dispatching):**
   - **Nếu máy đang BUSY** (có tiến trình hợp lệ đang chạy và vẫn đang update log):
  Thông báo Telegram: "Tiến trình London đang bận. Đã phân tích ý tưởng mới (cập nhật HF Diary) và đưa cấu hình mới vào hàng đợi chờ." và gọi `--done` để kết thúc.
- **Nếu máy đang IDLE**:
  Lấy `<RUN_ID>` từ Hàng Đợi và phát lệnh chạy huấn luyện ẩn:
  ```powershell
  Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && python src/training_v3/train_v3.py workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json --session london --scratch --run-id <RUN_ID> && python .agent/notify_done.py ltc_london_training_done`""
  ```
  > Lưu ý: Chạy lệnh ngầm bằng `Start-Process` để giải phóng tiến trình của bạn!

Chỉ kết thúc và gọi `--done` sau khi đã đưa ra phân tích, ghi nhận nhật ký, cập nhật HF, và kích hoạt tiến trình train.

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Báo cáo tiến trình định kỳ: `python .agent/send_to_tele.py "<Nội_dung>"`
> - Khi gọi Báo cáo cuối cùng để kết thúc, **BẮT BUỘC** tóm tắt ngắn gọn Giả thuyết & Ý tưởng mới nhất của bạn:
>   `python .agent/send_to_tele.py "🚀 [London Expert] Đã nảy ra ý tưởng mới: <tóm tắt ý tưởng>. Nhật ký đã đẩy lên HF. Đang train <RUN_ID>..." --done`

__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối cùng đi kèm cờ --done để báo hệ thống rảnh!)__
