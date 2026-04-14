# Bộ Điểu Phối Tự Động (Master Scheduler)

File này sẽ được Hệ thống (VS Code Extension hoặc Cronjob) đưa vào vòng lặp gọi tự động định kỳ **10 phút / lần**.
Nhiệm vụ của bạn MỖI KHI ĐƯỢC GỌI là ĐỌC CÁC MỐC THỜI GIAN dưới đây để quyết định xem có cần thực thi các file tác vụ chi nhánh hay không.

## Nguyên tắc Vận hành:
1. Bạn có khả năng lấy thời gian hiện tại từ `<ADDITIONAL_METADATA>` thông qua hệ thống. Hãy so sánh nó với `Next Run Time` của từng Task.
2. Nếu thời gian hiện tại **≥ Next Run Time**:
   - Mở file prompt tương ứng (`.agent/[Tên File]`) và **THỰC THI TOÀN BỘ YÊU CẦU** của file đó.
   - Ghi lại quá trình + kết quả chung vào file `.agent/response.txt`.
   - **BẮT BUỘC:** Bạn phải TỰ ĐỘNG chỉnh sửa lại chính file `periodic_prompt.md` này để cộng thêm thời gian (Interval) cho mốc `Next Run Time` ở Task tương ứng đó. (Ví dụ: +10 phút, +30 phút tính từ thời gian hiện tại).
3. Nếu thời gian hiện tại vẫn `< Next Run Time` của một Task nào đó, hãy tảng lờ (bỏ qua) Task đó và chờ đến chu kỳ 10 phút tiếp theo.
4. Nếu chưa đến mốc thời gian của *bất kỳ* Task nào, chỉ cần giữ im lặng và xuất dòng "Chờ đến mốc thời gian tiếp theo" vào `.agent/response.txt`.

---

## Bảng Lịch trình Nhiệm vụ (Cron Tasks):

### Task 1: Kiểm Tra Trading Bot
- **Nội dung:** Chẩn đoán lỗi Bot Giao dịch và Gợi ý chiến lược PNL.
- **File thực thi:** `.agent/trading_bot_prompt.md`
- **Chu kỳ (Interval):** 10 phút / lần
- **Next Run Time:** `2026-04-14T09:28:00+07:00`

### Task 2: Kiểm Tra Training Phân Tán
- **Nội dung:** Giám sát Client Node và lên lịch Training liên tục.
- **File thực thi:** `.agent/training_prompt.md`
- **Chu kỳ (Interval):** 30 phút / lần
- **Next Run Time:** `2026-04-14T09:48:00+07:00`

---
*(Hệ thống: Mỗi khi chạy chu kỳ tự động xong, BẮT BUỘC cập nhật lại Next Run Time và báo cáo toàn bộ ra `.agent/response.txt`)*
