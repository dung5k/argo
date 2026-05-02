# NHIỆM VỤ ĐỊNH KỲ (HOST): AUTO-TUNING LTC NY BRAIN (PHÂN TÁN)

Hệ thống sẽ gọi bạn chạy lại prompt này định kỳ mỗi 10 phút một lần. Trách nhiệm của bạn là đóng vai trò một Kỹ sư AI tự động hóa trên máy HOST để điều phối, đi tìm cấu hình và phương án tốt nhất cho bộ não `CFG_LTC_NY_V3_5` và giao việc cho **`client1`**.

Hãy thực thi nghiêm ngặt theo các bước sau trong mỗi lần được gọi:

---

## BƯỚC TIỀN XỬ LÝ: Đồng bộ kết quả mới nhất từ HuggingFace về HOST

**BẮT BUỘC chạy lệnh này đầu tiên**, trước khi làm bất cứ điều gì khác, để đảm bảo dữ liệu trên HOST là mới nhất:
```
python scripts/sync_workspaces.py pull CFG_LTC_NY_V3_5
```

Sau đó mới tiếp tục các bước bên dưới.

---

## BƯỚC 1: Đánh giá Năng lực Cụm (Cluster Status)

Kiểm tra `client1` để xem máy đang rảnh (IDLE) hay bận (BUSY):
```
python src/orchestration/host_controller.py listen --client-id client1 --time 10
```
Ghi nhận trạng thái: IDLE hay BUSY.

**GIÁM SÁT SỨC KHỎE (HEALTH CHECK):**
- Nếu `client1` đang **BUSY** nhưng tiến trình huấn luyện đã chạy quá lâu (ví dụ > 3 giờ) mà không sinh ra file kết quả `training_metrics_v3.json` trên HOST (sau khi sync), bạn ĐƯỢC PHÉP phát lệnh `stop` hoặc can thiệp để khởi động lại tiến trình của Client.
- Điều tra lỗi qua logs được sync về từ Client.

---

## BƯỚC 2: Phân tích Lịch sử & Tư duy Tối ưu hóa (Quant/ML Expert)

Thay vì đoán mò ngẫu nhiên, bạn phải phân tích có hệ thống dựa trên lịch sử để tìm ra **hướng tối ưu (Gradient of Improvement)**.

