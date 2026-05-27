import os
import sys

def install_hook():
    git_dir = ".git"
    if not os.path.exists(git_dir):
        print("Lỗi: Không tìm thấy thư mục .git. Vui lòng chạy script này ở thư mục gốc của project.")
        sys.exit(1)
        
    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    
    pre_commit_path = os.path.join(hooks_dir, "pre-commit")
    
    hook_content = """#!/bin/sh
# Chặn tuyệt đối việc commit các file cấu hình nhạy cảm mang tính Local

FORBIDDEN_FILES=".agent/tasks.json .vscode/settings.json"

for file in $FORBIDDEN_FILES; do
    if git diff --cached --name-only | grep -q "$file"; then
        echo "============================================================"
        echo "⛔ LỖI BẢO MẬT NGHIÊM TRỌNG (PRE-COMMIT HOOK) ⛔"
        echo "Bạn (hoặc AI Agent) đang cố gắng commit file cấu hình cục bộ:"
        echo "=> $file"
        echo "Hành động này bị chặn tuyệt đối để tránh làm loạn hệ thống Bot!"
        echo "Vui lòng chạy lệnh: git restore --staged $file"
        echo "============================================================"
        exit 1
    fi
done

exit 0
"""
    
    try:
        with open(pre_commit_path, "w", encoding="utf-8") as f:
            f.write(hook_content)
        
        # Cấp quyền thực thi trên Linux/Mac (Windows thường bỏ qua cái này nhưng làm cho chắc)
        if os.name != 'nt':
            os.chmod(pre_commit_path, 0o755)
            
        print("✅ Thành công! Đã cài đặt 'Người gác cổng' Pre-commit Hook.")
        print("Từ giờ, hệ thống Git trên máy này sẽ tự động CHẶN ĐỨNG mọi nỗ lực commit file tasks.json hoặc settings.json.")
    except Exception as e:
        print(f"Lỗi khi ghi file hook: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_hook()
