import os
import time
from huggingface_hub import HfApi, snapshot_download

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

REPO_ID = "dung5k/argo_workspaces"
LOCAL_DIR = "workspaces"

# Cấm đồng bộ dữ liệu siêu nặng (Được kế thừa từ STORAGE_POLICY)
IGNORE_RULES = [
    "*/data/raw/*", 
    "*.parquet"
]

def main():
    token = os.environ.get("HF_TOKEN", "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")
    if not token:
        log("❌ Lỗi: Không tìm thấy Token HF.")
        return

    log("="*50)
    log("🚀 KHỞI ĐỘNG CÔNG CỤ ĐỒNG BỘ THÔNG MINH (SMART SYNC) 2 CHIỀU")
    log("📌 Kịch bản: Bắt buộc Kéo (Pull) trước, Cập nhật (Push) sau.")
    log("📌 Luồng Cấm: Bỏ qua 100% dữ liệu Raw Parquet cho cả 2 luồng.")
    log("="*50)

    # 1. PULL (Kéo về các File bị thiếu hoặc Mới hơn)
    log("\n⬇️ BƯỚC 1: ĐANG KÉO (PULL) TÀI NGUYÊN TỪ MÂY XUỐNG MÁY...")
    log("   (Xin chờ trong giấy lát, hệ thống đang Hashing để so khớp...)")
    try:
        snapshot_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            local_dir=".",
            allow_patterns=["workspaces/*"],
            local_dir_use_symlinks=False,  
            ignore_patterns=IGNORE_RULES,
            token=token,
            max_workers=4
        )
        log("✔️ Kéo (Pull) tài nguyên hoàn tất! Local đã nhận đủ mảnh ghép của Đám mây.")
    except Exception as e:
        log(f"❌ Lỗi nghiêm trọng lúc PULL: {e}")

    # 2. PUSH (Đẩy lên các File mới Train xong ở Local)
    log("\n⬆️ BƯỚC 2: ĐANG TẢI (PUSH) NHỮNG THAY ĐỔI CỤC BỘ LÊN ĐÁM MÂY...")
    log("   (Chỉ những File như Model.pth hoặc Config vừa sửa mới được kích Hoạt Upload...)")
    try:
        api = HfApi(token=token)
        api.upload_folder(
            folder_path=LOCAL_DIR,
            repo_id=REPO_ID,
            path_in_repo="workspaces",
            repo_type="dataset",
            ignore_patterns=IGNORE_RULES,
            commit_message="Smart Sync: Tự động tải lên các thay đổi mới nhất từ Client",
            run_as_future=False
        )
        log("✔️ Tải lên (Push) HF hoàn tất! Repo đã ghi nhận thay đổi.")
    except Exception as e:
        log(f"❌ Lỗi nghiêm trọng lúc PUSH: {e}")

    log("="*50)
    log("🎉 CHUYẾN ĐỒNG BỘ HAI CHIỀU KẾT THÚC MỸ MÃN.")
    log("="*50)

if __name__ == "__main__":
    main()