1. **Thu thập Ngữ cảnh (Context Gathering):**
   - Đọc kết quả của lượt chạy mới nhất trong `workspaces/CFG_LTC_NY_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
   - Đọc thêm `tuning_notes.txt` của **3 run gần nhất** để biết lần trước đã thay đổi gì và kỳ vọng gì — tránh lặp lại thử nghiệm đã thất bại.
   - Nếu tồn tại file `workspaces/CFG_LTC_NY_V3_5/BEST_CONFIG.md`, đọc để lấy **mốc so sánh (Baseline)** tốt nhất hiện có.

2. **Phân tích Hiệu suất (Performance Analysis):**
   - So sánh `Composite Score`, `Win Rate`, `Val Loss` của lượt mới nhất với Baseline.
   - Đánh giá bias tín hiệu: Mô hình có đang **thiên lệch Buy/Sell** quá nhiều không? (Tỷ lệ Buy:Sell lý tưởng ≈ 45:55 đến 55:45)
   - Phát hiện **Overfitting**: Train loss giảm nhưng Val loss tăng?
   - Nếu `Composite Score` của run mới **cao hơn Baseline**, hãy cập nhật file `workspaces/CFG_LTC_NY_V3_5/BEST_CONFIG.md` với config và score mới.

3. **Đánh giá & Điều chỉnh Features (Feature Engineering):**
   - **Phiên NY (New York):** LTC chịu ảnh hưởng mạnh bởi tin tức vĩ mô Mỹ và chứng khoán Mỹ mở cửa.
   - Các chỉ số đang dùng: BTC, ETH, USTEC, DXY... Tự đánh giá sự đóng góp của từng chỉ số.
   - *Chiến lược:* Nếu mô hình chững lại, thử **THÊM** features đo lường biến động (Volatility) như `bb_width`, `vroc`, hoặc Macro khác; **HOẶC LOẠI BỎ** features nghi ngờ gây nhiễu. Không giữ nguyên bộ features nếu điểm số không tăng sau 3 lượt liên tiếp.

4. **Ra quyết định Siêu tham số (Hyperparameter Strategy):**
   - Không gian tìm kiếm gợi ý:
     + `WINDOW_SIZE` (độ dài chuỗi nhìn lại): Thử trong khoảng **15 - 120**.
     + `LEARNING_RATE`: Thử tinh chỉnh trong khoảng **1e-5 đến 5e-4**.
     + `BATCH_SIZE`: 32, 64, 128, 256.
     + `D_MODEL` / `NUM_LAYERS`: 32/2, 64/3, 128/4.
     + `TP_PCT` / `SL_PCT`: Điều chỉnh risk/reward ratio.
   - **NGUYÊN TẮC A/B TESTING — BẮT BUỘC:** Mỗi lượt config mới, **CHỈ THAY ĐỔI TỐI ĐA 2 THAM SỐ** so với lượt trước để cô lập tác động. Nếu thay đổi nhiều tham số cùng lúc và kết quả xấu đi, bạn sẽ không biết nguyên nhân từ đâu.

5. **Early Stopping (Dừng Task):**
   - Nếu đã thử thay đổi tuần tự nhưng `Composite Score` không vượt qua Baseline trong **25 lượt gần nhất**, hãy tắt task: sửa `.agent/tasks.json`, tìm id `ltc_ny_auto_tuning` và đặt `"enabled": false`. Báo cáo Telegram và gọi `--done`.

---


## BƯỚC 3: Quản lý Hàng Đợi (Queue Management) & Chuẩn bị Data Trước

Mục tiêu: Đảm bảo có sẵn dữ liệu cho `client1` chạy tiếp theo, nhưng KHÔNG ĐƯỢC CHUẨN BỊ THỪA.
Kiểm tra thư mục `workspaces/CFG_LTC_NY_V3_5/runs/`:
- Tìm các `<RUN_ID>` đã có thư mục `data/tensors/`, nhưng CHƯA CÓ file `results/training_metrics_v3.json` (tức là chưa chạy xong).
- Đối chiếu với kết quả Bước 1: Loại trừ những `<RUN_ID>` mà `client1` đang BUSY chạy.
- Còn lại chính là **HÀNG ĐỢI (Pending Runs)**.

**Xử lý:**
- **NGUYÊN TẮC: NẾU ĐÃ CÓ HÀNG ĐỢI (DÙ CHỈ CÒN 1 RUN), TUYỆT ĐỐI KHÔNG ĐƯỢC TẠO HAY CHUẨN BỊ THÊM RUN MỚI.**
- CHỈ KHI HÀNG ĐỢI HOÀN TOÀN RỖNG (0 runs), bạn MỚI CẦN TẠO 1 RUN MỚI:
  1. Sinh `<RUN_ID>` mới theo format `run_YYYYMMDD_HHMMSS_v3_ny_X` (X là số thứ tự).
  2. Tạo thư mục `workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/` và copy `base_config.json` thành `config.json`. Áp dụng các quyết định từ **Bước 2.4** vào `config.json` mới. **BẮT BUỘC KHÔNG SỬA `base_config.json` GỐC!**
     - Tạo thêm file **`tuning_notes.txt`** trong cùng thư mục run, viết đúng **3-5 câu** theo mẫu:
       ```
       Run: <RUN_ID>
       Thay đổi so với run trước: <tên tham số cũ → giá trị mới>
       Lý do: <tại sao nghĩ rằng thay đổi này sẽ cải thiện?>
       Kỳ vọng: <Composite Score tăng? Win Rate tăng? Bias giảm?>
       Baseline hiện tại: <Composite Score tốt nhất đang có>
       ```
     - File này giúp lần gọi tiếp theo đọc lại lịch sử suy luận, tránh lặp lại thử nghiệm đã thất bại.
  3. Chạy hai lệnh sau để **CHUẨN BỊ TENSOR** trước:
     ```
     python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json
     python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json
     ```
  4. Commit và đẩy lên Git:
     ```
     git add . && git commit -m "auto-tuning LTC NY data ready: <RUN_ID>" && git push
     ```

---

## BƯỚC 4: Điều Phối (Dispatching) cho `client1`

- **Nếu `client1` đang BUSY**:
  Bạn đã làm xong nhiệm vụ chuẩn bị data ở Bước 3. Thông báo Telegram: "`client1` đang bận, đã chuẩn bị sẵn data cho `<RUN_ID>` vào hàng đợi" và gọi `--done` để kết thúc.
- **Nếu `client1` đang IDLE**:
  Lấy `<RUN_ID>` từ Hàng Đợi (hoặc vừa tạo xong ở Bước 3) và phát lệnh cho `client1`:
  ```
  python src/orchestration/host_controller.py train --client-id client1 --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json --script src/training_v3/train_v3.py --scratch --run-id <RUN_ID>
  ```

Chỉ kết thúc và gọi `--done` sau khi:
1. Đã chuẩn bị xong data (nếu cần).
2. Phát lệnh và thấy `client1` phản hồi trạng thái BUSY (nếu có giao việc).
3. Thông báo đầy đủ kết quả, giả thuyết và hành động lên Telegram.

### Điều chỉnh Lịch trình (Tuỳ chọn)
Nếu quá trình crawling mất nhiều thời gian hoặc muốn theo dõi kết quả sau N phút, hãy tự sửa trường `nextRunTime` của task `ltc_ny_auto_tuning` trong file `.agent/tasks.json` thành `(timestamp_hiện_tại + N * 60) * 1000`. Nếu không sửa, Extension sẽ tự lặp lại theo `intervalMinutes` mặc định.

---

## BƯỚC 5: Dọn dẹp ổ cứng (Storage Cleanup)

**BẮT BUỘC** chạy script dọn dẹp sau khi đã hoàn thành mọi thứ để xoá bớt Tensors của các run đã hoàn thành cũ (tránh tràn đĩa):
```
python scripts/cleanup_host_storage.py
```
Ghi nhận số GB rác đã dọn dẹp vào nội dung báo cáo Telegram cuối cùng.

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Trong quá trình thực hiện, bạn có thể gọi lệnh này nhiều lần để cập nhật tiến độ:
>   `python .agent/send_to_tele.py "<Nội_dung_cập_nhật>"`
> - Khi đã hoàn tất toàn bộ tiến trình (sau khi đã giao việc cho Client), **BẮT BUỘC** chạy lệnh cuối cùng với flag `--done`:
>   `python .agent/send_to_tele.py "<Kết_quả_cuối_cùng>" --done`


__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__
