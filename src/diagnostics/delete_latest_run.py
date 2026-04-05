import os
import shutil

runs_dir = os.path.join(os.path.dirname(__file__), "..", "runs")
if not os.path.exists(runs_dir):
    print("Không có thư mục runs.")
    exit(0)

# Bỏ qua thư mục old
subdirs = [os.path.join(runs_dir, d) for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d)) and d != "old"]
if not subdirs:
    print("Không có thư mục run nào ngoài old.")
    exit(0)

# Tìm thư mục mới nhất
latest_run = max(subdirs, key=os.path.getmtime)
print(f"Thư mục run mới nhất tìm thấy: {latest_run}")

# Xoá nó đi
try:
    shutil.rmtree(latest_run)
    print(f"✅ Đã xóa thành công thư mục rác: {latest_run}")
except Exception as e:
    print(f"❌ Lỗi khi xóa: {e}")
