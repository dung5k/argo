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
  - **Loss & Winrate:**
    - Train Loss: `~0.1414` | Val Loss: `~0.2416`
    - Winrate: `>50%: N/A | >62%: N/A | >73%: N/A | >85%: N/A` *(Chưa thu thập từ Log cũ)*
  - **Mô tả:** Chạy phân tích phiến Mỹ.
  - **Trạng thái:** Đã Stop ngang để nhường tài nguyên cho phiến Á. Nguy cơ mớm overfit ở mốc Ep 200.
  - **Các đầu việc cần làm (Dành cho AI):**
    + [ ] Đánh giá lại việc cắt giảm Learning Rate.
    + [ ] Thử nghiệm load lại weights ở Ep 180 để chốt model (VLoss 0.19).

---

### 2.2. XAU Phiên Á (Asian Session)
- **Tình trạng/Kế hoạch sắp tới:** 
  - Vừa mới mồi lửa cấu hình. Biên độ phiên Á rất hẹp, Loss dự kiến sẽ giảm dốc đứng nhưng phải cẩn thận bẫy vấp thanh khoản (Wash Trading).

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: `20260412_225726_train`**
  - **Máy trạm:** `client1`
  - **Thời gian:** 12/04 22:56 đến 13/04 04:00 (Hẹn giờ tắt)
  - **Tiến độ:** Ep 113+ (Tính đến 23:18)
  - **Loss & Winrate:**
    - Train Loss: `0.1334` | Val Loss: `0.2662` *(Sơ bộ)*
    - Winrate: `>50%: 52.0% | >62%: 55.8% | >73%: 55.2% | >85%: 50.0%`
  - **Mô tả:** Bắt đầu nhận config mới cứng `bot_config_xau_asian_v2.json`. Máy đã ngoạm tín hiệu và đăng nhập quá trình Train (MAX Mode) thành công.
  - **Các đầu việc cần làm (Dành cho AI):**
    + [ ] Chờ đến khi hết giờ (04:00).
    + [ ] Trích xuất log để cập nhật kết quả Epoch cuối cùng và tỷ lệ Winrate vào đây.

---

### 2.3. XAU Phiên Âu (London Session)
- **Tình trạng/Kế hoạch sắp tới:** 
  - Đóng gói file cấu hình rập khuôn `bot_config_xau_london_v2.json`.
  - Mục tiêu đào tạo là tóm các nhịp Breakout giả (Fakeout) và dòng tiền dẫn dắt (Smart money injection) chuẩn bị gối đầu sang phiên Mỹ.
  - Sẽ trích xuất Dataset lọc chuẩn khung giờ từ 14:00 đến 19:30 (Giờ VN). Sẽ yêu cầu `clientGH` gánh phần khung giờ này vào trong rạng sáng các ngày trong tuần.

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: (Đang lên lịch, chưa khởi chạy)**
  - **Máy trạm:** `client1`
  - **Thời gian:** 13/04 04:00+ (Sau khi ngắt Asian)
  - **Mô tả:** Đào tạo phiến London để tóm Fakeout.
  - **Trạng thái:** Chờ tới giờ kích nổ.
  - **Các đầu việc cần làm (Dành cho AI):**
    + [ ] Khởi chạy quy trình trích xuất Dataset 100% MT5 lọc chuẩn biên độ thời gian [07h00 - 12h30 UTC].
    + [ ] Đóng gói và gửi config mới `bot_config_xau_london_v2.json` cho `client1`.
    + [ ] Gửi yêu cầu `client1` training v2 XAU London.
    + [ ] Báo cáo cập nhật kết quả training vào file `TRAINING_PLAN.md`.

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
  - **Tiến độ:** Quét Parquet
  - **Loss & Winrate:** N/A
  - **Mô tả:** Thu thập dữ liệu thử nghiệm qua HF. 
  - **Trạng thái:** Bị lỗi file config đường dẫn hệ thống. Đã khắc phục việc lộ đường viền Config và quy về ổ cứng `C:\argo`.

- **Lần chạy: `demo_arb_run2`**
  - **Máy trạm:** `clientGH`
  - **Thời gian:** Sắp chạy (Cuối tuần)
  - **Mô tả:** Chạy cấu hình Horizons 5-30m đánh dài.
  - **Trạng thái:** Chờ khởi động.
  - **Các đầu việc cần làm (Dành cho AI):**
    + [x] Gửi cấu hình định dạng mốc 5, 10, 15, 30 phút sang `clientGH`.
    + [ ] Giám sát quá trình chạy và nhét chỉ số Winrate mốc 5 phút vào Log.

---

*(Tài liệu này sẽ được Agent và Chủ nhân thường xuyên Review và Update sau mỗi chu kỳ Epoch Lớn)*
