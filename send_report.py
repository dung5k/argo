import os
import sys

# Change directory
os.chdir(r'd:\DungLA\client1')
sys.path.append(os.getcwd())

# Import send_to_tele
import importlib.util
spec = importlib.util.spec_from_file_location("send_to_tele", r"d:\DungLA\client1\.agent\send_to_tele.py")
send_to_tele = importlib.util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """📊 **Báo cáo Auto-Tuning LTC London (Local) + Fix Bug:**

🔧 **Vá lỗi Extension (VSIX 1.3.3):**
Tôi vô tình gõ nhầm một dấu xuống dòng (`\\n`) khiến file `send_to_tele.py` bị lỗi cú pháp `SyntaxError` ở lượt cập nhật 1.3.2 lúc nãy. Lỗi này đã được khắc phục hoàn toàn trong **VSIX 1.3.3**. Bạn tải lại bản 1.3.3 trên Github nhé!

❌ **Phân tích ldn_29:**
Lượt đào tạo `ldn_29` đã **Thất bại**! Việc thay đổi `CLS_HEAD` sang `residual` khiến mô hình Overfit mạnh, Val Loss tăng lên 0.7993 và Composite Score tụt thảm hại xuống 0.3357 (trong khi Baseline `ldn_23` là 0.4546). Ta chính thức loại bỏ hướng đi Residual Head khỏi kiến trúc.

🚀 **Điều phối (Dispatching):**
Máy Local vừa chuyển sang trạng thái IDLE, tôi đã lập tức kéo `ldn_30` từ Hàng Đợi ra và đã phát lệnh chạy đào tạo.
Lượt `ldn_30` thử nghiệm tính năng `VOL_REGIME=true` (Phân vùng biến động thị trường) dựa trên cấu trúc vàng của `ldn_23`.

🧹 **Storage:** Đã dọn dẹp xong từ trước (0.77 GB).

Đã hoàn tất toàn bộ luồng, tôi sẽ chuyển trạng thái về Rảnh!"""

send_to_tele.send_to_telegram(msg, is_done=True)
print("Sent successfully!")
