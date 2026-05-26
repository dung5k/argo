# Kỹ năng Đào tạo Tự động (Autonomous Training Skill)

Skill này hướng dẫn Agent cách khởi chạy và giám sát quá trình huấn luyện tự động (Autonomous Training) sử dụng hàm mới `autonomous_training_loop.py`. Hệ thống này sẽ tự động thu thập quyết định từ AI (thông qua LLM) để chọn phiên giao dịch cần huấn luyện tiếp theo (Asian, London, NY) và tự động chuẩn bị dữ liệu, cấu hình trước khi chạy.

## 1. Mục đích
- Loại bỏ quá trình khởi chạy thủ công.
- Hỗ trợ linh hoạt cấu hình đa mã (XAG, LTC), đa phiên bản (v5, v6) và tuỳ chỉnh khoảng thời gian.
- Đảm bảo tính liên tục của quá trình training (tự động luân chuyển phiên và tái thiết lập cấu hình theo quyết định của AI).
- Ghi log và báo cáo toàn diện.

## 2. Cách khởi chạy (MỚI HỖ TRỢ THAM SỐ)
Script `autonomous_training_loop.py` hiện đã hỗ trợ truyền tham số dòng lệnh (CLI arguments) để tăng tính linh hoạt. Cú pháp chạy đầy đủ:

```bash
python autonomous_training_loop.py \
    --symbol XAG \
    --version v5 \
    --start-date "2023-01-01" \
    --end-date "2026-05-01" \
    --custom-params '{"FEATURE_ENGINEERING.FAST_HIT_BARS": 8, "TRAIN.BATCH_SIZE": 256}'
```

### Các tham số hỗ trợ:
- `--symbol`: Mã giao dịch cần chạy (Mặc định: `LTC`). Ví dụ: `XAG`, `BTC`.
- `--version`: Phiên bản kiến trúc mã (Mặc định: `v6`). Ví dụ: `v5`, `v6`.
- `--prompt-file`: Đường dẫn đến file prompt strategy (Mặc định: `.agent/strategy_prompt_<symbol>.md`).
- `--start-date` & `--end-date`: Khoảng thời gian dữ liệu training (Format: `YYYY-MM-DD`). Tham số này sẽ ép ghi đè thẳng vào `TRAIN.TRAIN_START` và `TRAIN.TRAIN_END` của file config.
- `--custom-params`: Một chuỗi JSON để ghi đè mọi thông số config bất kỳ trước khi chạy.

## 3. Quy trình bên trong (Làm việc như thế nào?)
1. **Lấy Quyết Định Khởi Đầu:** `get_ai_decision()` gọi script `.agent/skill_training_report.py` để lấy report và yêu cầu AI trả về định dạng JSON (chọn `target_session` và cấu hình).
2. **Cập nhật Config:** `update_config()` nạp các thông số từ AI kết hợp với các tham số CLI (như start/end date) để ghi lại vào tệp config của phiên tương ứng (ví dụ: `bot_config_v5_xag_asian.json`).
3. **Chuẩn bị Dữ liệu:** Chạy `scripts/prepare_v5_dataset.py` để lấy dữ liệu từ HF dựa trên config mới.
4. **Huấn Luyện (Training):** Gọi `src/training_v5/train_v5.py` trong một subprocess.
5. **Pre-fetch AI:** Ngay trong lúc mô hình đang huấn luyện, hệ thống tiếp tục gọi AI để quyết định và chuẩn bị dữ liệu cho phiên tiếp theo. Tiến trình này chạy hoàn toàn SONG SONG với việc đào tạo hiện tại.
6. **Lặp lại:** Quá trình tự động tuần hoàn.

## 4. Xử lý lỗi thường gặp
- Nếu script báo **"Không tìm thấy JSON trong phản hồi của AI"**, hãy kiểm tra file log hoặc đảm bảo prompt template `.agent/strategy_prompt_<symbol>.md` có chứa ràng buộc yêu cầu đầu ra là JSON.
- Khi nhập chuỗi `--custom-params`, hãy chắc chắn đó là định dạng JSON chuẩn (sử dụng dấu nháy kép bên trong ngoặc đơn ở shell).

## 5. Giám sát
Bạn có thể đọc các file log trong thư mục `workspaces/CFG_<SYMBOL>_<SESSION>_<VERSION>/runs/<run_id>/` để theo dõi tiến trình:
- `train_v5.log`: Quá trình huấn luyện chi tiết.
- `prepare_dataset.log`: Quá trình tải và xử lý dataset.
