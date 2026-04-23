import os
import shutil
import glob
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

def cleanup_host_storage(keep_latest_n=3):
    """
    Dọn dẹp ổ cứng trên máy Host bằng cách xóa các file Tensor (.npy) khổng lồ 
    từ các lượt chạy (runs) cũ. Chỉ giữ lại Tensor của N lượt chạy mới nhất.
    """
    logging.info("🧹 BẮT ĐẦU QUY TRÌNH DỌN DẸP Ổ CỨNG TRÊN HOST...")
    workspaces_dir = "workspaces"
    
    if not os.path.exists(workspaces_dir):
        logging.warning(f"Thư mục {workspaces_dir} không tồn tại!")
        return

    total_freed_bytes = 0

    # Lặp qua tất cả các cấu hình (VD: CFG_LTC_NY_V3_5, CFG_LTC_ASIAN_V3_5, ...)
    for config_id in os.listdir(workspaces_dir):
        config_path = os.path.join(workspaces_dir, config_id)
        if not os.path.isdir(config_path):
            continue
            
        runs_dir = os.path.join(config_path, "runs")
        if not os.path.exists(runs_dir):
            continue
            
        # Lấy danh sách tất cả các run_id, sắp xếp theo tên (tương đương thời gian tạo)
        runs = sorted([d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))])
        
        if len(runs) <= keep_latest_n:
            logging.info(f"[{config_id}] Chỉ có {len(runs)} lượt chạy (<= {keep_latest_n}). Bỏ qua.")
            continue
            
        old_runs = runs[:-keep_latest_n]
        keep_runs = runs[-keep_latest_n:]
        
        logging.info(f"[{config_id}] Giữ lại {keep_latest_n} run mới nhất: {keep_runs}")
        logging.info(f"[{config_id}] Tiến hành xóa dữ liệu Tensor của {len(old_runs)} run cũ...")
        
        for old_run in old_runs:
            tensors_dir = os.path.join(runs_dir, old_run, "data", "tensors")
            if os.path.exists(tensors_dir):
                # Tính dung lượng sắp giải phóng
                for f in os.listdir(tensors_dir):
                    fpath = os.path.join(tensors_dir, f)
                    if os.path.isfile(fpath):
                        size = os.path.getsize(fpath)
                        total_freed_bytes += size
                        
                # Xóa thư mục tensors
                shutil.rmtree(tensors_dir, ignore_errors=True)
                logging.info(f"  🗑️ Đã xóa Tensors của: {old_run}")

    freed_gb = total_freed_bytes / (1024 ** 3)
    logging.info(f"✅ HOÀN TẤT! Tổng dung lượng đã giải phóng: {freed_gb:.2f} GB.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cleanup old run tensors on Host.")
    parser.add_argument("--keep", type=int, default=3, help="Số lượng run mới nhất cần giữ lại Tensors (Mặc định: 3)")
    args = parser.parse_args()
    
    cleanup_host_storage(keep_latest_n=args.keep)
