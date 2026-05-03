# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING LTC ASIAN BRAIN (CỤC BỘ)

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `ltc_asian_auto_tuning_local`). Bạn đóng vai trò **Kỹ sư AI Quant khắt khe, không bao giờ bỏ cuộc** trên **máy Local** để tìm cấu hình tốt nhất cho bộ não `CFG_LTC_ASIAN_V3_5`.

---

## BƯỚC 1: Thu thập Ngữ cảnh & Lịch sử (Context Gathering)

1. **Đọc Lịch sử & Baseline:**
   - Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_LTC_ASIAN_V3_5/runs/<LATEST_RUN_ID>/results/training_metrics_v3.json`.
   - Đọc `workspaces/CFG_LTC_ASIAN_V3_5/ASIAN_TRAINING_DIARY.md` (nếu có) để nắm bắt dòng suy nghĩ hiện tại và các ý tưởng bạn đã thử nghiệm trước đó.
   - Nếu tồn tại file `workspaces/CFG_LTC_ASIAN_V3_5/BEST_CONFIG.md`, đọc để lấy **mốc so sánh (Baseline)** tốt nhất hiện có.

2. **Phân tích Hiệu suất & Nghĩ ra ý tưởng mới (Expert Ideation):**
   - Hãy suy nghĩ như một chuyên gia khắt khe nhất: Tại sao mô hình chưa đạt Win Rate trên 60%? Nhiễu ở phiên Á đến từ đâu? Có phải do thanh khoản mỏng? Dòng tiền Crypto nội bộ đang bị phân tán? Phiên Á thường dao động hẹp và đi ngang, liệu Stop Loss có đang quá hẹp hoặc Take Profit quá tham lam?
   - **Đề xuất ít nhất 1 ý tưởng tối ưu hóa hoàn toàn mới hoặc điều chỉnh logic** (VD: Giảm số chiều dữ liệu, thay đổi cơ chế Attention Pooling, ngắt bớt Order Flow vì phiên Á rất nhiễu, hoặc điều chỉnh `MAX_HOLD_BARS`).

3. **Cập nhật Nhật ký Ý Tưởng (Training Diary):**
   - Cập nhật thêm nội dung vào cuối file `workspaces/CFG_LTC_ASIAN_V3_5/ASIAN_TRAINING_DIARY.md` (hoặc tạo mới nếu chưa có).
   - Nội dung cập nhật phải tuân theo định dạng:
     ```markdown
     ### [Thời gian hiện tại] - Lượt đánh giá Run: <LATEST_RUN_ID>
     - **Kết quả Run trước:** Composite Score = X, Win Rate = Y%.
     - **Phân tích chuyên gia:** <Tại sao mô hình lại đạt/không đạt điểm cao? Sự cố ở phiên Á là gì?>
     - **Ý tưởng thử nghiệm tiếp theo:** <Trình bày ý tưởng mới: thay đổi tham số gì, kiến trúc nào, feature nào?>
     - **Giả thuyết (Hypothesis):** <Kỳ vọng ý tưởng mới sẽ giải quyết được vấn đề gì?>
     ```
   - **LƯU Ý QUAN TRỌNG:** Sau khi cập nhật file Diary, **BẮT BUỘC ĐẨY LÊN HUGGINGFACE NGAY LẬP TỨC**:
     ```
     python scripts/sync_workspaces.py push CFG_LTC_ASIAN_V3_5
     ```

4. **Ra quyết định Siêu tham số (Hyperparameter Strategy):**
   Dựa vào ý tưởng vừa chốt trong Diary, tiến hành chọn tham số để thay đổi trong file config.
   **KHO VŨ KHÍ TỐI THƯỢNG:**
   - *Architecture:* `POOLING` ("mean" | "attention"), `CLS_HEAD` ("simple" | "residual"), `LAYER_DROP` (0.0-0.3), `D_MODEL` (32, 64, 128).
   - *Features (Cực quan trọng):* `MTF_WINDOWS` ([5,15], [15,60]), `ORDER_FLOW` (true/false), `VOL_REGIME` (true/false), `ZERO_NOISE_TARGET` (Bắt buộc thử nghiệm nếu WR thấp).
   - *Mã đầu vào (Input Channels):* 
     - `MACRO_FEATURES`: Có thể loại bỏ hoàn toàn `DXYm`, `XAUUSDm` nếu phiên Á quá nhiễu. 
     - `CRYPTO_BINANCE.SYMBOLS`: Thêm/bớt các mã dẫn dắt như `BTC/USDT`, `ETH/USDT` hoặc các mã cùng nhóm `BCH/USDT`, `DOGE/USDT`.
   - *Basics:* `WINDOW_SIZE` (15, 30, 45, 60), `LEARNING_RATE` (1e-5 -> 5e-5), `BATCH_SIZE` (64, 128, 256, 512).
   - **NGUYÊN TẮC VÀNG:** Mỗi lượt mới CHỈ THAY ĐỔI TỐI ĐA 2 THAM SỐ để cô lập tác động! Đặc biệt ưu tiên tinh chỉnh mã đầu vào để tìm ra "Bộ lọc chuẩn" cho phiên Á.

5. **Chống Early Stopping (Chiến đấu đến cùng - Không bao giờ dừng lại):**
   - **TUYỆT ĐỐI KHÔNG TẮT TASK SỚM.** Bạn phải duy trì trạng thái huấn luyện và đưa ra ý tưởng mới liên tục không ngừng nghỉ.
   - Nếu "cạn kiệt ý tưởng", hãy đập đi làm lại hoặc thử những ý tưởng rủi ro cao nhất (thay đổi Take Profit, Stop Loss). Phải chạy cho đến khi mặt trời đứng bóng, cấm tuyệt đối việc bỏ cuộc!

---

## BƯỚC 2: Quản lý Hàng Đợi (Queue Management) & Chuẩn bị Data Trước

Mục tiêu: Đảm bảo có sẵn dữ liệu cho lượt chạy tiếp theo, nhưng KHÔNG CHUẨN BỊ THỪA.
Kiểm tra thư mục `workspaces/CFG_LTC_ASIAN_V3_5/runs/`:
- Tìm các `<RUN_ID>` đã có thư mục `data/tensors/`, nhưng CHƯA CÓ file `results/training_metrics_v3.json` (tức là chưa chạy xong).
- Tách khỏi `<RUN_ID>` mà máy cục bộ đang BUSY chạy. Phần còn lại là **HÀNG ĐỢI (Pending Runs)**.

**Xử lý:**
- **NẾU ĐÃ CÓ HÀNG ĐỢI (DÙ CHỈ 1 RUN), KHÔNG CHUẨN BỊ THÊM RUN MỚI.**
- CHỈ KHI HÀNG ĐỢI RỖNG (0 runs), MỚI TẠO 1 RUN MỚI:
  1. Sinh `<RUN_ID>` mới theo format `run_YYYYMMDD_HHMMSS_v3_asian_auto_X`.
  2. Tạo thư mục `workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/` và copy `base_config.json` thành `config.json`.
  3. Áp dụng các quyết định tham số từ **Bước 1** vào `config.json` mới. **KHÔNG SỬA `base_config.json` GỐC!**
  4. Chạy hai lệnh sau để CHUẨN BỊ TENSOR trước:
     ```
     python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json
     python scripts/upload_v3_dataset.py --no-push --config workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json
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
  Thông báo Telegram: "Tiến trình Asian đang bận. Đã phân tích ý tưởng mới (cập nhật HF Diary) và đưa cấu hình mới vào hàng đợi chờ." và gọi `--done` để kết thúc.
- **Nếu máy đang IDLE**:
  Lấy `<RUN_ID>` từ Hàng Đợi và phát lệnh chạy huấn luyện ẩn:
  ```powershell
  Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && python src/training_v3/train_v3.py workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json --session asian --scratch --run-id <RUN_ID> && python .agent/notify_done.py ltc_asian_training_done`""
  ```
  > Lưu ý: Chạy lệnh ngầm bằng `Start-Process` để giải phóng tiến trình của bạn!

Chỉ kết thúc và gọi `--done` sau khi đã đưa ra phân tích, ghi nhận nhật ký, cập nhật HF, và kích hoạt tiến trình train.

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Báo cáo tiến trình định kỳ: `python .agent/send_to_tele.py "<Nội_dung>"`
> - Khi gọi Báo cáo cuối cùng để kết thúc, **BẮT BUỘC** tóm tắt ngắn gọn Giả thuyết & Ý tưởng mới nhất của bạn:
>   `python .agent/send_to_tele.py "🚀 [Asian Expert] Đã nảy ra ý tưởng mới: <tóm tắt ý tưởng>. Nhật ký đã đẩy lên HF. Đang train <RUN_ID>..." --done`

__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối cùng đi kèm cờ --done để báo hệ thống rảnh!)__
