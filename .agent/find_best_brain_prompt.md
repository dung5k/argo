# Nhiệm Vụ: Tìm Kiếm Cấu Hình Bộ Não Tốt Nhất (Best Brain Configuration)

Bạn là một chuyên gia phân tích dữ liệu AI. Hãy thực hiện quy trình sau để tìm ra tệp trọng số (weights) và ngưỡng (threshold) tối ưu nhất cho Trading Bot phiên bản 2.1:

## 1. Tìm Kiếm Các Bộ Não (Search Models)
1. **Quét kho lưu trữ:** Truy cập Hugging Face (sử dụng thư viện `huggingface_hub` hoặc script tải xuống) để tìm tất cả các kho lưu trữ (repositories/runs) liên quan đến thuật toán **Version 2.1** (xauusd_..._V2_1).
2. **Đọc báo cáo:** Bên trong mỗi repository tìm được, hãy tải và phân tích tệp `training_metrix_v2.json`. Tệp này chứa một mảng lớn/bảng dữ liệu đánh giá hiệu suất của mô hình ở nhiều mức độ tự tin khác nhau.
3. **Trích xuất Dữ liệu:** 
   Đối với mỗi file `training_metrix_v2.json`, hãy trích xuất 3 thông số cực kỳ quan trọng ở các mốc cắt (threshold):
   - `threshold` (Ngưỡng vào lệnh)
   - `win_rate` (Tỉ lệ thắng)
   - `total_signals` (Tổng số tín hiệu giao dịch phác thảo)

## 2. Ước Lượng Điểm Cân Bằng (Interpolation)
Dựa vào danh sách dữ liệu kéo được từ bước 1 đối với **từng mô hình riêng biệt**:
- Mục tiêu của chúng ta là so sánh công bằng các mô hình ở cùng một tần suất ra lệnh. Cụ thể mức tần suất mong đợi là **khoảng 100 tín hiệu (total_signals ~ 100)**.
- Bạn hãy sử dụng phương pháp Nội suy (Interpolation) hoặc tìm trung bình cộng khu vực lân cận để **ước lượng tự động**:
   - `Thresh_100`: Mức threshold tương ứng để dội ra ~100 tín hiệu.
   - `WinRate_100`: Tỉ lệ Win Rate ước lượng đạt được ở mức `Thresh_100` đó.
- Lập bảng danh sách kết quả (Model_Name | Thresh_100 | WinRate_100) cho toàn bộ các model Version 2.1 tìm thấy.

## 3. Lựa Chọn Và Áp Dụng (Selection & Configuration)
1. **Tìm Não Tốt Nhất:** Từ Bảng nội suy trên, hãy chọn ra **Bộ não** (Model) sở hữu **WinRate_100 (Win Rate trung bình tại mốc ~100 tín hiệu) CAO NHẤT**.
2. **Cấu hình Bot:** 
   - Lấy `Thresh_100` của bộ não vô địch này (thay vì lấy Best Threshold gốc của file metrix).
   - Truy cập vào file cấu hình của bot (`data/bot_v2_brain_schedule.json` hoặc cấu hình mong muốn).
   - Thay thế `run_id`, `weight_file`, `config_id` bằng tên của Bộ não tốt nhất này.
   - Sử dụng `Thresh_100` vừa ước lượng để làm cấu hình `entry_thresh` đi kèm cho Bot.
   
## Đầu Ra Yêu Cầu (Output)
Sau khi hoàn thành, hãy in ra báo cáo rõ ràng quá trình nội suy các mô hình và giải thích vì sao mô hình cuối cùng được chọn, ghi đè toàn bộ vào file `response.txt`.
