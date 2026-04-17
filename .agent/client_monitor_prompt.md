# Giám Sát Cấu Hình Máy Trạm & Mô Hình (Client & GPU Monitor)

Đây là Skill/Workflow chuyên dụng của hệ thống để phân tích sâu vào phần cứng của các Máy Trạm (CPU, RAM, đặc biệt là **GPU/VRAM**) và kiểm soát chất lượng Học Tập (Loss Rate) trên Hugging Face.

## Mục đích
- Bắt lỗi quá tải VRAM ngay lập tức nếu Tensor phi tập trung bị rò rỉ bộ nhớ.
- Xem xét lịch sử Loss Rate trên Hugging Face để quyết định xem sự đánh đổi phần cứng có xứng đáng với tốc độ học (Đang Tốt Lên) hay model đã bị Kẹt/Local Minima (Đi Ngang/Thụt lùi).

## Hướng dẫn thực thi:
Khi Khách hàng kích hoạt Prompt này, bạn phải thực thi 2 nhiệm vụ dưới đây:

### 1. Phân Tích Phần Cứng Client (Monitor MQTT)
1. Hãy chạy `python temp/listen_clients.py > temp/logs_clients_gpu.txt` trong Background. Đợi khoảng 10 giây.
2. Dùng chức năng Get-Content đọc lại file txt đó.
3. Rút trích cụm từ "CPU / RAM / GPU / VRAM" từ các máy `clientGH` và `client1`.
   - Chú ý: Trạm nào VRAM gần sát vách trần hoặc GPU vọt lên >95%, hãy phát cảnh báo Đỏ. 

### 2. Phân Tích Tiến Độ Học Tập trên Đám Mây (HF Metrix)
1. Chạy lệnh: `python scripts/check_hf_metrix.py`
2. Kịch bản này đã giao tiếp với Hugging Face và tải file `training_metrix_v2.json`.
3. Phân biệt rõ thông số ở báo cáo: 
   - Đánh giá xem xu hướng VLoss của 5 Epoch gần nhất ở `ĐANG TỐT LÊN` hay `KẸT HOẶC ĐI NGANG`.

### 3. Xuất Báo Cáo
Sau khi tổng hợp, hãy ghi thẳng báo cáo vào tệp `.agent/response.txt` theo đúng định dạng Markdown. Bao gồm:
- **[Hardware]**: Thể trạng VRAM và GPU của từng Node.
- **[Cloud Metrix]**: Model có đang khôn ra không hay nó đang dậm chân tại chỗ. Có cần phải chèn ép cấu hình hay điều đào tạo kiểu khác không.
