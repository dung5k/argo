import sys
import os

print("Đang khởi động App Cầu Nối (Tele Bridge) từ phiên bản mới V6...", flush=True)

# Chuyển hướng sang file listener thực sự ở thư mục .agent
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
target_script = os.path.join(project_root, '.agent', 'argo_tele_listener.py')

if os.path.exists(target_script):
    os.execv(sys.executable, [sys.executable, target_script] + sys.argv[1:])
else:
    print(f"Lỗi: Không tìm thấy file gốc tại {target_script}", file=sys.stderr)
