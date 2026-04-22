# NHIỆM VỤ ĐỊNH KỲ (HOST): AUTO-TUNING LTC NY BRAIN (PHÂN TÁN)

Hệ thống sẽ gọi bạn chạy lại prompt này định kỳ mỗi 10 phút một lần. Trách nhiệm của bạn là đóng vai trò một Kỹ sư AI tự động hóa trên máy HOST để điều phối, đi tìm cấu hình và phương án tốt nhất cho bộ não `CFG_LTC_NY_V3_5` và giao việc cho **`client1`** và **`clientGH`**.

Hãy thực thi nghiêm ngặt theo các bước sau trong mỗi lần được gọi:

---

## BƯỚC 0: Kiểm tra Khả năng Hội Tụ — Có nên tiếp tục không?

Trước tiên, hãy đọc toàn bộ lịch sử file metrics trong `workspaces/CFG_LTC_NY_V3_5/runs/` và so sánh xu hướng:
- Nếu bạn nhận thấy **Composite Score không còn cải thiện đáng kể qua ít nhất 5 lần chạy liên tiếp**, hoặc **mọi hướng tinh chỉnh hợp lý đã được thử**, hãy kết luận rằng không gian tìm kiếm đã bão hoà.
- **Nếu kết luận là BÃO HOÀ**: Đổi tên file này thành `.agent/periodic_prompt_host.DONE.md` bằng lệnh sau, thông báo Telegram và kết thúc:
  ```
  Rename-Item .agent/periodic_prompt_host.md .agent/periodic_prompt_host.DONE.md
  ```
  Sau đó báo cáo lý do dừng lên Telegram và gọi `--done`.
- **Nếu chưa bão hoà**: Tiếp tục từ BƯỚC 1.

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

## BƯỚC 2: Đồng bộ và Kiểm tra kết quả huấn luyện mới nhất

Kéo kết quả mới nhất từ HuggingFace về HOST để đánh giá:
```
python scripts/sync_workspaces.py pull CFG_LTC_NY_V3_5
```

Sau đó đọc file `training_metrics_v3.json` trong thư mục `runs/` mới nhất (sắp xếp theo tên để tìm run cuối cùng).

- **2.1 Chưa có kết quả nào**: Chuyển thẳng sang BƯỚC 4.
- **2.2 Đã có kết quả**: Đọc và phân tích đầy đủ các chỉ số, chuyển sang BƯỚC 3.

---

## BƯỚC 3: Review và Sửa đổi Cấu hình (Góc nhìn Chuyên gia)

Dựa vào phân tích ở Bước 2.2, **BẠN PHẢI ĐÓNG VAI TRÒ LÀ MỘT CHUYÊN GIA AI & ĐỊNH LƯỢNG TÀI CHÍNH (QUANT EXPERT) HÀNG ĐẦU**.

Hãy suy luận sâu sắc, phân tích đa chiều các chỉ số (Win Rate, Composite Score, Sharpe, Max Drawdown nếu có) và đối chiếu với **toàn bộ lịch sử** các `runs/` trước đó để tìm ra quy luật tham số nào thực sự mang lại Alpha. Mọi quyết định phải dựa trên tư duy phản biện sắc bén, tránh overfitting.

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
- Nếu **cả hai máy đều rảnh**, tạo thêm một run thứ hai với variant cấu hình khác biệt (ví dụ thử hyperparameter khác) và giao song song:
  ```
  python src/orchestration/host_controller.py train --client-id client1  --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID_A>/config.json --script src/training_v3/train_v3.py --scratch --run-id <RUN_ID_A>
  python src/orchestration/host_controller.py train --client-id clientGH --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/<RUN_ID_B>/config.json --script src/training_v3/train_v3.py --scratch --run-id <RUN_ID_B>
  ```

**4.4. Thông báo Telegram**: Báo cáo ngắn gọn: kết quả đánh giá, thay đổi gì, Run ID mới, máy nào được giao việc.

Chỉ kết thúc và gọi `--done` sau khi client đã xác nhận nhận lệnh (trạng thái BUSY trên log)!

__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần: `python .agent/send_to_tele.py "<Nội_dung>"`. Khi hoàn tất toàn bộ, BẮT BUỘC chạy: `python .agent/send_to_tele.py "<Kết_quả>" --done`)__
