# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING LTC WEEKEND BRAIN (CỤC BỘ)

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `ltc_weekend_auto_tuning_local`). Bạn đóng vai trò **Kỹ sư AI Quant khắt khe, không bao giờ bỏ cuộc** trên **máy Local** để tìm cấu hình tốt nhất cho bộ não `CFG_LTC_WEEKEND_V3_5`.

---

## BƯỚC 1: Thu thập Ngữ cảnh & Lịch sử (Context Gathering)

1. **Đọc Lịch sử & Baseline:**
   - Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_LTC_WEEKEND_V3_5/runs/<LATEST_RUN_ID>/results/training_metrics_v3.json`.
   - Đọc `workspaces/CFG_LTC_WEEKEND_V3_5/WEEKEND_TRAINING_DIARY.md` (nếu có) để nắm bắt dòng suy nghĩ hiện tại và các ý tưởng bạn đã thử nghiệm trước đó.
   - Nếu tồn tại file `workspaces/CFG_LTC_WEEKEND_V3_5/BEST_CONFIG.md`, đọc để lấy **mốc so sánh (Baseline)** tốt nhất hiện có.

2. **Phân tích Hiệu suất & Nghĩ ra ý tưởng mới (Expert Ideation):**
   - Hãy suy nghĩ như một chuyên gia: Thị trường cuối tuần có thanh khoản thấp và biên độ hẹp. Tín hiệu trend thường là giả. Cần ưu tiên các chiến lược Scalping/Reversal.
   - **Đề xuất ít nhất 1 ý tưởng tối ưu hóa hoàn toàn mới hoặc điều chỉnh logic** (VD: Điều chỉnh TP/SL hẹp hơn, thay đổi `WINDOW_SIZE` để bắt nhịp nhanh, hoặc sử dụng thêm các feature đo Volatility Regime).

3. **Cập nhật Nhật ký Ý Tưởng (Training Diary):**
   - Cập nhật thêm nội dung vào cuối file `workspaces/CFG_LTC_WEEKEND_V3_5/WEEKEND_TRAINING_DIARY.md`.
   - Nội dung cập nhật phải tuân theo định dạng:
     ```markdown
     ### [Thời gian hiện tại] - Lượt đánh giá Run: <LATEST_RUN_ID>
     - **Kết quả Run trước:** Composite Score = X, Win Rate = Y%.
     - **Phân tích chuyên gia:** <Tại sao mô hình lại đạt/không đạt điểm cao? Sự cố ở cuối tuần là gì?>
     - **Ý tưởng thử nghiệm tiếp theo:** <Trình bày ý tưởng mới: tham số, kiến trúc, feature?>
     - **Giả thuyết (Hypothesis):** <Kỳ vọng ý tưởng mới sẽ giải quyết được vấn đề gì?>
     ```
   - **LƯU Ý QUAN TRỌNG:** Sau khi cập nhật file Diary, **BẮT BUỘC ĐẨY LÊN HUGGINGFACE NGAY LẬP TỨC**:
     ```
     python scripts/sync_workspaces.py push CFG_LTC_WEEKEND_V3_5
     ```

4. **Ra quyết định Siêu tham số (Hyperparameter Strategy):**
   **KHO VŨ KHÍ:**
   - *Architecture:* `POOLING` ("mean" | "attention"), `CLS_HEAD` ("simple" | "residual"), `LAYER_DROP` (0.0-0.3)
   - *Basics:* `WINDOW_SIZE` (15, 30, 45), `MAX_HOLD_BARS` (10, 15, 20), `TP_PCT`, `SL_PCT`.

---

## BƯỚC 2: Quản lý Hàng Đợi (Queue Management) & Chuẩn bị Data Trước

- Kiểm tra thư mục `workspaces/CFG_LTC_WEEKEND_V3_5/runs/` tìm HÀNG ĐỢI.
- Nếu Hàng Đợi rỗng, tạo Run mới `run_YYYYMMDD_HHMMSS_v3_weekend_auto_X`.
- Chuẩn bị Tensor:
  ```
  python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_WEEKEND_V3_5/runs/<RUN_ID>/config.json
  python scripts/upload_v3_dataset.py --no-push --config workspaces/CFG_LTC_WEEKEND_V3_5/runs/<RUN_ID>/config.json
  ```

---

## BƯỚC 3: Giám sát & Điều phối Huấn Luyện Cục Bộ (Local Dispatching & Monitoring)

1. **Giám sát Tiến trình:** Kiểm tra `train_v3.py`. Nếu treo > 4h hoặc log đứng im > 20p thì KILL và điều tra.
2. **Điều phối:**
   - **Nếu máy đang BUSY**: Thông báo Telegram và gọi `--done`.
   - **Nếu máy đang IDLE**: Lấy `<RUN_ID>` từ Hàng Đợi và phát lệnh chạy ẩn:
     ```powershell
     Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && python src/training_v3/train_v3.py workspaces/CFG_LTC_WEEKEND_V3_5/runs/<RUN_ID>/config.json --session weekend --scratch --run-id <RUN_ID> && python .agent/notify_done.py ltc_weekend_training_done`""
     ```

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Báo cáo cuối cùng: `python .agent/send_to_tele.py "🚀 [Weekend Expert] Đã nảy ra ý tưởng mới: <tóm tắt>. Đang train <RUN_ID>..." --done`
