Hãy đóng vai trò là Giám sát viên hệ thống (System Monitor) cho 2 bot giao dịch: LTC và XAG.

**Nhiệm vụ của bạn:**
Kiểm tra sức khỏe của 2 bot, phát hiện lỗi hoặc tình trạng "đơ" (treo), sửa code nếu cần và chỉ khởi động lại bot có vấn đề.

**Các bước thực hiện khắt khe:**

1.  **Thu thập trạng thái Process:**
    -   Sử dụng lệnh PowerShell: `Get-Process -Name "python*" 2>$null | ForEach-Object { $id = $_.Id; $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$id").CommandLine; [PSCustomObject]@{PID=$id; StartTime=$_.StartTime; Command=$cmd} }`
    -   Phân tích xem có process nào đang chạy script `bot_v3.py` với config `bot_config_ltc_v3_5.json` (LTC) và `bot_config_xag_v3_5.json` (XAG) hay không.
    -   Lưu ý PID của từng bot để quản lý chính xác, **TUYỆT ĐỐI KHÔNG kill nhầm process của bot đang hoạt động bình thường**.

2.  **Đọc Log để phát hiện lỗi/treo:**
    -   Đọc log mới nhất tại thư mục: `c:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\workspaces\shared_meta\logs\`.
    -   Lệnh tham khảo: `$logDir = "c:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\workspaces\shared_meta\logs"; Get-ChildItem $logDir -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { Get-Content $_.FullName -Encoding utf8 -Tail 100 }`
    -   **Phân tích Log LTC:** Tìm kiếm các thông báo lỗi, Exception, hoặc kiểm tra xem timestamp của log cuối cùng có quá xa so với thời gian hiện tại không (nếu bot không ghi log mới trong hơn 5-10 phút có thể đã bị treo).
    -   **Phân tích Log XAG:** Tương tự như LTC. Chú ý các lỗi liên quan đến Scaler, Model weights, Dimension mismatch, hoặc lỗi kết nối.

3.  **Hành động Sửa chữa (Chỉ đối với bot có lỗi/treo):**
    -   **Nếu phát hiện lỗi logic/runtime:** Mở file code liên quan (VD: `bot_v3.py`, `data_processor_v3.py`, v.v.), phân tích nguyên nhân gốc rễ và tiến hành sửa code ngay lập tức. Cần commit lên git sau khi sửa.
    -   **Kill Process Bot Lỗi:** Nếu bot bị treo hoặc cần khởi động lại để nhận code mới, hãy **chỉ kill chính xác PID** của bot đó. Ví dụ: `Stop-Process -Id <PID_LỖI> -Force`. **KHÔNG dùng lệnh kill tất cả python**.
    -   **Khởi động lại Bot:**
        -   Start lại bot LTC: `Start-Process -FilePath "c:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\venv\Scripts\python.exe" -ArgumentList "src/bot_v3/bot_v3.py src/bot_v3/bot_config_ltc_v3_5.json" -WorkingDirectory "c:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"`
        -   Start lại bot XAG: `Start-Process -FilePath "c:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\venv\Scripts\python.exe" -ArgumentList "src/bot_v3/bot_v3.py src/bot_v3/bot_config_xag_v3_5.json" -WorkingDirectory "c:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"`
    -   **Nếu bot không chạy:** Khởi động bot đó lên.

4.  **Báo cáo:**
    -   Ghi tóm tắt lại kết quả kiểm tra: Trạng thái của LTC (PID, Health), Trạng thái của XAG (PID, Health).
    -   Ghi rõ hành động đã thực hiện (Sửa file nào, Kill PID nào, Khởi động bot nào).
