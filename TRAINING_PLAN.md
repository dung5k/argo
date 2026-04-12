# NHẬT KÝ ĐÀO TẠO HỆ SINH THÁI (TRAINING LOGS & MASTER PLAN)

*Tài liệu này đóng vai trò là Sổ cái (Ledger) theo dõi toàn bộ kế hoạch, lịch sử và kết quả thực thi của các đợt huấn luyện Neural Network (Models) phân tán qua kiến trúc MQTT.*

---

## 1. MỤC TIÊU LỚN & TỔNG QUAN
- **Mục tiêu**: Xây dựng, mài giũa và giám sát các khối Neural Network (V1.5 và V2) song song trên các Trạm (Nhờ kiến trúc MQTT).
- **Trọng tâm hiện tại**:
  1. Tách biệt việc theo dõi các Session/Thị trường (NY, Asian, London, Weekend).
  2. Bổ sung thêm dòng tiền Crypto biến động cuối tuần (ARB).
  3. Hệ thống hóa độ lệch chuẩn, Val_Loss và các đợt ném code deploy xuống Client.

---

## 2. TRAINING V2 XAU (VÀNG) - THEO TỪNG THỊ TRƯỜNG

Mảng cốt lõi được chia theo múi giờ, vì hành vi Market Maker đánh quét thanh khoản ở phiên Mỹ (NY) khác hoàn toàn với cách giăng bẫy đi ngang (Sideway) ở Á (Asian).

### 2.1. XAU Phiên Mỹ (NY Session)
- **Tình trạng/Kế hoạch sắp tới:** 
  - Khai thác tận cùng hành vi chạy dồn giá lúc ra tin (Lưu ý: Dataset sẽ cắt bỏ những phần của YFinance cũ, thuần 100% MT5).
  - Khắc phục lỗi API Gemini 400 (do IP khu vực) của AI Supervisor nhúng trong đợt đánh giá mỗi 200 epochs để khỏi rác log.

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: `20260412_181628_train`**
  - **Máy trạm:** `client1`
  - **Thời gian:** 12/04 18:16 - 22:30
  - **Tiến độ:** Ep 200+
  - **Loss:** Train `~0.1414` | Val `~0.2416`
  - **Ghi chú:** Bị ngắt (Stop Train) để chuẩn bị chuyển qua Asian. Có dấu hiệu Val_Loss hơi với (nguy cơ mớm overfit). Lời khuyên: Giảm Learning Rate hoặc chốt model sớm mốc Ep 180 (Val: 0.19).

- **Lần chạy: `20260411_...`**
  - **Máy trạm:** `clientGH`
  - **Thời gian:** 11/04
  - **Tiến độ:** Ep 100+
  - **Ghi chú:** Bị kẹt lỗi đụng độ Git Pull do rác hệ thống (Đã xử lý cơ chế cưỡng chế Hard Reset + Clean).

---

### 2.2. XAU Phiên Á (Asian Session)
- **Tình trạng/Kế hoạch sắp tới:** 
  - Vừa mới mồi lửa cấu hình. Biên độ phiên Á rất hẹp, Loss dự kiến sẽ giảm dốc đứng nhưng phải cẩn thận bẫy vấp thanh khoản (Wash Trading).

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: (Vừa khởi động)**
  - **Máy trạm:** `client1`
  - **Thời gian:** 12/04 22:56+
  - **Tiến độ:** Đang chạy
  - **Loss:** Đang thu thập
  - **Ghi chú:** Bắt đầu nhận config mới cứng `bot_config_xau_asian_v2.json`. Máy đã ngoạm tín hiệu và đăng nhập quá trình Train (MAX Mode) thành công. File Json được nhét trơn tru vào kho `C:\argo\data`.

---

### 2.3. XAU Phiên Âu (London Session)
- **Tình trạng/Kế hoạch sắp tới:** 
  - Đóng gói file cấu hình rập khuôn `bot_config_xau_london_v2.json`.
  - Mục tiêu đào tạo là tóm các nhịp Breakout giả (Fakeout) và dòng tiền dẫn dắt (Smart money injection) chuẩn bị gối đầu sang phiên Mỹ.
  - Sẽ trích xuất Dataset lọc chuẩn khung giờ từ 14:00 đến 19:30 (Giờ VN). Sẽ yêu cầu `clientGH` gánh phần khung giờ này vào trong rạng sáng các ngày trong tuần.

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: (Đang lên lịch, chưa khởi chạy)**
  - **Máy trạm:** Dự kiến `clientGH` hoặc `client1` sau khi nhả phiên Á.
  - **Thời gian:** N/A
  - **Tiến độ:** N/A
  - **Loss:** N/A
  - **Ghi chú:** Đang chờ hoàn tất việc gọt Dataset.

---

## 3. TRAINING V2 ARB (CRYPTO CUỐI TUẦN)

Ngách khai thác lợi nhuận bù đắp vào các ngày thứ Bảy, Chủ Nhật khi dòng tiền Fiat nghỉ xả hơi. Arbitrum (ARB) có thanh khoản tương đối nén với biên độ sóng ăn sâu.

- **Tình trạng/Kế hoạch sắp tới:** 
  - Khởi chạy thường trực cho `clientGH` đóng vai "Cỗ máy đục vách" thứ Bảy và Chủ Nhật.
  - Phế bỏ hoàn toàn những lệnh cố gắng ăn xổi (Scalp) 1-3 phút vì đã có bài nghiên cứu chứng minh nó vướng rào cản Spread/Phí (Chỉ có ~13% - 28% tỷ lệ thắng phí). Xoay trục cấu trúc sang đánh dồn tụ dài hạn: Horizons `[5, 10, 15, 30]` phút.

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: `demo_arb_run1`**
  - **Máy trạm:** `clientGH`
  - **Thời gian:** 12/04 21:30
  - **Tiến độ:** Thu thập tệp parquet
  - **Ghi chú:** Quá trình tải tệp từ HuggingFace qua Safe HTTP hoàn tất nhưng bộ lọc ban đầu báo vớt được `0/3 file`. Đã khắc phục việc lộ đường viền Config và bắt Agent quy về ổ cứng `C:\argo`.

- **Lần chạy: `demo_arb_run2`**
  - **Máy trạm:** `clientGH`
  - **Thời gian:** Sắp chạy...
  - **Ghi chú:** Chờ nạp bản Config mới với bộ Horzion 5-30m để kiểm chứng kết quả thực chiến vào dịp T7 tới.

---

*(Tài liệu này sẽ được Agent và Chủ nhân thường xuyên Review và Update sau mỗi chu kỳ Epoch Lớn)*
