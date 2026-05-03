# NHIỆM VỤ ĐỊNH KỲ (GH): AUTO-TUNING XAG ASIAN BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `xag_asian_auto_tuning`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy GH** để tìm cấu hình tốt nhất cho bộ não `CFG_XAG_ASIAN_V3_5`. 

**GIÁM SÁT SỨC KHỎE (HEALTH CHECK):**
- Nếu nhận thấy lượt chạy (Run) hiện tại kéo dài bất thường (ví dụ > 2 giờ) mà không có kết quả, phải chủ động `taskkill` tiến trình treo, thực hiện điều tra nguyên nhân qua logs (`bg_train.log` hoặc console) và kích hoạt chạy lại (Restart).

## BƯỚC 1: Phân tích Lịch sử & Tư duy Tối ưu hóa (Quant/ML Expert)

Thay vì đoán mò ngẫu nhiên, bạn phải phân tích có hệ thống dựa trên lịch sử để tìm ra hướng tối ưu (Gradient of Improvement).

1. **Thu thập Ngữ cảnh (Context Gathering):**
   - Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_XAG_ASIAN_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
   - Nếu có, HÃY KIỂM TRA file ghi nhận kết quả tốt nhất (ví dụ các run tốt nhất trong quá khứ) để lấy mốc so sánh (Baseline).

2. **Phân tích Hiệu suất (Performance Analysis) & Dọn dẹp (Cleanup/Push):**
   - So sánh `Composite Score`, `Win Rate`, `Loss` của lượt mới nhất với Baseline. 
   - Đánh giá phân phối tín hiệu: Mô hình có đang bị bias (thiên lệch) mua/bán quá nhiều không? Có bị overfit không (Train loss giảm nhưng Val loss tăng)?
   - **HÀNH ĐỘNG BẮT BUỘC (KHẮT KHE):** NẾU kết quả kém quá (Win Rate < 60% hoặc N=0, N<50, Bias Mua/Bán > 90%), HÃY XÓA NGAY thư mục run đó (`rm -rf`) để dọn dẹp dung lượng. NẾU kết quả ổn, hãy sử dụng lệnh để đồng bộ nó lên Hugging Face.
   - **BÁO CÁO TỔNG QUAN:** HÃY cập nhật một file `training_report.md` (nằm trong thư mục gốc của cấu hình). Ghi ngắn gọn tóm tắt nội dung của từng lượt thực hiện (Run ID, tham số thay đổi, kết quả đạt được, và quyết định tiếp theo).

3. **Chống Trùng Lặp (Non-overlapping Search):**
   - Đọc file `workspaces/CFG_XAG_ASIAN_V3_5/asian_tried_configs.json` (nếu chưa có thì tự tạo) để xem các bộ config nào ĐÃ ĐƯỢC CHẠY.
   - Khi nghĩ ra một config mới (các thông số TP, SL, ZERO_NOISE, D_MODEL, MACRO - bao gồm cả việc thêm/bớt mã và chỉ số mới), BẮT BUỘC phải đảm bảo nó CHƯA TỪNG tồn tại trong file này.
   - Sau khi tạo `<RUN_ID>` mới, hãy ghi cấu hình đó vào file `asian_tried_configs.json`.

4. **Ra quyết định Siêu tham số & Đánh giá:**
   - **MỆNH LỆNH TỐI THƯỢNG:** BẰNG MỌI GIÁ KHÔNG ĐƯỢC DỪNG LẠI (TRỪ KHI HẾT GIỜ). BẠN PHẢI LIÊN TỤC TÌM KIẾM GIẢI PHÁP, PHƯƠNG PHÁP, CHIẾN THUẬT MỚI (Đổi MACRO, đổi D_MODEL, đổi WINDOW_SIZE, đổi TP/SL, thêm bớt Features...) ĐỂ ĐẠT ĐƯỢC MỤC TIÊU WIN RATE > 60%. NẾU THẤT BẠI, LẬP TỨC PHÂN TÍCH VÀ THỬ HƯỚNG KHÁC!
   - Liên tục nghĩ ra các hướng khác nhau để thử nghiệm:
     + Nếu Micro-Scalping (TP=15) thất bại, hãy thử TP/SL lớn hơn (30, 40) hoặc ngược lại.
     + Nếu `ZERO_NOISE_TARGET` thất bại, hãy thử tắt nó.
     + **CẢI TIẾN ĐẦU VÀO (Macro Innovation):** Đừng chỉ bó hẹp trong các mã mặc định. Hãy chủ động đề xuất thêm hoặc loại bỏ các mã chỉ số để tối ưu tín hiệu (vd: thêm `NI225`, `HSI`, `BTCUSD` hoặc loại bỏ các mã gây nhiễu). Hãy kiểm tra tính sẵn có của mã trong hệ thống trước khi áp dụng.
     + Hãy thử thay đổi Macro Leader (vd: thêm/bớt VIXm, thay USDJPYm bằng XAUUSDm hoặc ngược lại).
     + Hãy điều chỉnh `WINDOW_SIZE` (vd: 10, 15, 30).
   - Hãy suy nghĩ logic: Tại sao lần trước thất bại? (Bias mua? -> Thêm Volatility / Giảm Window. Không có tín hiệu? -> Hạ ngưỡng TP/SL, Tăng D_MODEL để học tốt hơn).

## BƯỚC 2: Chuẩn bị dữ liệu (Hàng Đợi)
Kiểm tra `workspaces/CFG_XAG_ASIAN_V3_5/runs/`. Những thư mục chưa có `training_metrics_v3.json` là Pending Runs.
Nếu hàng đợi rỗng:
1. Tạo `<RUN_ID>` mới (vd: `run_YYYYMMDD_HHMMSS_v3_asian_X`), tạo thư mục và copy `base_config.json` thành `config.json`. 
   - Áp dụng các quyết định từ Bước 1 vào `config.json` mới (VÀ KIỂM TRA CHỐNG TRÙNG LẶP). **BẮT BUỘC KHÔNG SỬA base_config.json gốc!**
2. Chạy:
```
python scripts/crawl_crypto_v3.py workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json
python scripts/upload_v3_dataset.py --config workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json
```

## BƯỚC 3: Training Cục bộ
Lấy RUN_ID từ hàng đợi và chạy:
```
python src/training_v3/train_v3.py workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json --session asian --scratch --run-id <RUN_ID>
```

## BƯỚC 4: Tự động điều chỉnh lịch trình CHẠY LIÊN TỤC
- Để duy trì vòng lặp đào tạo không ngừng nghỉ:
  - HÃY dùng Python tự động sửa `.agent/tasks.json`, tìm task `xag_asian_auto_tuning` và đặt `"nextRunTime": 0` (để hệ thống gọi lại bạn NGAY LẬP TỨC sau khi hoàn thành lượt chạy này).
  - TUYỆT ĐỐI KHÔNG tự động chuyển `"enabled": false` trừ khi có lệnh trực tiếp từ người dùng.

## BƯỚC 5: Nhả trạng thái rảnh
Sau khi mọi thứ chạy xong (dù thành công hay thất bại), Gửi Telegram và báo xong (BẮT BUỘC):
```
python .agent/send_to_tele.py "<Báo cáo tình hình>" --done
```
