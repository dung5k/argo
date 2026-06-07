# TÀI LIỆU THIẾT KẾ KỸ THUẬT LÕI V8: CHOCH/BOS FRACTAL NLP
*Mức độ bảo mật: Tuyệt mật thuật toán lõi.*
*Cảnh báo nguyên tắc kỹ sư: Tuyệt đối không áp dụng Indicator Repaint trong toàn bộ Pipeline. Mọi xử lý phải mang tính nhân quả một chiều (Chỉ tham chiếu quá khứ).*

---

## 1. Vấn Đề Cơ Sở & Luận Điểm Thiết Kế
Thuật toán nhận diện cấu trúc thị trường (Market Structure) kinh điển thường lạm dụng các hàm **ZigZag** (phổ biến trên MT4/TradingView). Vấn đề chí mạng: ZigZag có tính chất **Repaint** (Vẽ lại đồ thị). Nghĩa là đỉnh cũ sẽ bị dời sang nến mới nếu giá tiếp tục đi lên. 
Việc đẩy dữ liệu Repaint vào tập Train sẽ sinh ra hiện tượng **Data Leakage** rùng rợn: AI học được kết quả của tương lai.

**Giải pháp của V8:** Sử dụng **Bill Williams Fractal** - một cấu trúc tĩnh, không thể vẽ lại, làm nền tảng toán học duy nhất xác định Đỉnh/Đáy.

---

## 2. Đặc Tả Toán Học Thuật Toán Fractal (Non-Repaint)
Một đỉnh Fractal (Fractal High) được định nghĩa cứng là một cụm 5 nến thỏa mãn điều kiện:
`High[i-2] < High[i] AND High[i-1] < High[i] AND High[i+1] < High[i] AND High[i+2] < High[i]`

- **Điểm neo trung tâm (Pivot):** Là cây nến `i`.
- **Độ trễ hệ thống (System Latency Trade-off):** Tín hiệu Fractal High chỉ được hệ thống XÁC NHẬN CHẾT (Commit) tại thời điểm đóng cửa hoàn toàn của nến `i+2`. Tức là, hệ thống buộc phải chấp nhận Delay 2 nến thời gian thực để đánh đổi lấy 100% độ trung thực của dữ liệu (Data Integrity).

---

## 3. Khái Niệm Đột Phá: Token Hóa Cấu Trúc (NLP Tokenization)
Thay vì nhồi trực tiếp các con số giá trị thuần túy của Đỉnh/Đáy vào Mạng Neural (rất dễ gây ra lỗi tràn Gradient hoặc vỡ trọng số do Scale giá khác nhau giữa các cặp tiền), V8 sẽ dịch các chuỗi Đỉnh/Đáy này thành **Ngôn ngữ Văn bản (Tokens)**.

### 3.1. Từ Vựng Trạng Thái (Vocabulary Dictionary)
- `HH` (Higher High): Đỉnh Fractal mới CAO HƠN Đỉnh Fractal liền kề trước đó.
- `HL` (Higher Low): Đáy Fractal mới CAO HƠN Đáy Fractal trước đó.
- `LH` (Lower High): Đỉnh Fractal mới THẤP HƠN Đỉnh Fractal trước đó.
- `LL` (Lower Low): Đáy Fractal mới THẤP HƠN Đáy Fractal trước đó.
- `BOS_UP` (Break of Structure Up): Xác nhận nến đóng cửa (Close price) vượt qua Đỉnh râu `HH` gần nhất kèm Volume xác nhận. (Tiếp diễn tăng)
- `CHOCH_DN` (Change of Character Down): Giá đóng cửa đâm thủng thẳng qua Đáy râu tạo ra đỉnh cao nhất (`HL` gần nhất). (Gãy cấu trúc chuyển giảm)

### 3.2. Vector Chuỗi Đầu Vào (Input Sequence)
Tại mỗi thời điểm nến đóng cửa `t`, Data Pipeline sẽ trích xuất một chuỗi sự kiện lịch sử cấu trúc gồm N Tokens.
Ví dụ một Record dữ liệu cấp cho Transformer: `["HL", "HH", "HL", "HH", "CHOCH_DN"]`.
-> Chuỗi Token này tương đương với một mô tả hình thái: *"Thị trường đang có xu hướng tăng vững nhưng đột ngột gãy cấu trúc thành giảm"*.

---

## 4. Tích Hợp Vào Kiến Trúc Transformer Của V8
Kiến trúc AI sẽ cư xử với chuỗi giá giống hệt cách một mô hình ngôn ngữ (GPT) phân tích một câu văn:

- **Embedding Layer**: Chuyển các Token (`HH`, `CHOCH_DN`,...) thành Vector nhiều chiều (dimension = 64 hoặc 128) để tính toán ma trận.
- **Positional Encoding**: Bổ sung thông tin tọa độ tuần tự. Một Token `CHOCH_DN` xuất hiện ở cuối chuỗi mang ý nghĩa khẩn cấp hơn hẳn `CHOCH_DN` nằm ở vị trí đầu chuỗi bị đè lấp bởi lịch sử.
- **Self-Attention Mechanism**: Khả năng cốt lõi. Mô hình sẽ phân bổ trọng số (Attention Weight) vượt trội. Nếu Self-Attention phát hiện chuỗi Token báo hiệu lực đẩy đang suy thoái dần (nhiều nến chồng chéo liên tục), nó sẽ dồn Attention cực đại vào tín hiệu `CHOCH` kế tiếp để dự báo khả năng sập giá mà không bị trễ.

---

## 5. Ràng Buộc Kỹ Thuật (Technical Filters & Constraints)
Để đảm bảo tín hiệu BOS/CHOCH phát sinh từ thị trường thực chứ không phải nhiễu, các ràng buộc Toán học sau được ghim vào lớp Filter:

1. **Close Price Rule (Luật giá đóng cửa)**: Một BOS/CHOCH CẤM ĐƯỢC KÍCH HOẠT nếu nó chỉ là một cái râu nến (Wick) thọc qua mốc giá. Bắt buộc `Close_Price[t]` phải đâm thủng dứt khoát mốc Extrema đó. Chống 90% False Breakout.
2. **Volume Threshold Filter (Bộ lọc Khối lượng)**: Sự kiện vỡ cấu trúc không có Định chế tham gia là vô giá trị. Tín hiệu phá vỡ phải đi kèm điều kiện `Volume[t] > 1.2 * MA_Volume(20)`. Nếu nhỏ hơn, gán mác `FAKE_BOS` và loại bỏ.
3. **Array State Limit (Giới hạn Trạng thái O(n))**: Mảng bộ nhớ RAM chỉ duy trì Rolling Window max 50 Tokens gần nhất. Mọi Token thứ 51 bị đẩy khỏi Stack (FIFO) để giới hạn độ phức tạp thời gian vận hành Real-time xuống O(1) - O(N), chống khựng hệ thống.
