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

---

## BƯỚC 2: Kiểm tra Kết quả & Phân tích Tương quan (Quant Expert)

1. **Đọc dữ liệu**: Mở file `training_metrics_v3.json` mới nhất trong `workspaces/CFG_LTC_NY_V3_5/runs/` (thường trong thư mục `results/`). Xem xét `Composite Score`, `Win Rate` và phân phối tín hiệu (Buy/Sell).
2. **Phân tích Leading Indicators**: LTC NY bị dẫn dắt mạnh bởi BTC, ETH và chỉ số USTEC (dòng tiền Mỹ). Dựa vào lịch sử các lượt chạy, hãy tự đánh giá xem các chỉ số Macro hiện tại trong `MACRO_FEATURES` (BTC, ETH, USTEC, DXY,...) có đang đóng góp hiệu quả cho mô hình không. Nên chủ động **thêm, bớt hoặc thay thế** các chỉ số dẫn dắt trong `config.json` của lượt chạy mới nếu có lý do tin rằng một chỉ số khác sẽ phản ánh tốt hơn tương quan với LTC trong phiên NY.
3. **Đề xuất thay đổi cấu hình**: Dựa trên kết quả thực tế từ các lượt chạy, hãy tự đưa ra giả thuyết và thay đổi siêu tham số phù hợp. Không có công thức cố định — hãy tư duy như một Quant Engineer và chịu trách nhiệm về quyết định cấu hình của lượt tiếp theo.
4. **Dừng Task**: Nếu đã thử mọi cách nhưng Composite Score không cải thiện qua 25 lượt, hãy tắt task này bằng cách sửa file `.agent/tasks.json`: tìm task có id `ltc_ny_auto_tuning` và đặt `"enabled": false`. Báo cáo Telegram và gọi `--done`.

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
  2. Tạo thư mục `workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/` và copy `base_config.json` thành `config.json`. Áp dụng giả thuyết từ Bước 2.2 vào `config.json` mới. **BẮT BUỘC KHÔNG SỬA `base_config.json` GỐC!**
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
