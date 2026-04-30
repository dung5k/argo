import os
import subprocess

msg = "🚀 [NY Expert] Tôi đã soạn thảo xong toàn bộ KẾ HOẠCH NÂNG CẤP DỮ LIỆU ĐẦU VÀO (FEATURE ENGINEERING V4) cho bộ não LTC NY. Chiến thuật bao gồm 3 mũi nhọn: Tương quan Vĩ mô (DXY, SPX500, LTC/BTC), Cấu trúc Vi mô (OI, Funding) và Chỉ báo Neo thời gian (NY Open VWAP). Vui lòng xem bản Implementation Plan chi tiết để duyệt!"

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
