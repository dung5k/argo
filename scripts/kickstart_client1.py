import subprocess
import time

print("1. Gửi lệnh cập nhật code từ Git (git pull)...")
subprocess.run(["python", "src/orchestration/host_controller.py", "update", "-c", "client1"])

time.sleep(3) # Đợi Client1 restart sau update

print("\n2. Đảm bảo thư viện requests được cài đặt trên Client1 (tránh lỗi HF pull)...")
install_code = """import subprocess\nimport sys\nsubprocess.run([sys.executable, '-m', 'pip', 'install', 'requests', 'certifi', 'huggingface_hub', 'numpy'])\nprint('PIP INSTALL DONE!')"""
with open("tmp_install.py", "w") as f:
    f.write(install_code)

subprocess.run(["python", "src/orchestration/host_controller.py", "run", "-c", "client1", "--script", "tmp_install.py"])

time.sleep(5)

print("\n3. Ra lệnh TRAIN cho Client1...")
subprocess.run(["python", "src/orchestration/host_controller.py", "train", "-c", "client1", "-s", "XAGUSD"])
print("Xong!")
