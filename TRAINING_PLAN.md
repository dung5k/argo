# NHẬT KÝ ĐÀO TẠO HỆ SINH THÁI (TRAINING LOGS & MASTER PLAN)

*Tài liệu này đóng vai trò là Sổ cái (Ledger) thực thi. Nó được thiết kế theo chuẩn (Standard Operating Procedure - SOP) để Trợ lý Sinh học / AI (Antigravity) có thể tự động đọc hiểu, báo cáo kết quả và tick hoàn thành kế hoạch sau mỗi quy trình tự động hóa.*

---

## 1. QUY TRÌNH CẬP NHẬT TỰ ĐỘNG (SOP DÀNH CHO AI THỰC THI)
Khi AI (Antigravity hoặc các Agent khác) nhận lệnh báo cáo hoặc vừa hoàn tất Deploy/Train, AI bắt buộc phải thực hiện các bước sau trên tài liệu này:
- `[ ]` Tìm đến đúng Khu vực (Session / Symbol) của mô hình vừa chạy.
- `[ ]` Cập nhật Trạng thái các hộp check `[ ]` trong phần **Kế hoạch thực thi (Action Plan)**.
- `[ ]` Ghi đè vào danh sách **Lịch sử các lần chạy (Run History)** theo khung chuẩn (Bắt buộc phải có **Winrate** ở các mốc `>50%, >62%, >73%, >85%` từ Log ghi nhận được).

---

## 2. TRAINING V2 XAU (VÀNG) - THEO TỪNG THỊ TRƯỜNG

Mảng cốt lõi phân lớp (Object-Oriented) dựa trên hệ sinh thái thời gian của Vàng.

### 2.1. Nhánh: XAU Phiên Mỹ (NY Session)
Đặc thù thao túng giá cực mạnh, thanh khoản sâu, và rũ bỏ bằng tin tức. Đổi Dataset hoàn toàn sang hệ MT5 thay vì Yfinance.

#### Kế hoạch thực thi (Action Plan):
- `[x]` Triển khai Train V2 trên tập dữ liệu cắt nguyên bản NY Session (Đã vướng lỗi overfit ở Ep 200).
- `[x]` Ức chế nhiễu từ API Gemini 400 trong lớp AI Supervisor.
- `[ ]` Trích xuất bộ Dataset 100% từ MT5 và Re-train lại trên Trạm Client 1 hoặc Client GH.
- `[ ]` Dời mức kịch trần (Early Stopping) về Ep 180 để chốt chặn Val_Loss vùng `0.19`.

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: `20260412_181628_train`**
  - **Máy trạm:** `client1`
  - **Thời gian:** 12/04 18:16 - 22:30
  - **Tiến độ:** Ep 200+
  - **Loss:** Train `~0.1414` | Val `~0.2416`
  - **Winrate:** `>50%: N/A | >62%: N/A | >73%: N/A | >85%: N/A` *(Chưa thu thập kỹ từ Log cũ)*
  - **Ghi chú:** Bị ngắt (Stop Train) để chuyển qua Asian. Dấu hiệu Val_Loss hơi với (nguy cơ mớm overfit). Chốt model sớm mốc Ep 180 (Val: 0.19).

- **Lần chạy: `20260411_...`**
  - **Máy trạm:** `clientGH`
  - **Thời gian:** 11/04
  - **Tiến độ:** Ep 100+
  - **Loss:** N/A
  - **Winrate:** N/A
  - **Ghi chú:** Bị kẹt lỗi đụng độ Git Pull do rác hệ thống (Đã xử lý cơ chế cưỡng chế Hard Reset + Clean).

---

### 2.2. Nhánh: XAU Phiên Á (Asian Session)
Đặc trưng đánh theo kênh giá, biên độ nén hẹp, tỷ lệ rủi ro/phần thưởng (R:R) thấp nhưng tỷ lệ thắng (Winrate) trên các mốc tín hiệu lớn cực ổn định.

#### Kế hoạch thực thi (Action Plan):
- `[x]` Giao phó cấu hình kết thúc tự động (`training_end_time = 04:00`) cho Asian V2.
- `[x]` Chạy `deploy_agent` và khởi động lại `client1` với môi trường sạch.
- `[ ]` Phân tích Winrate và Loss của chuyến cày tàng hình đêm 12/04 rạng sáng 13/04.
- `[ ]` Đánh giá ngưỡng chống chịu Fakeout ở phiên Á.

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: `20260412_225726_train` (Đang chạy)**
  - **Máy trạm:** `client1`
  - **Thời gian:** 12/04 22:56+ --> Dự kiến kết thúc tự động 04:00 (13/04).
  - **Tiến độ:** Vừa vượt Ep 113+ (Tính tới 23:18)
  - **Loss:** Train `0.1334` | Val `0.2662` *(Sơ bộ Ep 113)*
  - **Winrate:** `>50%: 52.0% | >62%: 55.8% | >73%: 55.2% | >85%: 50.0%` *(Chụp tại Ep 113)*
  - **Ghi chú:** Máy đã bắt sóng Config thành công ở `C:\argo\data`. Tự động chốt quyền tắt vào lúc 04:00 sáng.

---

### 2.3. Nhánh: XAU Phiên Âu (London Session)
Khung thời gian mồi dòng tiền (14:00 - 19:30 VN). Nhiều pha bẻ gãy xu hướng Á để tạo tiền đề cho phiên Mỹ.

#### Kế hoạch thực thi (Action Plan):
- `[ ]` Export cấu hình `bot_config_xau_london_v2.json`.
- `[ ]` Khai thác Dataset 100% MT5 lọc chuẩn biên độ thời gian [07h00 - 12h30 UTC].
- `[ ]` Triển khai giao task cho `clientGH` chạy vét vào ban đêm.

#### Lịch sử các lần chạy (Run History):
*(Chưa khởi chạy)*

---

## 3. TRAINING V2 ARB (CRYPTO CUỐI TUẦN)

Ngách L2 Token (Arbitrum). Nén sóng mạnh vào T7, CN do Fiat nghỉ xả hơi.

#### Kế hoạch thực thi (Action Plan):
- `[x]` Định hướng lại Target Horizon bọc chóp lên `[5, 10, 15, 30]` phút (Bỏ khung 1-3m để tránh cắn hao hụt Spread).
- `[ ]` Đốc thúc `clientGH` chạy thử nghiệm full epoch.
- `[ ]` Báo cáo chiết khấu Winrate với mốc Target 5 phút.

#### Lịch sử các lần chạy (Run History):

- **Lần chạy: `demo_arb_run1`**
  - **Máy trạm:** `clientGH`
  - **Thời gian:** 12/04 21:30
  - **Tiến độ:** Quét Parquet
  - **Loss:** N/A
  - **Winrate:** N/A
  - **Ghi chú:** Bộ lọc ban đầu báo vớt được `0/3 file`. Đã khắc phục việc lộ đường viền Config và bắt Agent quy về ổ cứng `C:\argo`.

- **Lần chạy: `demo_arb_run2` (Upcoming)**
  - **Máy trạm:** `clientGH` (Dự kiến)
  - **Thời gian:** Sắp chạy...
  - **Ghi chú:** Chờ nạp bản Config mới với bộ Horzion 5-30m để kiểm chứng kết quả thực chiến vào dịp T7 tới.
