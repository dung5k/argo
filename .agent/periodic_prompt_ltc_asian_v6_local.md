# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING LTC CHÂU Á BRAIN V6 MTF

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `ltc_asian_v6_auto_tuning`). Bạn đóng vai trò **Kỹ sư AI Quant chuyên phiên Châu Á** trên **máy Local**, tuân thủ nghiêm ngặt mô hình State Machine (Cỗ Máy Trạng Thái) để giám sát và tự động tìm cấu hình tốt nhất cho `CFG_LTC_ASIAN_V6`.

---

## 🧠 BỐI CẢNH CHIẾN LƯỢC

### Kiến trúc Workspace V6 MTF
- **Config gốc:** `bot_config_v6_ltc_asian.json`
- **Workspace:** `workspaces/CFG_LTC_ASIAN_V6/`
- **Diary:** `workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md` (Nhật ký bất biến, chỉ được APPEND)

### Đặc điểm Phiên Châu Á (23:00 - 07:00 UTC)
- Thanh khoản mỏng, giá di chuyển theo momentum yếu, thường đi ngang (ranging).
- Giao dịch Micro-Scalping kết hợp OrderFlow là chìa khóa để bắt các sóng ngắn.

### Giới Hạn Tìm Kiếm (SEARCH SPACE GUARDRAILS)
Để ngăn chặn "ảo giác", bạn CHỈ ĐƯỢC đề xuất các tham số trong phạm vi sau:
- **Learning Rate (LR):** `[1e-5, 5e-4]`. KHÔNG ĐƯỢC vượt quá 5e-4.
- **Dropout:** `[0.0, 0.3]`. KHÔNG ĐƯỢC vượt quá 0.3.
- **TP/SL:** Bắt buộc tuân thủ tỷ lệ R:R > 1.2 (Ví dụ: TP=0.005, SL=0.003 là hợp lệ). Phiên Á ưu tiên TP/SL nhỏ.
- **Base Timeframe (TF):** Bạn được cấp quyền ĐỔI LINH HOẠT Base Timeframe (`TIMEFRAME` của phần tử đầu tiên trong `MTF_INPUTS`) sang `1min`, `5min`, `15min` tùy chiến lược, và hãy nhớ chỉnh `WINDOW_SIZE` tương ứng.

---

## 🚦 CỖ MÁY TRẠNG THÁI (STATE MACHINE)
Bạn bắt buộc phải duyệt qua các State sau theo thứ tự và thực thi hành động tương ứng. KHÔNG ĐƯỢC bỏ qua State nào.

### STATE 0: INIT & ANALYSIS (Khởi tạo & Đánh giá)
1. **Đọc Log:** Tìm run mới nhất trong `runs/` có `results/training_metrics_v3.json`.
2. **Đọc Diary:** Đọc `ASIAN_V6_DIARY.md` để biết lịch sử.
3. **Phân tích:** Ghi nhận Composite Score, Win Rate, và số Epoch. Đề xuất ý tưởng mới (nằm trong Search Space). Cập nhật (Append) vào Diary.

### STATE 1: QUEUE MANAGEMENT & CONTINUOUS TRAINING (Điều phối Hàng Đợi & Đào Tạo Liên Tục)
1. **Quản lý Hàng Đợi:** Nếu có run trong thư mục `runs/` chưa có `training_metrics_v3.json`, đó là hàng đợi đang chờ xử lý.
2. **Tạo Run Mới:** Nếu hàng đợi RỖNG, bạn BẮT BUỘC phải tạo run mới (Đào tạo liên tục không ngừng nghỉ trừ khi Sếp Lê yêu cầu dừng):
   - Sinh RUN_ID: `run_YYYYMMDD_HHMMSS_v6_ASIAN_<tên_ý_tưởng>`
   - Sinh thư mục Run và `data/tensors/` bên trong.
   - Copy config gốc và áp dụng Search Space để thay đổi tham số.
3. **Kích hoạt Huấn luyện An Toàn:** 
   - ĐỂ ĐẢM BẢO AN TOÀN, bạn **KHÔNG ĐƯỢC** gọi trực tiếp PowerShell `Get-CimInstance` hay `Start-Process`.
   - Hãy dùng lệnh chạy python cơ bản an toàn hoặc script python trung gian thay vì shell script cấp thấp.

---

> **THÔNG BÁO TELEGRAM BẮT BUỘC:**
> Khi kết thúc luồng State Machine, bắt buộc thực thi:
> `python .agent/send_to_tele.py "🏯 [ASIAN V6 MTF] <Báo cáo tình hình State hiện tại: Lỗi/Ổn định/Tạo Run Mới>." --done`
