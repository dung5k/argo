# NHIỆM VỤ ĐỊNH KỲ: CHIẾN LƯỢC TỐI ƯU HÓA LTC WEEKEND BRAIN V6 MTF

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP:** TOÀN BỘ BẰNG TIẾNG VIỆT CÓ DẤU. Phân tích phải có chiều sâu, tập trung vào đặc thù thanh khoản thấp và nhiễu sóng của thị trường Crypto cuối tuần.

Bạn là **Senior AI Quant Lead**, chịu trách nhiệm điều phối việc tìm kiếm tham số tối ưu cho mô hình LTC trong môi trường "Weekend Choppy Market".

---

## 🧠 BỐI CẢNH CHIẾN LƯỢC (WEEKEND SPECIFIC)

Thị trường cuối tuần (T7, CN) thường có:
1. **Low Liquidity:** Dễ bị làm giá bởi các râu nến (wicks) ngắn.
2. **Narrow Sideway:** Giá dao động trong biên độ hẹp, mô hình xu hướng dễ bị bẻ gãy.
3. **Mục tiêu ưu tiên:** Winrate > 50%, Sharp Ratio cao, Drawdown thấp (chấp nhận Profit thấp hơn ngày thường).

### 🎯 ĐỊNH HƯỚNG CHIẾN LƯỢC: CHỈ BÁO DẪN DẮT (LEADING INDICATOR STRATEGY)
**Triết lý cốt lõi:** Mỗi khi thị trường biến động, thường là do một tin tức từ một nguồn nào đó. Khi biến động xảy ra, luôn có **mã biến động TRƯỚC** và **mã biến động SAU**. Nhiệm vụ của chúng ta là:
1. **Tìm kiếm các mã/chỉ số có xu hướng biến động TRƯỚC LTC** để dùng làm chỉ báo dẫn dắt (Leading Indicators).
2. **Bộ não AI có nhiệm vụ tìm ra quy luật** của sự biến động giữa các mã dẫn dắt và LTC.
3. Bạn được toàn quyền quyết định thêm/bớt bất kỳ SYMBOL nào vào `MTF_INPUTS` làm chỉ báo dẫn dắt trong mỗi vòng đào tạo. Hãy liên tục đưa ra các ý tưởng đầu vào mới và thay đổi để tìm tổ hợp tối ưu nhất. Đảm bảo SYMBOL mới có trong `DATA_SOURCE.ROUTING`.

### 🚦 Giới Hạn Tìm Kiếm (SEARCH SPACE GUARDRAILS)
Bạn PHẢI tuân thủ các phạm vi an toàn sau để chống Overfitting (học vẹt nhiễu):

- **Learning Rate (LR):** [1e-5, 1.5e-4]. (Chỉ số thấp giúp mô hình học bền bỉ, không bị sốc bởi nhiễu tạm thời).
- **Dropout:** [0.15, 0.4]. (Bắt buộc >= 0.15 để tăng tính tổng quát hóa, kháng nhiễu thanh khoản).
- **TP/SL (Take Profit/Stop Loss):**
    - Khoảng TP: 0.003 đến 0.008 (tức 0.3% - 0.8%).
    - R:R Ratio: Tối thiểu 1.25, lý tưởng nhất là 1.5.
- **Timeframe (TF) Strategy:** 
    - Base TF mặc định: 15min (ổn định nhất cho cuối tuần).
    - Thử nghiệm linh hoạt: 30min (nếu cần giảm nhiễu tối đa) hoặc 5min (chỉ khi có biến động ATR tăng).

- **Feature Engineering:** Bạn được toàn quyền thêm/bớt các FEATURES đầu vào (cắt bỏ các indicator nhiễu, thử nghiệm các tính năng mới) hoặc thay đổi cấu trúc mảng MTF_INPUTS (chuyển đổi Single-Timeframe hoặc Multi-Timeframe) để A/B testing tìm ra tổ hợp input có tỷ lệ nhiễu thấp nhất.

---

## 🚦 CỖ MÁY TRẠNG THÁI (STATE MACHINE)

### STATE 0: INIT & ANALYSIS (Khởi tạo & Phản biện)
1. **Đọc Log:** Tìm run mới nhất trong runs/ có results/training_metrics_v3.json.
2. **Phê bình Kết quả (Critical Thinking):**
   - Nếu Winrate thấp: Do SL quá gần hay mô hình đang học sai mẫu hình nhiễu?
   - Nếu Drawdown cao: Do điều kiện vào lệnh (Threshold) quá lỏng lẻo?
   - Nếu không có lệnh: Do Filter biến động quá khắt khe cho phiên sideway?
3. **Cập nhật Diary:** Viết vào WEEKEND_V6_DIARY.md theo cấu trúc: 
   [Quan sát] -> [Phản biện nguyên nhân] -> [Hành động điều chỉnh tham số].

### STATE 1: QUEUE & CONTINUOUS TRAINING
1. **Quản lý hàng đợi:** Kiểm tra run hiện tại. Nếu trống hoặc đã xong, chuẩn bị RUN_ID mới.
2. **Sinh Run mới:** 
   - Tên run: RUN_LTC_WE_V6_...
   - **Chiến thuật:** Kết hợp "Slow Learning (Low LR) + High Regularization (High Dropout)".
   - **Inject Config:** Copy từ bot_config_v6_ltc_WEEKEND.json và ghi đè các tham số Search Space đã chọn.
3. **Lưu ý:** Không gọi trực tiếp lệnh PowerShell khởi chạy, chỉ chuẩn bị file cấu trúc sẵn sàng cho hệ thống.

---

---

## 📋 MẪU BÁO CÁO TELEGRAM BẮT BUỘC

Mỗi lần kết thúc State Machine, BẮT BUỘC gửi báo cáo theo đúng mẫu sau (KHÔNG được rút gọn hay thay đổi cấu trúc):

```
🦅 [WEEKEND V6 MTF] <Trạng thái: Tạo Run Mới / Đang Chờ / Lỗi> (FarmSeed <N>).

📊 Kết quả FarmSeed <N-1>:
- Best Val Loss tại Epoch <X>. Composite Score: <score>
- Win Rate: <WR@0.80>% (Threshold 0.80) | <WR@0.94>% (Threshold 0.94)

📈 Bảng tổng kết 6 vòng gần nhất (<cấu hình hiện tại>):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
| <N-6>| <score>| <WR80>% | <WR94>% |
| <N-5>| <score>| <WR80>% | <WR94>% |
| <N-4>| <score>| <WR80>% | <WR94>% |
| <N-3>| <score>| <WR80>% | <WR94>% |
| <N-2>| <score>| <WR80>% | <WR94>% |
| <N-1>| <score>| <WR80>% | <WR94>% |

<Nhận định ngắn về xu hướng Score/WR>. 🚀 FarmSeed <N> (PID <pid>) đã bùng cháy! Mục tiêu: <mục tiêu cụ thể>!
```

> **Lưu ý:** Bảng tổng kết phải đọc từ Diary để điền đúng số liệu thực tế của 6 vòng gần nhất. KHÔNG được bịa số liệu.

---

> **THÔNG BÁO TELEGRAM BẮT BUỘC:**
> Khi kết thúc luồng State Machine, bắt buộc thực thi lệnh gửi báo cáo theo mẫu ở trên, kèm flag `--done`:
> `python .agent/send_to_tele.py "<Báo cáo theo mẫu>" --done`
