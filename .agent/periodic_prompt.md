Nhiệm vụ định kỳ (Periodic Task):
1. Kiểm tra xem client1 và clientGH có online hay không và có rảnh hay không (bằng cách dùng lệnh host_controller.py listen).
2. Nếu máy nào đang training thì báo cáo tình hình trainning của máy đấy.
3. Nếu 1 trong 2 máy rảnh, thực hiện điều tra thành tích tốt nhất của các bộ trọng số tương ứng với các phiên giao dịch Asian, London, NY của version 2.1 (đọc log, phân tích WR/EV từ runs/ trên nền tảng HF).
4. Xem thành tích phiên nào kém nhất thì yêu cầu client rảnh thực hiện training bộ đấy.
5. Khi client bắt đầu training thì cần nghe log để fix bug nếu cần.
6. XUẤT KẾT QUẢ BÁO CÁO TOÀN BỘ (MARKDOWN) VÀO TỆP `.agent/response.txt`.

__(Lệnh hệ thống định kỳ: BẮT BUỘC dùng công cụ write_to_file xuất kết quả Markdown thẳng vào tệp '.agent/response.txt' nhé!)__
