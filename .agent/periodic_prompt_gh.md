# NHIỆM VỤ ĐỊNH KỲ (GH): AUTO-TUNING LTC ASIAN BRAIN (CỤC BỘ)

Hệ thống sẽ gọi bạn chạy lại prompt này định kỳ mỗi 10 phút một lần. Trách nhiệm của bạn là đóng vai trò một Kỹ sư AI tự động hóa trên **máy GH** để điều phối, đi tìm cấu hình và phương án tốt nhất cho bộ não `CFG_LTC_ASIAN_V3_5`. Training chạy **trực tiếp trên máy này** (không dispatch sang máy khác).

Hãy thực thi nghiêm ngặt theo các bước sau trong mỗi lần được gọi:



## BƯỚC 1: Kiểm tra Kết quả & Đánh giá Hội tụ (Góc nhìn Quant Expert)

Đọc file `training_metrics_v3.json` trong thư mục `runs/` mới nhất. Dựa vào phân tích, **BẠN PHẢI ĐÓNG VAI TRÒ LÀ MỘT CHUYÊN GIA AI & ĐỊNH LƯỢNG TÀI CHÍNH**.

### 2.1. Kiểm tra Khả năng Hội Tụ
- So sánh kết quả mới nhất với toàn bộ lịch sử file metrics trong `workspaces/CFG_LTC_ASIAN_V3_5/runs/`.
- Nếu **Composite Score không còn cải thiện qua 25 lần chạy**, hoặc mọi hướng tinh chỉnh hợp lý đã cạn kiệt -> Kết luận BÃO HOÀ.
  ```
  Rename-Item .agent/periodic_prompt_gh.md .agent/periodic_prompt_gh.DONE.md
  ```
  Báo cáo lý do dừng lên Telegram và gọi `--done`.

### 2.2. Đưa ra Giả thuyết (Hypothesis) cho lượt chạy tiếp theo
- Dựa trên lịch sử, rút ra bài học (Sự kết hợp nào tốt? Cái nào gây sụp đổ?).
- **LƯU Ý 1 (TỔNG HỢP TRỌNG SỐ):** Khi quyết định thay đổi cho bộ mới, cần phân tích và **TỔNG HỢP** từ những bộ trọng số (hyperparameters) của các kết quả tốt nhất trước đó (ví dụ: lấy D_MODEL của top 1 kết hợp với LR của top 2 nếu thấy hợp lý). Không thay đổi các thông số một cách ngẫu nhiên.
- **LƯU Ý 2 (WINDOW_SIZE & ASIAN):** Phiên Asian volume thấp, ít nhiễu hơn London/NY. Thử nghiệm `WINDOW_SIZE` trong khoảng 15-25. Đặc biệt chú ý đến tương quan BTC/ETH/XRP trong đêm châu Á — đây là tín hiệu dẫn dắt chính. Ưu tiên giả thuyết xoay quanh `corr_60` và các chỉ số volume của BTC/XRP.
- **LƯU Ý 3 (MAX_HOLD_BARS):** Asian session nến hội tụ chậm hơn. Thử nghiệm `MAX_HOLD_BARS` 10-15 để tìm khoảng tối ưu.
- Đưa ra giả thuyết toán học rõ ràng cho lần chạy tới.
- (Bạn chỉ áp dụng giả thuyết này ở BƯỚC 2 nếu cần tạo Run mới).

---

## BƯỚC 2: Quản lý Hàng Đợi (Queue Management) & Chuẩn bị Data Trước

Mục tiêu: Luôn có sẵn ít nhất 1 lượt chạy (run) ĐÃ ĐƯỢC CHUẨN BỊ TENSOR để chạy ngay khi máy rảnh.
Kiểm tra thư mục `workspaces/CFG_LTC_ASIAN_V3_5/runs/`:
- Tìm các `<RUN_ID>` đã có thư mục `data/tensors/` hoặc đã tạo, nhưng CHƯA CÓ file `results/training_metrics_v3.json` (tức là chưa chạy xong).
- Còn lại chính là **HÀNG ĐỢI (Pending Runs)**.

**Xử lý:**
- Nếu Hàng Đợi rỗng (hoặc quá ít), bạn CẦN TẠO RUN MỚI:
  1. Sinh `<RUN_ID>` mới theo giả thuyết ở Bước 1.2.
  2. Tạo thư mục `runs/<RUN_ID>/` và copy/sửa đổi `base_config.json` thành `config.json`.
  3. BẮT BUỘC KHÔNG SỬA `base_config.json` GỐC!
  4. Chạy hai lệnh sau để CHUẨN BỊ TENSOR trước:
     ```
     python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json
     python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json
     ```
  5. Commit và đẩy lên Git:
     ```
     git add . && git commit -m "auto-tuning LTC ASIAN data ready: <RUN_ID>" && git push
     ```

---

## BƯỚC 3: Thực thi Training Cục bộ (Local Execution)

**Máy này tự chạy training**, không dispatch sang máy khác.

Lấy `<RUN_ID>` từ Hàng Đợi (hoặc cái vừa tạo xong ở Bước 2) và **chạy trực tiếp trên máy GH**:
```
python src/training_v3/train_v3.py --config workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json --session asian --scratch --run-id <RUN_ID>
```

Chỉ kết thúc và gọi `--done` sau khi:
1. Đã chuẩn bị xong data (nếu cần).
2. Đã khởi động training.
3. Thông báo đầy đủ kết quả, giả thuyết và hành động lên Telegram.

---

## BƯỚC 4: Dọn dẹp ổ cứng (Storage Cleanup)

**BẮT BUỘC** chạy script dọn dẹp sau khi đã hoàn thành mọi thứ để xoá bớt Tensors của các run đã hoàn thành cũ (tránh tràn đĩa):
```
python scripts/cleanup_host_storage.py
```
Ghi nhận số GB rác đã dọn dẹp vào nội dung báo cáo Telegram cuối cùng.

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Trong quá trình thực hiện, bạn có thể gọi lệnh này nhiều lần để cập nhật tiến độ:
>   `python .agent/send_to_tele.py "<Nội_dung_cập_nhật>"`
> - Khi đã hoàn tất toàn bộ tiến trình (sau khi đã bắt đầu training), **BẮT BUỘC** chạy lệnh cuối cùng với flag `--done`:
>   `python .agent/send_to_tele.py "<Kết_quả_cuối_cùng>" --done`


__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__

