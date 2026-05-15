import sys
import os

# Add .agent to path so we can import
agent_dir = os.path.join(r"d:\DungLA\client1", ".agent")
sys.path.append(agent_dir)

from send_to_tele import send_to_telegram

content = '''🦅 [XÁC NHẬN LỆNH - UPDATE BASE TIMEFRAME]

Dạ Sếp, em đã cấu hình lại hệ thống theo lệnh:
1. **Config JSON**: Đã chuyển Base Timeframe của mô hình từ 5min lên 15min (WINDOW_SIZE tự động thu gọn lại còn 12 để cân đối độ dài chuỗi). 
2. **Prompt Auto-Tuning**: Đã cấp thêm quyền "ĐỔI LINH HOẠT Base Timeframe" vào lõi Prompt của State Machine. Kể từ giờ, thuật toán sẽ tự do thử nghiệm các khung 5m, 15m, 30m để tìm ra khung thời gian có tỉ lệ "phá nhiễu" tốt nhất.
3. **Kích hoạt lại Auto-Tuning**: Em đã mở khóa (enabled: true) cho cỗ máy State Machine chạy lại. Nó sẽ tự động kích hoạt vòng Continuous 44 trong chu kỳ quét sắp tới với hệ quy chiếu 15m mới toanh!

Hệ thống đã nạp xong đạn. Xin mời Sếp nghỉ ngơi để máy tiếp tục cày cuốc ạ!'''

send_to_telegram(content, is_done=True, target_channels="1816854047")
