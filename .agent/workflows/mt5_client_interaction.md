---
description: Cách thức kết nối và quản lý chuỗi Multi-Terminal MT5 Clients (Mạng lưới IPC In-Memory)
---

# MT5 Client Interaction Workflow

Dự án này sử dụng nhiều MT5 Client (Terminals) cài trên máy Local để phục vụ cho việc khảm đa dạng tín hiệu từ các môi trường Giao dịch/Sàn khác nhau (Forex, Crypto, Vĩ mô, Indices Nhật/Phố Wall). 
Khi nhận được yêu cầu tinh chỉnh bộ thu nhận Data, hay check symbols, AI Agent (hay bất cứ module nào) phải T UYỆT ĐỐI làm theo quy trình dưới đây nhằm tránh treo giao tiếp IPC (Inter-Process Communication):

## 1. Các Đường dẫn Clients (Paths) gốc đã đăng ký
Có 4 Terminal MT5 hiện được quy hoạch và chạy ngầm (Background) trên máy của User:
1. `C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe` (Sàn Exness: Chuyên trị toàn bộ rổ Crypto (BTC, BNB...), Hàng hoá, và Chỉ số JP225, XAU).
2. `C:\Program Files\MetaTrader 5\terminal64.exe` (Sàn gốc: Dành riêng hút dữ liệu Vĩ mô đặc biệt như VIXY).
3. `C:\Program Files\MetaTrader 5 - 2\terminal64.exe` (Backup Node 1).
4. `C:\Program Files\Mtrading MetaTrader 5\terminal64.exe` (Backup Node 2).

## 2. Quy tắc Đổi Kênh Cứng (Rapid IP Switching)
API `MetaTrader5` trong Python chạy một Instance Singleton kết nối duy nhất ở bất kỳ thời điểm nào. Không được kết nối nhiều luồng. Nếu cần cào từ Sàn Gốc, rồi bay sang cào từ Sàn Exness, thì phải thực hiện "Ngắt xả" (`shutdown`) trước:

```python
import MetaTrader5 as mt5

# Bước 1: Luôn shutdown Client trước đó kể cả khi không rõ phiên trước có mở hay không!
mt5.shutdown()

# Bước 2: Khởi tạo Client bằng đường dẫn tường minh (nếu không truyền path, nó sẽ trượt ngẫu nhiên về bản Gốc)
success = mt5.initialize(path=r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")

if success:
    # Bước 3: Symbol_select (Cực quan trọng để bóc nến)
    mt5.symbol_select("BTCUSDm", True)
    
    # Bước 4: Hút mảng giá trị (Rates tuple)
    rates = mt5.copy_rates_from_pos("BTCUSDm", mt5.TIMEFRAME_M1, 0, 120)
    
# Cổng IPC đóng hoàn chỉnh:
mt5.shutdown()
```

## 3. Chiến Thuật Dò Quét Auto-Discovery Mạng Lưới
Khi mạng Nơ-ron huấn luyện thêm biến mới (Scaler nhét thêm mã AAAUSD) mà chưa rõ Sàn nào trong 4 Sàn kia hỗ trợ, Agent PHẢI:
- Lặp qua mảng 4 `paths`.
- Gọi block Switch IPC (shutdown -> init -> get_symbols -> shutdown).
- Lưu lại danh sách đọ từ `mt5.symbols_get()` để tự động lập Bản Đồ Định Tuyến (Router Map), sau đó mới nhét vào vòng lặp chạy Live để loại bỏ Delay.

*Lưu ý: Thời gian ngắt mở ống IPC ở Local chỉ diễn ra dưới `~0.15` giây, nên thao tác này được phép để ngầm sâu trong Thread Live Trading.*
