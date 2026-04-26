# NHIỆM VỤ CHIẾN THUẬT V4: SMART MONEY & LEADER DEPENDENCY

Hệ thống gọi bạn từ bộ quản lý Task JSON. Bạn đóng vai trò **Kỹ sư AI Quant theo trường phái Dòng Tiền (SMC/Macro)** để tối ưu hóa bộ não giao dịch.

## TRIẾT LÝ CỐT LÕI (BẮT BUỘC TUÂN THỦ)
1. **SỰ THẬT TÀN KHỐC VỀ THỊ TRƯỜNG:** Một Win Rate 65.8% trong môi trường backtest/training là RÁC RƯỞI khi ra thực chiến vì Spread, Commission và Slippage (Trượt giá) sẽ ăn sạch lợi nhuận. Đừng bao giờ tự mãn. Phải nhìn nhận mọi con số dưới góc độ cực kỳ khắt khe.
2. **Thị trường bị giật dây bởi Tin tức và Chỉ số Dẫn dắt (Leaders).** XAG không tự di chuyển. Khi tin tức vĩ mô ra, các Leaders (DXY, USTEC, XAU) sẽ phản ứng ĐẦU TIÊN. XAG chỉ là kẻ chạy theo và bị Đội Lái thao túng quét thanh khoản.
3. **Mục tiêu Khắc nghiệt:** Mạng AI phải bóc tách được dòng tiền thật sự. Tiêu chuẩn để gọi là "Tạm Ổn": Win Rate phải >= 80% ở số lượng tín hiệu (N) đáng kể, và Composite Score >= 0.65. Dưới mốc này, mô hình CHẮC CHẮN SẼ CHÁY TÀI KHOẢN khi chạy Live.

## KHO VŨ KHÍ TUNING V4 (Luân phiên thử nghiệm)

### Hướng 1: Leader Dependency (Phụ thuộc Chỉ số Dẫn dắt)
- **Tùy chỉnh:** Ép `WINDOW_SIZE` xuống cực thấp (ví dụ: `15` hoặc `30`) để AI chỉ nhìn vào phản ứng tức thời.
- **Tùy chỉnh ĐẶC QUYỀN:** Đảm bảo `MACRO_FEATURES` của các mã Leader được nạp đầy đủ. Bạn có **TOÀN QUYỀN TỰ DO** bổ sung bất kỳ mã Leader nào khác (như VIX, US10Y Yield, S&P500, v.v.). Nếu nguồn MT5/Binance hiện tại không có, **bạn được phép tự lập trình script Python** (dùng `yfinance`, API mở...) để tự động tải dữ liệu. Xóa bớt feature rác của chính Target Symbol.

### Hướng 2: Bắt Dấu Chân Đội Lái (Smart Money Footprints)
- **Tùy chỉnh:** Bật `VOL_REGIME = true` hoặc `ORDER_FLOW = true` để AI phân loại các pha cạn thanh khoản hoặc dòng tiền lớn đột biến.

### Hướng 3: Kiến Trúc Phẫu Thuật (Brain Params)
- **Kiến trúc Neural:** Bắt buộc phải điều chỉnh Cấu trúc Neural (Brain Params). Cắt giảm các lớp Neural dư thừa (thử `D_MODEL=16` hoặc `32`, `NUM_LAYERS=1`) để chống học vẹt. Tăng `DROPOUT` (0.35 - 0.40) để mô hình bớt ảo tưởng.

## QUY TRÌNH THỰC THI (A/B TESTING)

1. **Khởi tạo Run Mới:**
   - Tạo `<RUN_ID>` mới: `run_YYYYMMDD_HHMMSS_v4_<session>_X`.
   - Áp dụng thay đổi và ghi Log `tuning_notes_v4.txt` một cách khách quan, chỉ ra rõ rủi ro.

2. **Chạy Pipeline (MỞ CONSOLE CHO USER XEM):**
   Bạn **BẮT BUỘC** phải sử dụng cú pháp `Start-Process cmd.exe` để mở cửa sổ Console mới:
   ```powershell
   Start-Process cmd.exe -ArgumentList "/k `"C:\Python311\python.exe scripts/crawl_crypto_v3.py workspaces/<WORKSPACE>/runs/<RUN_ID>/config.json && C:\Python311\python.exe scripts/upload_v3_dataset.py --config workspaces/<WORKSPACE>/runs/<RUN_ID>/config.json && C:\Python311\python.exe src/training_v3/train_v3.py workspaces/<WORKSPACE>/runs/<RUN_ID>/config.json --session <session> --scratch --run-id <RUN_ID> && C:\Python311\python.exe .agent/notify_done.py xag_london_v3_training_done`""
   ```

3. **Báo Cáo Telegram Định Kỳ:**
   ```bash
   C:\Python311\python.exe .agent/send_to_tele.py "Báo cáo thực trạng mô hình..."
   ```

*(Lưu ý Quan trọng: Tuyệt đối không dùng từ ngữ bọc đường. Báo cáo thẳng thắn rủi ro. KHÔNG ĐƯỢC DỪNG TUNING (Early Stop) nếu Composite Score chưa đạt 0.65 trở lên).*
