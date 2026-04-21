# QUY ĐỊNH LƯU TRỮ VÀ ĐỒNG BỘ WORKSPACES

Tài liệu này quy chuẩn hóa cách thức lưu trữ nội bộ (Local/Git) và cơ chế phát triển trên Đám mây (Hugging Face) của hệ thống Trading dựa trên cấu trúc Workspaces độc lập (Silo).

## 1. Cấu trúc Mô hình Độc Lập (Silo Workspace)

Hệ thống quản lý dữ liệu không qua thư mục gộp `data/` mà chia nhỏ hoàn toàn độc lập cho mỗi bộ Cấu hình (Config ID), ví dụ *`CFG_XAG_LONDON_V3_5`*.
```text
workspaces/
├── CFG_XAG_LONDON_V3_5/
│   ├── bot_config_xag_london_v3_5.json  # Lưu file cấu hình gốc của cấu hình
│   ├── data/
│   │   ├── raw/         # Chứa Dữ liệu Thô cào từ MT5 (các file .parquet ~ Hàng Gb)
│   │   └── tensors/     # Chứa dữ liệu tinh chế Numpy (.npy) và Scaler (.pkl)
│   ├── brains/          # Chứa các model Weights (.pth) và File Thành tích đào tạo (.json)
│   └── trading_logs/    # Ghi log riêng biệt trong quá trình Bot chạy Live
└── shared_meta/         # Chứa các catalog và schedule chung dùng cho điều hướng hệ thống
```

## 2. Quy Định Đối với Git Local (Kho chứa Mã Nguồn)

Thư mục `workspaces` đã được thiết lập một "Trạm Gác" khắt khe qua tệp `.gitignore` cục bộ để bảo vệ kích thước Repo Git không bị thổi phồng.

- **[CHỈ CHO PHÉP]**: Git **chỉ theo dõi** và Commit các tập tin nhẹ mang tính cấu trúc:
  - File cấu hình (`*.json`)
  - Bảng thành tích Huấn luyện / Gợi ý (`*.json`, `*.txt`)
  - File tài liệu (`*.md`)
- **[NGHIÊM CẤM]**: Mọi dữ liệu vật lý thể rắn hay trọng lượng nặng đều sẽ bị ẩn và cấm đẩy lên Git:
  - Tập tin Dữ liệu thô `.parquet`
  - Các ma trận Tensor `.npy`
  - Trọng số AI `.pkl`, `.pth`
  - Lịch sử Giao dịch và Log (`trading_logs/*`)

## 3. Quy Định Đồng Bộ Lên Hugging Face (Kho chứa Tài Nguyên Training)

Kho lưu trữ Hub Đám mây HuggingFace (`dung5k/argo_workspaces`) đóng vai trò kho trung gian nạp đạn (Fetch) cho các Master/Slave Clients trong quá trình Đào tạo Phân tán.

- **[ĐỒNG BỘ]**:
  - `data/tensors/`: Không thể thiếu trong lúc Train (được dùng thay vì load Parquet lại từ đầu nhằm tối ưu I/O máy con).
  - `config/`: Chia sẻ cấu hình cho Client nạp HyperParameters.
  - `brains/`: Sync não bộ 2 chiều.

- **[TỐI KỊ - TUYỆT ĐỐI KHÔNG ĐỒNG BỘ]**:
  - `data/raw/*.parquet`: Tại máy Trạm Training không dùng dữ liệu thô nên việc đồng bộ Hàng Chục/Trăm Gb định dạng Parquet lên Mây là lãng phí nghiêm trọng Băng thông, Thời gian và gây Nặng Cloud. Dữ liệu Raw CHỈ NẰM Ở MÁY CHỦ MASTER.

🚨 **Lưu ý thao tác của Kỹ Sư**: Trong mọi Script Đồng bộ (Push HF API), phải luôn set điều kiện loại trừ thư mục `*/data/raw/*` và `*.parquet`.
