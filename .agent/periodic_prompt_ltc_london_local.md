# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING LTC LONDON BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `ltc_london_auto_tuning_local`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy Local** để tìm cấu hình tốt nhất cho bộ não `CFG_LTC_LONDON_V3_5`. 

## BƯỚC 1: Phân tích Lịch sử & Tư duy Tối ưu hóa (Quant/ML Expert)

Thay vì đoán mò ngẫu nhiên, bạn phải phân tích có hệ thống dựa trên lịch sử để tìm ra hướng tối ưu (Gradient of Improvement).

1. **Thu thập Ngữ cảnh (Context Gathering):**
   - Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_LTC_LONDON_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
   - Nếu có, HÃY KIỂM TRA file ghi nhận kết quả tốt nhất (ví dụ các run tốt nhất trong quá khứ) để lấy mốc so sánh (Baseline).

2. **Đánh giá Khắt Khe (Strict Evaluation):**
   - So sánh `Composite Score`, `Win Rate`, `Loss` của lượt mới nhất với Baseline. Đừng chỉ nhìn vào Score, một kết quả thực sự tốt bắt buộc phải có Win Rate >= 65%. 
   - Nếu mô hình có Score cao nhưng Win Rate thấp, đó là một mô hình đánh cược (Gambling). Bạn phải nhận diện và lên phương án khắc phục ngay.
   - Đánh giá cực kỳ khắt khe phân phối tín hiệu: Mô hình có đang bị bias (chỉ BUY hoặc chỉ SELL) không? Có bị overfit không? Bất kỳ dấu hiệu nào của Overfitting đều phải bị trừng phạt bằng cách đổi cấu hình.

3. **Đánh giá & Điều chỉnh Features (Feature Engineering):**
   - **Phiên London (07:00 - 13:00 UTC):** LTC (Litecoin) trong phiên London thường đi theo sự dẫn dắt của BTC và ETH, với dòng tiền đổ vào từ châu Âu.
   - Các chỉ số đang có: BTCUSDT, ETHUSDT, LTCBTC... Hãy tự đánh giá sự đóng góp của chúng. 
   - *Chiến lược:* Nếu mô hình đang chững lại, hãy thử **THÊM** các features đo lường biến động (Volatility) hoặc tương quan (corr) vào `config.json`; HOẶC **LOẠI BỎ** các features có vẻ gây nhiễu. Đừng giữ nguyên một bộ features nếu điểm số không tăng.

4. **Ra quyết định & Sáng tạo Liên tục (Continuous Innovation):**
   - Không gian tìm kiếm cơ bản: `WINDOW_SIZE`, `D_MODEL`, `NUM_LAYERS`, `BATCH_SIZE`, `LEARNING_RATE`, `TP_PCT`, `SL_PCT`.
   - NGUYÊN TẮC: Thay đổi 1-2 tham số để đo lường. TUY NHIÊN, nếu mô hình bị kẹt quá lâu, hãy mạnh dạn **Phá vỡ Quy tắc (Think Outside the Box)**. 
   - Hãy liên tục đưa ra các ý tưởng mới: Thử kiến trúc dị (D_MODEL siêu nhỏ hoặc siêu to đi kèm Dropout cực đại), đảo lộn biên độ chốt lời cắt lỗ, kết hợp các indicator theo những cách điên rồ nhất. Bạn phải hành động như một Quant Researcher thực thụ, không ngừng thử nghiệm cái mới.

5. **Chống Early Stopping (Chiến đấu đến cùng):**
   - **TUYỆT ĐỐI KHÔNG TẮT TASK SỚM.** Bạn phải duy trì trạng thái huấn luyện và đưa ra ý tưởng mới liên tục ít nhất cho đến 07:00 AM sáng (giờ Local).
   - Tuyệt đối không bao giờ được phép báo cáo "Đã hết ý tưởng". Nếu hết ý tưởng, hãy đập đi làm lại hoặc thử những ý tưởng rủi ro cao nhất. Phải chạy cho đến khi mặt trời mọc!

## BƯỚC 2: Chuẩn bị dữ liệu (Hàng Đợi)
Kiểm tra `workspaces/CFG_LTC_LONDON_V3_5/runs/`. Những thư mục chưa có `training_metrics_v3.json` là Pending Runs.
Nếu hàng đợi rỗng:
1. Tạo `<RUN_ID>` mới (vd: `run_YYYYMMDD_HHMMSS_v3_ldn_X`), tạo thư mục và copy `base_config.json` thành `config.json`. 
   - Áp dụng các quyết định từ Bước 1.4 vào `config.json` mới. **BẮT BUỘC KHÔNG SỬA base_config.json gốc!**
   - Tạo thêm một file `tuning_notes.txt` trong thư mục run mới này, viết đúng 2-3 câu tóm tắt: "Lượt này thay đổi tham số gì? Kỳ vọng điều gì xảy ra?". Điều này giúp bạn của tương lai đọc lại và hiểu mạch tư duy.
2. Chạy:
```
python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json
python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json --no-push
```
3. (Tùy chọn) Ghi chép trạng thái vào log cục bộ.

## BƯỚC 3: Training Cục bộ
Lấy RUN_ID từ hàng đợi và chạy:
```
python src/training_v3/train_v3.py workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json --session london --scratch --run-id <RUN_ID>; python .agent/notify_done.py ltc_london_training_done
```
(Lưu ý: Gọi `notify_done.py` sau lệnh training giúp kích hoạt luồng nhận biết training xong để nhận nhiệm vụ tiếp theo ngay lập tức).

## BƯỚC 4: Tự động điều chỉnh lịch trình (Tuỳ chọn)
Nếu bạn nhận thấy quá trình crawling mất nhiều thời gian, hoặc bạn muốn theo dõi kết quả sau 5 phút, 15 phút, bạn có thể tự thay đổi thời gian kích hoạt task tiếp theo bằng cách:
Sửa trường `nextRunTime` của task `ltc_london_auto_tuning_local` trong file `.agent/tasks.json` thành `(timestamp hiện tại + N * 60) * 1000`. Nếu không sửa, Extension sẽ tự lặp lại theo `intervalMinutes` mặc định.

## BƯỚC 5: Nhả trạng thái rảnh
Sau khi mọi thứ chạy ổn, Gửi Telegram và báo xong (BẮT BUỘC):
```
python .agent/send_to_tele.py "<Báo cáo tình hình>" --done
```
