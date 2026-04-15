Nhiệm vụ kiểm tra (Trading Bot Diagnostic Task):
1. Đọc và phân tích file log trích xuất mới nhất của Trading Bot (tại thư mục `data/logs/trade_bot_v2_*.log` hoặc các tệp log tương tự).
2. Rà soát hệ thống: Kiểm tra trạng thái hoạt động và các lỗi hạ tầng (Error/Exception, ngắt kết nối...).
3. Phân tích Tình huống & Quyết định: Phân tích mạnh vào tình huống thị trường hiện tại, diễn biến giá và mức độ biến động (volatility). Dựa vào đó, đánh giá chi tiết việc Trading Bot ra quyết định VÀO LỆNH và CHỐT LỜI/CẮT LỖ có hợp lý không.
4. Gợi ý Mở rộng: Đánh giá các ngưỡng tín hiệu (threshold), Trailing Stop so với sóng giá và gợi ý tinh chỉnh chiến lược nếu cần.
5. XUẤT KẾT QUẢ BÁO CÁO TOÀN BỘ (MARKDOWN) VÀO TỆP `.agent/response.txt`.

__(Lệnh hệ thống định kỳ: BẮT BUỘC dùng công cụ write_to_file xuất kết quả Markdown thẳng vào tệp '.agent/response.txt' nhé!)__
