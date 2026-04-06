---
description: Cách thức điều khiển và tương tác với các máy Trạm (Client Node) chạy Huấn luyện từ xa thông qua MQTT
---

# MQTT Workflow: Tương Tác Với Các Client Chạy Huấn Luyện

Hệ thống Huấn luyện Phân tán (Distributed AI Training) hoạt động dựa trên Giao thức MQTT (Machine-to-Machine) để quản lý tín hiệu và file giữa **Máy Chủ (Host/Master)** và **Máy Trạm (Client Nodes)**.
Tuyệt đối tuân thủ cấu trúc Pipeline này khi viết code để điều khiển quá trình huấn luyện:

## 1. Mạng Lưới Kết Nối (Connection Fabric)
- **Broker**: `broker.emqx.io` (Public Broker độ trễ thấp)
- **Cổng (Port)**: `1883`
- **Tiền tố Kênh (Prefix)**: `argo_dungla_9213`
- **Topic Nhận Lệnh (Command)**: `argo_dungla_9213/<client_id>/cmd`
- **Topic Báo Cáo (Log)**: `argo_dungla_9213/<client_id>/log`

## 2. API Của Host Controller (`host_controller.py`)
Máy Chủ sử dụng Class `HostController` để điều khiển Client. Các lệnh được gửi dưới dạng JSON payload. Có 5 dạng lệnh Tối cao:

### a) Lệnh Gọi Script Khởi động Trạm (`cmd: "run"`)
Ra lệnh cho Client chạy một script huấn luyện (ví dụ: `src/core/train_unified.py`).
```python
# Payload JSON
{"cmd": "run", "symbol": "xauusd", "script": "src/core/train_unified.py"}
```

### b) Lệnh Ép Chạy Code Sống (`cmd: "run_code"`)
Cho phép Host bơm thẳng mã nguồn Python dưới dạng văn bản thô (RAW Code) qua MQTT (tối đa 512KB). Client sẽ nhận cấu trúc này, lưu thành file tạm, và Execute. Rất hữu ích cho Testing Mạng Lưới:
```python
{"cmd": "run_code", "code": "print('Test MQTT in Client')\n#..."}
```

### c) Lệnh Gửi File Trực Tiếp (`cmd: "receive_file"`)
Truyền tải các tệp nhỏ (`<= 512KB` như `.yaml`, `.json` weights) trực tiếp qua kênh MQTT bằng mã hoá Base64. Giúp đồng bộ cấu trúc Config tức thời mà không cần qua Cloud.
```python
{"cmd": "receive_file", "dest": "data/bot_config.json", "filename": "bot_config_xau.json", "content_b64": "<BASE64_STRING>", "size": 1024}
```

### d) Lệnh Rút HuggingFace (`cmd: "pull_hf_file"`)
Đối với tệp quá khổ (`> 512KB` như Tensor Weights `.pth`, `scaler.pkl`), Host Controller sẽ **tự động upload lên HuggingFace**, sau đó gửi lệnh nhẹ này yêu cầu Client cắm API vào HuggingFace tải file về đích đến.
```python
{"cmd": "pull_hf_file", "hf_path": "data/scaler.pkl", "local_dest": "data/scaler.pkl"}
```

### e) Lệnh Deploy Toàn Mạng (`cmd: "deploy_agent"`)
Đây là lệnh Huỷ diệt. Máy chủ đè bản cập nhật mới của chính Agent Client (`client_tg_agent.py`) bằng Base64. Máy trạm nhận xong sẽ Shutdown tiến trình và Tự khởi động lại (Self-Restart) với bản Code mới.
```python
{"cmd": "deploy_agent", "version": "v1.3.5", "content_b64": "<BASE64_STRING>", "size": 33140}
```

## 3. Kiến Trúc Client Node (`client_tg_agent.py`)
- Lắng nghe 24/7 kênh `/cmd` do Host điều khiển.
- Mọi hoạt động `print`, PnL, hoặc Loss Rate của Client đều được wrap và **Bắn ngược lại `/log`** vào host theo dạng `{"level": "INFO", "message": "..."}`. Máy chủ nhận được sẽ hiển thị Real-time như thể đang chạy ở Localhost.
