# NHIỆM VỤ ĐỊNH KỲ (HOST): AUTO-TUNING LTC NY BRAIN (PHÂN TÁN)

Hệ thống sẽ gọi bạn chạy lại prompt này định kỳ mỗi 10 phút một lần. Trách nhiệm của bạn là đóng vai trò một Kỹ sư AI tự động hóa trên máy HOST để điều phối, đi tìm cấu hình và phương án tốt nhất cho bộ não `CFG_LTC_NY_V3_5` và giao việc cho **`client1`** và **`clientGH`**.

Hãy thực thi nghiêm ngặt theo các bước sau trong mỗi lần được gọi:

---

## BƯỚC TIỀN XỬ LÝ: Đồng bộ kết quả mới nhất từ HuggingFace về HOST

**BẮT BUỘC chạy lệnh này đầu tiên**, trước khi làm bất cứ điều gì khác, để đảm bảo dữ liệu trên HOST là mới nhất:
```
python scripts/sync_workspaces.py pull CFG_LTC_NY_V3_5
```

Sau đó mới tiếp tục các bước bên dưới.

---

---

## BƯỚC 1: Đánh giá Năng lực Cụm (Cluster Status)

Kiểm tra cả hai máy `client1` và `clientGH` để xem có máy nào đang rảnh (IDLE) hay bận (BUSY):
```
python src/orchestration/host_controller.py listen --client-id client1 --time 10
python src/orchestration/host_controller.py listen --client-id clientGH --time 10
```
Ghi nhận danh sách máy rảnh và máy bận.

---

## BƯỚC 2: Kiểm tra Kết quả & Đánh giá Hội tụ (Góc nhìn Quant Expert)

Đọc file `training_metrics_v3.json` trong thư mục `runs/` mới nhất. Dựa vào phân tích, **BẠN PHẢI ĐÓNG VAI TRÒ LÀ MỘT CHUYÊN GIA AI & ĐỊNH LƯỢNG TÀI CHÍNH**.

### 2.1. Kiểm tra Khả năng Hội Tụ
- So sánh kết quả mới nhất với toàn bộ lịch sử file metrics trong `workspaces/CFG_LTC_NY_V3_5/runs/`.
- Nếu **Composite Score không còn cải thiện qua 25 lần chạy**, hoặc mọi hướng tinh chỉnh hợp lý đã cạn kiệt -> Kết luận BÃO HOÀ.
  ```
  Rename-Item .agent/periodic_prompt_host.md .agent/periodic_prompt_host.DONE.md
  ```
  Báo cáo lý do dừng lên Telegram và gọi `--done`.

### 2.2. Đưa ra Giả thuyết (Hypothesis) cho lượt chạy tiếp theo
- Dựa trên lịch sử, rút ra bài học (Sự kết hợp nào tốt? Cái nào gây sụp đổ?).
- Đưa ra giả thuyết toán học rõ ràng cho lần chạy tới.
- (Bạn chỉ áp dụng giả thuyết này ở BƯỚC 3 nếu cần tạo Run mới).

---

## BƯỚC 3: Quản lý Hàng Đợi (Queue Management) & Chuẩn bị Data Trước

Mục tiêu: Luôn có sẵn ít nhất 1-2 lượt chạy (runs) ĐÃ ĐƯỢC CHUẨN BỊ TENSOR để giao ngay cho Client khi rảnh.
Kiểm tra thư mục `workspaces/CFG_LTC_NY_V3_5/runs/`:
- Tìm các `<RUN_ID>` đã có thư mục `data/tensors/` hoặc đã tạo, nhưng CHƯA CÓ file `results/training_metrics_v3.json` (tức là chưa chạy xong).
- Đối chiếu với kết quả Bước 1: Loại trừ những `<RUN_ID>` mà Client đang "BUSY" đang chạy.
- Còn lại chính là **HÀNG ĐỢI (Pending Runs)**.

**Xử lý:**
- Nếu Hàng Đợi rỗng (hoặc quá ít), bạn CẦN TẠO RUN MỚI:
  1. Sinh `<RUN_ID>` mới theo giả thuyết ở Bước 2.2.
  2. Tạo thư mục `runs/<RUN_ID>/` và copy/sửa đổi `base_config.json` thành `config.json`.
  3. BẮT BUỘC KHÔNG SỬA `base_config.json` GỐC!
  4. Chạy hai lệnh sau để CHUẨN BỊ TENSOR trước:
     ```
     python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json
     python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json
     ```
  5. Commit và đẩy lên Git:
     ```
     git add . && git commit -m "auto-tuning LTC NY data ready: <RUN_ID>" && git push
     ```

---

## BƯỚC 4: Điều Phối (Dispatching)

- **Nếu KHÔNG CÓ máy nào rảnh (Cả hai đều BUSY)**: 
  Bạn đã làm xong nhiệm vụ chuẩn bị data ở Bước 3. Thông báo Telegram: "Cả hai Client đều bận, đã chuẩn bị sẵn data cho <RUN_ID> vào hàng đợi" và gọi `--done` để kết thúc.
- **Nếu CÓ máy rảnh (IDLE)**:
  Lấy `<RUN_ID>` từ Hàng Đợi (hoặc cái vừa tạo xong ở Bước 3) và phát lệnh cho máy rảnh:
  ```
  python src/orchestration/host_controller.py train --client-id <client_rảnh> --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json --script src/training_v3/train_v3.py --scratch --run-id <RUN_ID>
  ```
  *(Lặp lại nếu có nhiều máy rảnh và nhiều Run trong hàng đợi)*

Chỉ kết thúc và gọi `--done` sau khi:
1. Đã chuẩn bị xong data (nếu cần).
2. Phát lệnh và thấy Client phản hồi trạng thái BUSY (nếu có giao việc).
3. Thông báo đầy đủ kết quả, giả thuyết và hành động lên Telegram.

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Trong quá trình thực hiện, bạn có thể gọi lệnh này nhiều lần để cập nhật tiến độ:
>   `python .agent/send_to_tele.py "<Nội_dung_cập_nhật>"`
> - Khi đã hoàn tất toàn bộ tiến trình (sau khi đã giao việc cho Client), **BẮT BUỘC** chạy lệnh cuối cùng với flag `--done`:
>   `python .agent/send_to_tele.py "<Kết_quả_cuối_cùng>" --done`


__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__
