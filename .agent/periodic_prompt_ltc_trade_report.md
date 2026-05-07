# NHIỆM VỤ ĐỊNH KỲ: BÁO CÁO TÌNH HÌNH GIAO DỊCH BOT LTC V3

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**.

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `ltc_trade_report`). Bạn đóng vai trò **Giám đốc Quản lý Rủi ro (Risk Manager)**. Nhiệm vụ của bạn là kiểm tra nhật ký giao dịch và trạng thái ví của Bot LTC, sau đó tổng hợp thành một báo cáo súc tích gửi lên Telegram.

---

## BƯỚC 1: THU THẬP DỮ LIỆU GIAO DỊCH
Bạn có thể sử dụng Python Script hoặc các công cụ File System để thu thập thông tin:

1. **Đọc Trạng Thái Lệnh Ảo (Virtual Trade State):**
   - File nằm tại: `data/virtual_state_LTCUSDT.json` (hoặc tên tương tự trong thư mục `data/`).
   - Đọc giá trị: `virtual_balance` (Số dư hiện tại so với gốc 10,000$), Số lượng lệnh đang mở (`active_trade_loggers`), và xem qua danh sách `history_deals` để đếm số lệnh chốt lời/cắt lỗ gần đây.

2. **Đọc Nhật Ký Mới Nhất (Logs):**
   - Thư mục log: `workspaces/shared_meta/logs/`
   - Tìm file log của ngày hôm nay (VD: `trade_bot_v3_20260507.log`).
   - Xem 50-100 dòng cuối để nắm bắt xem bot có gặp lỗi gì không (ví dụ: mất kết nối MT5, lỗi CCXT, hay lỗi khởi tạo mạng).

---

## BƯỚC 2: PHÂN TÍCH VÀ ĐÁNH GIÁ
- **Hiệu Suất (Performance):** Lãi/Lỗ ròng (PnL) tính đến thời điểm hiện tại là bao nhiêu? Win Rate thực tế của các lệnh gần nhất.
- **Tình Trạng (Status):** Có lệnh nào đang bị ngâm quá lâu không? Bot có đang nhận diện dữ liệu bình thường không?
- **Khuyến nghị:** Nếu phát hiện chuỗi thua lỗ liên tục hoặc số dư sụt giảm mạnh, hãy đề xuất tạm dừng bot để kiểm tra lại cấu hình.

---

## BƯỚC 3: XUẤT BÁO CÁO QUA TELEGRAM
Soạn một báo cáo chuyên nghiệp, ngắn gọn (chỉ gửi những gì quan trọng nhất, tránh spam). 

**Mẫu tham khảo:**
```text
📊 BÁO CÁO GIAO DỊCH LTC BOT V3 (Định Kỳ)

💰 Số dư ảo (Balance): 10,050.25$ (+50.25$)
📉 Lệnh đang mở (Open): 1 lệnh (LTCUSDT MUA @ 85.0)
✅ Lịch sử gần đây: 3 Thắng / 1 Thua (WinRate 75%)
⚙️ Tình trạng hệ thống: Hoạt động ổn định, không có lỗi kết nối MT5.
```

**Thực thi lệnh gửi:**
```powershell
python .agent/send_to_tele.py "<Nội_dung_báo_cáo>" --done
```

> ⚠️ LƯU Ý BẮT BUỘC: Bạn **PHẢI** gọi lệnh `send_to_tele.py` với cờ `--done` ở cuối tiến trình để thông báo kết thúc chu kỳ báo cáo và giải phóng hàng đợi của hệ thống!
