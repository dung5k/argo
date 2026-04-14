Nhiệm vụ kiểm tra (Trading Bot Diagnostic Task):
1. Đọc và phân tích file log trích xuất mới nhất của Trading Bot (tại thư mục `data/logs/trade_bot_v2_*.log` hoặc các tệp log tương tự).
2. Rà soát hệ thống: Kiểm tra xem có bất kỳ lỗi (Error/Exception, ngắt kết nối MT5, crash bộ nhớ, lỗi đồng bộ HuggingFace...) nào hay không. Nếu phát hiện lỗi cơ sở hạ tầng, chủ động đọc thêm code và đề xuất phương án FIX dứt điểm LỖI HỆ THỐNG ĐÓ.
3. Phân tích kết quả Trading: Thống kê trạng thái các lệnh giao dịch (vào lệnh, giữ lệnh, đóng lệnh do hit Take Profit / Stop Loss / Reversal), PnL hiện tại và diễn biến giá cả (slippage/delay).
4. Gợi ý thuật toán: Dựa trên phân tích trạng thái thị trường và tần suất khớp lệnh, đưa ra **GỢI Ý điều chỉnh chiến lược/thuật toán** (ví dụ: điều chỉnh ngưỡng `BUY_ENTRY_THR`/`SELL_ENTRY_THR`, cấu hình Stoploss, thay đổi volume ảo...). Lưu ý: Chỉ giới hạn ở mức GỢI Ý CHIẾN LƯỢC, tuyệt đối **KHÔNG lập kế hoạch sửa code hoặc tự ý sửa code thuật toán** nếu thao tác không nhắm mục đích Fix Bugs Hệ Thống.
5. XUẤT KẾT QUẢ BÁO CÁO TOÀN BỘ (MARKDOWN) VÀO TỆP `.agent/response.txt`.

__(Lệnh hệ thống định kỳ: BẮT BUỘC dùng công cụ write_to_file xuất kết quả Markdown thẳng vào tệp '.agent/response.txt' nhé!)__
