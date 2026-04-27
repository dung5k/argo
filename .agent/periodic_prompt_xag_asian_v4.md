# NHIỆM VỤ CHIẾN THUẬT V4: ASIAN SESSION (DU KÍCH & ĐÁNH NHANH)

Hệ thống gọi bạn từ bộ quản lý Task JSON. Bạn đóng vai trò **Kỹ sư AI Quant** để tối ưu hóa bộ não giao dịch cho phiên ASIAN (Phiên Á).

## ĐẶC ĐIỂM PHIÊN Á (ASIAN SESSION)
1. **Thanh khoản cực mỏng, giá lờ đờ:** Không giống như NY, phiên Á di chuyển rất chậm, thường xuyên đi ngang (sideway) với biên độ hẹp. 
2. **Bài học xương máu:** Tuyệt đối KHÔNG gồng lệnh dài (như TP/SL 50 pips của NY). Nếu gồng quá lâu ở phiên Á, AI sẽ bị "ảo tưởng" và có xu hướng đoán một chiều.
3. **Mục tiêu Khắc nghiệt:** Chiến lược hợp lý nhất là Đánh Du Kích (Scalping cực nhanh, ăn ít pips nhưng Win Rate cao). Mục tiêu vẫn là: **Win Rate >= 80%** và **Composite Score >= 0.65**.

## KHO VŨ KHÍ TUNING V4 CHO PHIÊN Á (Luân phiên thử nghiệm)

### Hướng 1: Rào cản Sinh tồn hẹp (Tight Triple Barrier)
- **Tùy chỉnh:** Hạ `TP_PIPS` và `SL_PIPS` xuống mức 15, 20, hoặc 30 pips. Giảm `MAX_HOLD_BARS` xuống khoảng 5 - 8 nến để AI dứt khoát thoát lệnh nhanh, tránh bị kẹt trong sóng sideway.

### Hướng 2: Bật lại Dấu Chân Đội Lái (Smart Money Footprints)
- **Tùy chỉnh:** Trái với phiên NY, ở phiên Á thanh khoản mỏng nên dấu chân SMC có thể rất hiệu quả! Thử bật lại `VOL_REGIME = true` hoặc `ORDER_FLOW = true` để xem mô hình có bắt được nhịp dòng tiền rỉ rích không.

### Hướng 3: Leader Dependency
- **Tùy chỉnh:** Tập trung vào các Leaders ảnh hưởng mạnh đến phiên Á: **Vàng (XAUUSDm), USDJPYm, và DXY**. Tránh dùng NASDAQ (USTECm) nếu không cần thiết vì giờ Mỹ đã đóng cửa. Đảm bảo `MACRO_FEATURES` nạp đủ các mã này.

## QUY TRÌNH THỰC THI (A/B TESTING)

1. **Khởi tạo Run Mới:**
   - Tạo `<RUN_ID>` mới: `run_YYYYMMDD_HHMMSS_v4_asian_X`.
   - Workspace: `workspaces/CFG_XAG_ASIAN_V3_5`
   - Áp dụng thay đổi và ghi Log `tuning_notes_v4.txt` một cách khách quan.

2. **Chạy Pipeline (MỞ CONSOLE CHO USER XEM):**
   Bạn **BẮT BUỘC** phải sử dụng cú pháp `Start-Process cmd.exe` để mở cửa sổ Console mới:
   ```powershell
   Start-Process cmd.exe -ArgumentList "/k `"C:\Python311\python.exe scripts/upload_v3_dataset.py --config workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json && C:\Python311\python.exe src/training_v3/train_v3.py workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json --session asian --scratch --run-id <RUN_ID> && C:\Python311\python.exe .agent/notify_done.py xag_asian_v4_training_done`""
   ```

3. **Báo Cáo Telegram Định Kỳ:**
   ```bash
   C:\Python311\python.exe .agent/send_to_tele.py "Báo cáo thực trạng mô hình..."
   ```

*(Lưu ý Quan trọng: Tuyệt đối không dùng từ ngữ bọc đường. Báo cáo thẳng thắn rủi ro. KHÔNG ĐƯỢC DỪNG TUNING (Early Stop) nếu Composite Score chưa đạt 0.65 trở lên).*

__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__
