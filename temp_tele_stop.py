import os
import subprocess

msg = "🚀 [NY Expert] Đã nảy ra ý tưởng mới: CẠN KIỆT KHÔNG GIAN TUNING! Sau 8 lượt thay đổi cấu hình (Scalping, Macro, Order Flow, Volatility, Residual Head) điểm số vẫn bị nghẽn ở dưới 0.60. Vấn đề cốt lõi có thể nằm ở Feature Data hoặc Model Core. Tôi đã DỪNG tiến trình Auto-Tuning để tiết kiệm tài nguyên. Nhật ký đánh giá chi tiết đã đẩy lên HF để sếp xem xét các bước tiếp theo."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
