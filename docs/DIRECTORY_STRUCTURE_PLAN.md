# Quy hoạch không gian làm việc (Directory Structure Plan)

Tài liệu này quy định cấu trúc thư mục chuẩn và các quy tắc để tránh việc không gian làm việc bị rác hóa bởi các file sinh tự do. Tất cả AI Agent và thành viên dự án bắt buộc phải tuân thủ nghiêm ngặt.

## 1. Cấu trúc Thư mục Chính

- **`src/`**: Nơi chứa toàn bộ mã nguồn chính của dự án. Gồm các thành phần quan trọng như Trade Bot, Inference Engine, Data Processor, Trading Managers. KHÔNG ĐƯỢC ĐẶT FILE CODE VÀO BÊN NGOÀI THƯ MỤC NÀY NẾU NÓ LÀ THÀNH PHẦN CHÍNH.
- **`scripts/`**: Nơi chứa các công cụ hỗ trợ một lần, file test (nếu được giữ lại), mã di chuyển dữ liệu (migrate), crawl dữ liệu định kỳ, hoặc các mã kiểm tra báo cáo định kỳ.
- **`tools/`**: Nơi chứa các công cụ đóng gói chuyên biệt hỗ trợ ngoại vi cho hệ thống. Ví dụ: `tele_bridge` (ứng dụng kết nối Telegram).
- **`temp/`**: Không gian lưu trữ TẠM THỜI (Scratch Space). Đây là thư mục duy nhất được phép lưu các file tạo nhanh, các script crawl nháp, test log, hoặc các mã kiểm thử tạm. MỌI FILE TẠM SINH RA TRONG NÀY BẮT BUỘC PHẢI BỊ XÓA SAU KHI SỬ DỤNG.
- **`workspaces/`**: Nơi lưu trữ cấu hình môi trường, các vòng huấn luyện (runs) và brains (mô hình đã train).
- **`logs/`**: Thư mục lưu trữ nhật ký hoạt động cố định của Trade Bot và các hệ thống lõi.
- **`data/`**: Nơi chứa các dữ liệu thô, dataset, file cấu hình tĩnh.
- **`docs/`**: Nơi chứa tài liệu dự án, quy hoạch, kiến trúc.

## 2. Quy tắc Làm việc Cốt lõi (File Management Rules)

1. **Tuyệt đối không lưu file rác vào thư mục gốc (`./`)**: 
   Thư mục gốc chỉ được chứa file khởi động (`.bat`, `.ps1`), file cấu hình chính (e.g. `*.json`), và file mô tả thư mục. Không được tạo các file như `append_diary_*.py`, `temp_*.txt` hay `debug*.log` ở đây.
2. **Quy tắc dọn dẹp (Zero-Waste Policy)**:
   Nếu một tác vụ (ví dụ: in báo cáo ra file, crawl một lần, test một hàm) cần file trung gian, hãy lưu vào `temp/`. Tác vụ hoàn thành thì AI Agent/Người dùng phải TỰ ĐỘNG xóa file đó.
3. **Log hệ thống**:
   Nếu cần ghi log ra file cho mục đích gỡ lỗi kéo dài, phải ghi vào thư mục `logs/`. Nếu chỉ log cho một vòng lặp, ghi vào `temp/` và tự xử lý.

## 3. Quản lý Thư mục Mở rộng
Nếu có một công cụ mới độc lập hoàn toàn với `src/`, hãy tạo thư mục con mới bên trong `tools/` (Giống như cách `tele_bridge` đã được bố trí).

***Lưu ý: Mọi vi phạm quy tắc này sẽ phá vỡ tính nguyên vẹn của dự án và làm tăng độ trễ đọc-hiểu hệ thống.***
