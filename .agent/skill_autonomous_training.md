# Kỹ năng Đào tạo Tự động (Autonomous Training Skill)

Skill này hướng dẫn Agent cách khởi chạy và giám sát quá trình huấn luyện tự động (Autonomous Training) sử dụng hàm mới `autonomous_training_loop.py`. Hệ thống này sẽ tự động thu thập quyết định từ AI (thông qua LLM) để chọn phiên giao dịch cần huấn luyện tiếp theo (Asian, London, NY) và tự động chuẩn bị dữ liệu, cấu hình trước khi chạy.

## 1. Mục đích
- Loại bỏ quá trình khởi chạy thủ công.
- Đảm bảo tính liên tục của quá trình training (tự động luân chuyển phiên và tái thiết lập cấu hình theo quyết định của AI).
- Ghi log và báo cáo toàn diện.

## 2. Cách khởi chạy
Để bắt đầu vòng lặp huấn luyện tự động, hãy thực thi script Python chính:

```bash
python autonomous_training_loop.py
```

*Lưu ý:* Script này chạy dưới dạng tiến trình chặn (blocking) vì nó duy trì một vòng lặp `while True`. Nếu cần chạy nền, hãy sử dụng các file `.bat` hoặc lệnh tương ứng trên Windows.

## 3. Quy trình bên trong (Làm việc như thế nào?)
1. **Lấy Quyết Định Khởi Đầu:** `get_ai_decision()` gọi script `.agent/skill_training_report.py` để lấy report và yêu cầu AI trả về định dạng JSON (chọn `target_session` và cấu hình).
2. **Cập nhật Config:** `update_config()` ghi lại các tuỳ chỉnh parameter mới vào tệp config của phiên tương ứng (ví dụ: `bot_config_v6_ltc_asian.json`).
3. **Chuẩn bị Dữ liệu:** Chạy `scripts/prepare_v6_dataset.py` để lấy dữ liệu từ HF dựa trên config mới.
4. **Huấn Luyện (Training):** Gọi `src/training_v6/train_v6.py` trong một subprocess.
5. **Pre-fetch AI:** Ngay trong lúc mô hình đang huấn luyện, hệ thống tiếp tục gọi AI để quyết định và chuẩn bị dữ liệu cho phiên tiếp theo.
6. **Lặp lại:** Quá trình tự động tuần hoàn.

## 4. Xử lý lỗi thường gặp
- Nếu script báo **"Không tìm thấy JSON trong phản hồi của AI"**, hãy kiểm tra file log hoặc đảm bảo prompt template `.agent/strategy_prompt_LTC.md` có chứa ràng buộc yêu cầu đầu ra là JSON.
- Đảm bảo môi trường ảo và các biến môi trường (như `PYTHONUTF8`, `PYTORCH_CUDA_ALLOC_CONF`) được giữ nguyên như thiết lập mặc định trong script.

## 5. Giám sát
Bạn có thể đọc các file log trong thư mục `workspaces/CFG_LTC_<SESSION>_V6/runs/<run_id>/` để theo dõi tiến trình:
- `train_v6.log`: Quá trình huấn luyện chi tiết.
- `prepare_dataset.log`: Quá trình tải và xử lý dataset.
