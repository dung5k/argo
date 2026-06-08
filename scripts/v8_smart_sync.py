import os
import sys
import json
import time
import stat
import paramiko

# Force UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# --- Cấu hình ---
SYNC_STATE_FILE = "data/sync_state.json"
PROJECT_ROOT = "D:/DungLA/client1"
IGNORE_DIRS = [".git", "temp", "logs", "__pycache__", ".vscode", "v8_training", "workspaces", "tools"]
# Trong thư mục data, chỉ sync data/v8_splits (bỏ qua data/raw, data/processed...)
DATA_ALLOWED_SUBDIRS = ["v8_splits"]
TARGET_NODES = [
    {"id": "ARGO2", "ip": "192.168.1.18", "user": "dungla", "path": "D:/DungLA/Argo"},
    {"id": "ARGO3", "ip": "192.168.1.16", "user": "dungla", "path": "D:/DungLA/Argo"}
]
# Các loại file cần theo dõi để đồng bộ
WATCHED_EXTENSIONS = [".py", ".json", ".yaml", ".md", ".parquet"]

def get_last_sync_time():
    """Lấy thời gian đồng bộ thành công gần nhất."""
    if os.path.exists(SYNC_STATE_FILE):
        try:
            with open(SYNC_STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("last_sync_time", 0)
        except:
            return 0
    return 0

def update_last_sync_time():
    """Cập nhật thời gian đồng bộ."""
    os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
    with open(SYNC_STATE_FILE, "w") as f:
        json.dump({"last_sync_time": time.time()}, f)

def get_modified_files(last_sync):
    """Tìm tất cả các file đã được thay đổi từ lần đồng bộ cuối."""
    modified_files = []
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Loại bỏ các thư mục không cần thiết
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        # Trong thư mục data/, chỉ giữ các subdirs được phép
        rel_root = os.path.relpath(root, PROJECT_ROOT).replace("\\", "/")
        if rel_root == "data":
            dirs[:] = [d for d in dirs if d in DATA_ALLOWED_SUBDIRS]
        
        for file in files:
            # Chỉ lấy các file trong danh sách theo dõi
            if any(file.endswith(ext) for ext in WATCHED_EXTENSIONS):
                file_path = os.path.join(root, file)
                
                try:
                    # Lấy thời gian sửa đổi (mtime)
                    mtime = os.path.getmtime(file_path)
                    
                    # Nếu mtime lớn hơn lần đồng bộ cuối, đánh dấu là modified
                    if mtime > last_sync:
                        rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                        # Đảm bảo đường dẫn sử dụng '/' thay vì '\' cho hệ thống Linux (dù đích là Windows thì '/' vẫn an toàn hơn cho sftp)
                        rel_path = rel_path.replace("\\", "/")
                        modified_files.append((file_path, rel_path))
                except OSError:
                    pass
                    
    return modified_files

def sync_to_node(node, modified_files):
    """Đồng bộ danh sách file lên một node qua SFTP."""
    if not modified_files:
        return True
        
    print(f"\\n[{node['id']}] Đang kết nối đến {node['ip']}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Kết nối SSH (giả định dùng ssh key)
        key_path = os.path.expanduser('~/.ssh/id_rsa')
        client.connect(node['ip'], username=node['user'], key_filename=key_path, timeout=10)
        
        sftp = client.open_sftp()
        print(f"[{node['id']}] Đang đồng bộ {len(modified_files)} files...")
        
        for local_path, rel_path in modified_files:
            remote_path = f"{node['path']}/{rel_path}"
            
            # Đảm bảo thư mục đích tồn tại
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                # Tạo thư mục (dùng powershell -Force để tạo thư mục lồng nhau)
                win_dir = remote_dir.replace("/", "\\")
                _, stdout, _ = client.exec_command(f'powershell -Command "New-Item -ItemType Directory -Force -Path \'{win_dir}\'"')
                stdout.channel.recv_exit_status() # Đợi lệnh thực thi xong trước khi put file
                
            print(f"  -> Uploading: {rel_path}")
            sftp.put(local_path, remote_path)
            
        sftp.close()
        client.close()
        print(f"[{node['id']}] Đồng bộ hoàn tất!")
        return True
        
    except Exception as e:
        print(f"[{node['id']}] LỖI: {str(e)}")
        return False

def sync_code_to_cluster():
    """Chạy toàn bộ quy trình đồng bộ."""
    print("=== V8 SMART SYNC ===")
    
    last_sync = get_last_sync_time()
    print(f"Lần đồng bộ cuối: {time.ctime(last_sync) if last_sync > 0 else 'Chưa từng đồng bộ'}")
    
    modified_files = get_modified_files(last_sync)
    
    if not modified_files:
        print("Không có file nào thay đổi. Bỏ qua đồng bộ.")
        return
        
    print(f"Phát hiện {len(modified_files)} file thay đổi:")
    for _, rel in modified_files:
        print(f" - {rel}")
        
    all_success = True
    for node in TARGET_NODES:
        success = sync_to_node(node, modified_files)
        if not success:
            all_success = False
            
    if all_success:
        update_last_sync_time()
        print("\\n✅ Đã đồng bộ THÀNH CÔNG lên toàn bộ Cluster!")
    else:
        print("\\n❌ Có lỗi xảy ra trong quá trình đồng bộ ở một hoặc nhiều node.")

if __name__ == "__main__":
    sync_code_to_cluster()
