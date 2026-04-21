# NHIỆM VỤ ĐỊNH KỲ: AUTO-TUNING LTC ASIAN BRAIN

Hệ thống sẽ gọi bạn chạy lại prompt này định kỳ mỗi 10 phút một lần. Trách nhiệm của bạn là đóng vai trò một Kỹ sư AI tự động hóa để đi tìm cấu hình và phương án tốt nhất cho bộ não `CFG_LTC_ASIAN_V3_5`.

Hãy thực thi nghiêm ngặt theo các bước sau trong mỗi lần được gọi:

## BƯỚC 1: Kiểm tra tiến trình Training hiện tại
Sử dụng các công cụ thao tác Terminal (như PowerShell) để tìm xem tiến trình huấn luyện của cấu hình này có đang chạy trên máy này hay không.
- Gợi ý: Kiểm tra bằng `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "train_v3.py" -and $_.CommandLine -match "CFG_LTC_ASIAN_V3_5" }`
- **1.1 Đang Training**: Nếu có tiến trình đang chạy, bạn BỎ QUA phiên làm việc này. Dừng lại và kết thúc công việc ngay.
- **1.2 Không Training**: Nếu tiến trình đã hoàn thành (hoặc bị lỗi dừng lại, hoặc chưa từng chạy), chuyển sang BƯỚC 2.

## BƯỚC 2: Kiểm tra kết quả huấn luyện mới nhất
Sử dụng công cụ File/Thư mục để truy cập vào `workspaces/CFG_LTC_ASIAN_V3_5/brains/`.
Hãy tìm thư mục `run_...` mới nhất và đọc file báo cáo kết quả (như `training_metrics_v3.json`).
- **2.2.1 Lần chạy đầu tiên (Chưa có kết quả)**: Nếu không có thư mục nào hoặc không tìm thấy file metrics, có nghĩa là chưa training lần nào. Chuyển thẳng tới BƯỚC 4 để thực hiện huấn luyện.
- **2.2.2 Đã có kết quả**: Nếu có file kết quả, đọc và phân tích toàn bộ các chỉ số bên trong. Chuyển sang BƯỚC 3.

## BƯỚC 3: Review và Sửa đổi Cấu hình (Góc nhìn Chuyên gia)
Dựa vào phân tích ở Bước 2.2.2, **BẠN PHẢI ĐÓNG VAI TRÒ LÀ MỘT CHUYÊN GIA AI & ĐỊNH LƯỢNG TÀI CHÍNH (QUANT EXPERT) HÀNG ĐẦU**. 
Hãy suy luận sâu sắc, phân tích đa chiều các chỉ số (Win Rate, Composite Score, Sharpe, Max Drawdown nếu có) và đối chiếu với cấu hình hiện tại `workspaces/CFG_LTC_ASIAN_V3_5/bot_config_ltc_asian_v3_5.json`. 
Mọi quyết định đưa ra phải dựa trên tư duy phản biện sắc bén của chuyên gia để tránh overfitting và tìm ra "Alpha" thực sự. Đưa ra lập luận logic vững chắc trước khi thực hiện các thay đổi.
Những thay đổi BẠN CÓ QUYỀN VÀ NÊN làm:
- **Thay đổi Input Features**: Thử nghiệm thêm hoặc bớt các chỉ số vĩ mô trong `MACRO_FEATURES` (như DXYm, Crypto, Vàng...).
- **Thay đổi Thông số Trading**: Tinh chỉnh lại `TP_PCT`, `SL_PCT`, `MAX_HOLD_BARS` xem tỷ lệ Risk/Reward nào tối ưu.
- **Thay đổi Hyperparameters**: Điều chỉnh `WINDOW_SIZE`, `LEARNING_RATE`, `BATCH_SIZE` hoặc bất kỳ tham số gì trong file cấu hình.
- **Thay đổi Code**: Bạn được phép sửa đổi logic mã nguồn trong `src/` (như thuật toán sinh Feature, kiến trúc Model, hay hàm Loss) nếu có ý tưởng đột phá.
> LƯU Ý: Phải ghi chú lại (có thể tạo file Note hoặc Log) những gì đã thay đổi để so sánh.

## BƯỚC 4: Chuẩn bị Dữ liệu & Kích hoạt Huấn luyện
1. **Chuẩn bị lại Data (Nếu Cần)**: Nếu Bước 3 có động chạm tới cấu trúc Features, `WINDOW_SIZE` hoặc `TP/SL` v.v., bạn BẮT BUỘC phải gọi script sinh lại bộ dữ liệu (tạo Tensors). Hãy tìm đúng file script sinh data của hệ thống và chạy nó với cấu hình mới.
2. **Kích hoạt Training**: Gọi lệnh chạy huấn luyện mô hình (ví dụ: chạy `train_v3.py` truyền vào đường dẫn cấu hình). Đảm bảo sử dụng công cụ Run Command theo cơ chế ngầm (Background / Async) để tiến trình tự chạy.
   - **THEO DÕI LOG VÀ FIX LỖI**: Đừng chỉ khởi động xong rồi bỏ đó! Hãy đọc liên tục các dòng log (thông qua file output hoặc theo dõi Command_Status) trong vài phút đầu để xem tiến trình chuẩn bị Data hoặc Training có sinh ra Exception / Error không.
   - Nếu có lỗi phát sinh: BẠN PHẢI TỰ ĐỘNG PHÂN TÍCH LỖI, SỬA CODE/CONFIG và CHẠY LẠI tiến trình cho đến khi Training thực sự diễn ra thành công.
3. **Thông báo Telegram**: Sử dụng script `.agent/send_to_tele.py` để báo cáo ngắn gọn về việc: Bạn vừa đánh giá kết quả ra sao, thay đổi những gì ở Cấu hình/Code, và đã kích hoạt lại vòng lặp huấn luyện mới. 

Chúc bạn tìm ra "chén thánh" thành công!
