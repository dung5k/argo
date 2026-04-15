Nhiệm vụ kiểm tra Tiến độ (Distributed Training Diagnostic Task):
1. Kiểm tra trạng thái online/offline của client1 và clientGH báo cáo ngắn gọn (VD: dùng lệnh `cmd /c "set PYTHONIOENCODING=utf-8 && python src\orchestration\host_controller.py listen --client-id all"`).
2. Nếu máy OFFLINE: Chỉ cần rà soát và báo cáo đơn giản là máy đang tắt, không cần đào sâu thêm.
3. Nếu máy ONLINE đang training: Phân tích kỹ quá trình tiến hóa: loss giảm ra sao, win rate (WR) và Expected Value (EV) đã cải thiện thế nào qua các checkpoint.
4. Nếu máy ONLINE nhưng đang rảnh: Kiểm tra chỉ số WR/EV của các phiên (Asian, London, NY) hiện tại trên HuggingFace.
5. Quyết định: Yêu cầu máy rảnh training cho phiên có thành tích đuối nhất. Lắng nghe log khi bắt đầu để fix bug (nếu có).
6. **LƯU Ý QUAN TRỌNG:** Nếu trong quá trình kiểm tra, bạn có thực hiện lệnh khởi động lại bot, cập nhật code (git pull), sửa lỗi trên client, hoặc gán task mới, bạn BẮT BUỘC phải ghi trúng dòng chú thích `"CẦN ĐIỀU TRA LẠI SAU 5 PHÚT"` vào cuối báo cáo để hệ thống điều phối biết đường giảm chu kỳ và tái kiểm tra ngay lập tức.
7. XUẤT KẾT QUẢ BÁO CÁO TOÀN BỘ (MARKDOWN) VÀO TỆP `.agent/response.txt`.

__(Lệnh hệ thống định kỳ: BẮT BUỘC dùng công cụ write_to_file xuất kết quả Markdown thẳng vào tệp '.agent/response.txt' nhé!)__
