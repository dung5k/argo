import os
import subprocess
import sys

def main():
    print("=== BEGIN GIT RESET OTA ===")
    
    try:
        print("1. Đang chạy git reset --hard...")
        subprocess.run(["git", "reset", "--hard"], check=True)
        print("=> Xong git reset.")
    except Exception as e:
        print("Lỗi git reset:", e)

    try:
        print("2. Đang chạy git clean -fd...")
        subprocess.run(["git", "clean", "-fd"], check=True)
        print("=> Xong git clean.")
    except Exception as e:
        print("Lỗi git clean:", e)

    try:
        print("3. Đang chạy git pull...")
        subprocess.run(["git", "pull"], check=True)
        print("=> Xong git pull.")
    except Exception as e:
        print("Lỗi git pull:", e)

    print("=== KẾT THÚC GIT RESET OTA ===")

if __name__ == "__main__":
    main()
