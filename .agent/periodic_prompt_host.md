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

## BƯỚC 1: Kiểm tra trạng thái các Client

Kiểm tra cả hai máy `client1` và `clientGH` để xác định máy nào đang rảnh:
```
python src/orchestration/host_controller.py listen --client-id client1 --time 10
python src/orchestration/host_controller.py listen --client-id clientGH --time 10
```

Phân tích kết quả:
- **Cả hai đều BUSY**: BỎ QUA phiên này, kết thúc ngay.
- **Ít nhất một máy IDLE**: Ghi nhận máy nào đang rảnh, tiếp tục BƯỚC 2.

> Lưu ý: Nếu cả hai đều IDLE, ưu tiên giao lượt chạy *mới nhất* cho `client1`; lượt chạy *song song/thử nghiệm khác* cho `clientGH`.

---

## BƯỚC 2: Kiểm tra kết quả huấn luyện mới nhất

Đọc file `training_metrics_v3.json` trong thư mục `runs/` mới nhất (sắp xếp theo tên để tìm run cuối cùng).

- **2.1 Chưa có kết quả nào**: Chuyển thẳng sang BƯỚC 4.
- **2.2 Đã có kết quả**: Đọc và phân tích đầy đủ các chỉ số, chuyển sang BƯỚC 3.

---

## BƯỚC 3: Review, Kiểm tra Hội tụ & Sửa đổi Cấu hình (Góc nhìn Chuyên gia)

Dựa vào phân tích ở Bước 2.2, **BẠN PHẢI ĐÓNG VAI TRÒ LÀ MỘT CHUYÊN GIA AI & ĐỊNH LƯỢNG TÀI CHÍNH (QUANT EXPERT) HÀNG ĐẦU**.

### 3.1. Kiểm tra Khả năng Hội Tụ — Có nên tiếp tục không?
Hãy so sánh kết quả mới nhất với toàn bộ lịch sử file metrics trong `workspaces/CFG_LTC_NY_V3_5/runs/` và đánh giá xu hướng:
- Nếu bạn nhận thấy **Composite Score không còn cải thiện đáng kể qua ít nhất 25 lần chạy liên tiếp**, hoặc **mọi hướng tinh chỉnh hợp lý đã được thử**, hãy kết luận rằng không gian tìm kiếm đã bão hoà.
- **Nếu kết luận là BÃO HOÀ**: Đổi tên file này thành `.agent/periodic_prompt_host.DONE.md` bằng lệnh sau, thông báo Telegram lý do cụ thể và kết thúc:
  ```
  Rename-Item .agent/periodic_prompt_host.md .agent/periodic_prompt_host.DONE.md
  ```
  Sau đó báo cáo lý do dừng lên Telegram và gọi `--done`.
- **Nếu chưa bão hoà**: Tiếp tục bước 3.2.

### 3.2. Đánh giá và Tinh chỉnh Chiến thuật (Nhiệm vụ CỐT LÕI)
**ĐIỀU QUAN TRỌNG NHẤT TRONG TOÀN BỘ NHIỆM VỤ NÀY:** Bạn phải đóng vai trò là một **Chuyên gia AI & Định lượng Tài chính (Quant Expert) cực kỳ giàu kinh nghiệm**. Trách nhiệm của bạn KHÔNG PHẢI là thay đổi tham số một cách ngẫu nhiên hay máy móc.

Bạn BẮT BUỘC phải:
1. **Đánh giá các tình huống đã thử nghiệm**: Nhìn nhận lại lịch sử các cấu hình trước đó. Sự kết hợp tham số nào đã mang lại kết quả tốt? Sự thay đổi nào làm mô hình sụp đổ? (Ví dụ: Thêm tính năng Vàng có làm nhiễu không? Bắt đỉnh đáy bằng RSI có hiệu quả không?)
2. **Đưa ra Giả thuyết (Hypothesis)**: Bằng tư duy sắc bén, hãy đưa ra một gợi ý/giả thuyết rõ ràng cho lần chạy tiếp theo. Bạn định giải quyết vấn đề gì ở lượt chạy này và TẠI SAO lại điều chỉnh như vậy? Mọi quyết định phải dựa trên tư duy toán học, tránh xa overfitting.

Những thay đổi BẠN CÓ QUYỀN VÀ NÊN làm:
- **Thay đổi Input Features**: Thử nghiệm thêm/bớt chỉ số vĩ mô trong `MACRO_FEATURES` (DXYm, Crypto, Vàng...).
- **Thay đổi Thông số Trading**: Tinh chỉnh `TP_PCT`, `SL_PCT`, `MAX_HOLD_BARS`.
- **Thay đổi Hyperparameters**: Điều chỉnh `WINDOW_SIZE`, `LEARNING_RATE`, `BATCH_SIZE`...
- **Thay đổi Code**: Sửa đổi logic trong `src/` (thuật toán Feature, kiến trúc Model, hàm Loss) nếu có ý tưởng đột phá.

> **TUYỆT ĐỐI KHÔNG ĐƯỢC CHỈNH SỬA FILE `base_config.json` GỐC!**
>
> Khi quyết định thay đổi, BẮT BUỘC phải:
> 1. Sinh chuỗi thời gian mới (VD: `20260422_143008`) và TẠO THƯ MỤC: `workspaces/CFG_LTC_NY_V3_5/runs/run_20260422_143008_v3/`
> 2. Copy `base_config.json` vào đó, đặt tên `config.json`. Thực hiện thay đổi trên file mới này.

---

## BƯỚC 4: Tạo Lượt Chạy Mới & Giao Việc Cho Client(s)

**4.1. Chuẩn bị Tensor** (thay `<RUN_ID>` bằng run vừa tạo):
```
python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json
python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json
```

**4.2. Commit Git**:
```
git add . && git commit -m "auto-tuning LTC NY: <RUN_ID>" && git push
```

**4.3. Giao Việc Cho Client(s)**:
- Nếu chỉ **1 máy rảnh** (kết quả từ Bước 1), giao cho đúng máy đó:
  ```
  python src/orchestration/host_controller.py train --client-id <client_rảnh> --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID>/config.json --script src/training_v3/train_v3.py --scratch --run-id <RUN_ID>
  ```
- Nếu **cả hai máy đều rảnh**, tạo thêm một run thứ hai with variant cấu hình khác biệt (ví dụ thử hyperparameter khác) và giao song song:
  ```
  python src/orchestration/host_controller.py train --client-id client1  --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID_A>/config.json --script src/training_v3/train_v3.py --scratch --run-id <RUN_ID_A>
  ```
  ```
  python src/orchestration/host_controller.py train --client-id clientGH --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID_B>/config.json --script src/training_v3/train_v3.py --scratch --run-id <RUN_ID_B>
  ```

**4.4. Thông báo Telegram**: Báo cáo ngắn gọn: kết quả đánh giá, thay đổi gì, Run ID mới, máy nào được giao việc.

Chỉ kết thúc và gọi `--done` sau khi client đã xác nhận nhận lệnh (trạng thái BUSY trên log)!

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Trong quá trình thực hiện, bạn có thể gọi lệnh này nhiều lần để cập nhật tiến độ:
>   `python .agent/send_to_tele.py "<Nội_dung_cập_nhật>"`
> - Khi đã hoàn tất toàn bộ tiến trình (sau khi đã giao việc cho Client), **BẮT BUỘC** chạy lệnh cuối cùng với flag `--done`:
>   `python .agent/send_to_tele.py "<Kết_quả_cuối_cùng>" --done`


__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__
