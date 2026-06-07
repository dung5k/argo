# KIẾN TRÚC TỔNG THỂ V8 (MASTER ARCHITECTURE)
*Tài liệu thiết kế Core Engine cho thuật toán Transformer Fractal NLP.*
*Quy định: Mọi Module phải hoàn toàn độc lập (Decoupled), Giao tiếp qua Interface chuẩn.*

## 1. Data Pipeline Layer (Lớp Quản lý Luồng Dữ Liệu)
- **Class `DatasetBuilder`**: Trái tim của hệ thống cấp liệu. 
  - **Nhiệm vụ**: Đọc dữ liệu Raw CSV từ các khung thời gian `M15`, `H1`, `H4`.
  - **Luật khắt khe**: Khi tiến hành Left Join dữ liệu H1/H4 vào M15, BẮT BUỘC sử dụng thuật toán `ffill()` (Forward Fill) dựa trên nến `[t-1]`. Kỹ sư nghiêm cấm truy xuất giá trị hiện tại của H1/H4 chưa chốt sổ (Chống Data Leakage tuyệt đối).
  - **Output**: Một DataFrame đã gộp sạch sẽ, không có Null/NaN không hợp lệ.

## 2. Feature Engineering Layer (Lớp Chiết Xuất Tín Hiệu)
Lớp này hoàn toàn không dùng Indicator MT4 truyền thống. Nó xử lý logic Toán học tĩnh.

- **Class `FractalDetector`**:
  - **Nhiệm vụ**: Lướt qua mảng High/Low để tìm cụm nến Fractal.
  - **Đầu vào (Input)**: Mảng `High[t-4 ... t]` và `Low[t-4 ... t]`.
  - **Đầu ra (Output)**: Một Object đánh dấu vị trí nến có Fractal High hoặc Fractal Low.
  - **Luật khắt khe**: Luôn luôn trả về tín hiệu tĩnh ở nến `t-2` (Delay 2 nến so với thực tại để confirm). Không được phép Repaint.

- **Class `NLPTokenizer`**:
  - **Nhiệm vụ**: Đọc chuỗi các sự kiện Fractal vừa được detect, kết hợp với kiểm tra râu nến/giá đóng cửa/Volume để biên dịch thành ngôn ngữ Text.
  - **Đầu vào (Input)**: Danh sách tọa độ Fractal và DataFrame gốc (chứa Close, Volume).
  - **Đầu ra (Output)**: Chuỗi String Array độ dài N (ví dụ: `["HL", "HH", "CHOCH_DN"]`).
  - **Luật khắt khe**: Phải check Volume Spike > tham số cấu hình. Nếu không đủ Volume, trả về `FAKE_BOS` và loại bỏ.

## 3. AI / Machine Learning Layer (Lớp Lõi Trí Tuệ Nhân Tạo)
- **Class `TransformerModel` (PyTorch)**:
  - **Nhiệm vụ**: Học và nhận diện mẫu hình gãy cấu trúc (CHOCH) thông qua chuỗi Tokenizer.
  - **Kiến trúc mạng**: 
    - `TokenEmbedding`: Dịch Text Token thành Vector không gian.
    - `PositionalEncoding`: Mã hóa thứ tự thời gian của sự kiện.
    - `SelfAttention`: Tính toán sự quan tâm (Weight) của thị trường với các cấu trúc trước đó.
  - **Đầu ra**: Probability Tensor (0.0 -> 1.0) dự đoán nến kế tiếp đi lên hay đi xuống.

## 4. Execution & Training Layer (Lớp Huấn Luyện)
- **File `training_loop.py`**:
  - **Nhiệm vụ**: Load cấu hình JSON, khởi tạo Model, chạy vòng lặp epochs, Backpropagation.
  - **Luật khắt khe**: Không được Hardcode bất cứ biến số nào. Toàn bộ Hyperparameter lấy từ File Config. Báo cáo Loss định kỳ ra màn hình.
