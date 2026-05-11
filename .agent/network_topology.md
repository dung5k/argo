# Bản Đồ Mạng Lưới ARGO (Multi-Agent Topology)

File này mô tả mạng lưới giao tiếp (Channels) giữa các Agents và Người Dùng (Sếp) đang chạy hệ thống Antigravity để phối hợp công việc. Bằng cách đọc cấu hình mạng lưới, mỗi AI Quant Engineer trên mỗi máy có thể biết được cách liên lạc với các thực thể khác trong mạng.

## 1. Cấu Trúc Kênh Giao Tiếp (Channels)

Danh sách chi tiết được cấu hình tại file `network_config.json`. Dưới đây là mô tả khái quát:

- **sep_agent1 (Sếp ↔ Agent 1):**
  - **Mô tả:** Kênh giao tiếp trực tiếp giữa Sếp và Agent 1 (chạy trên Máy Chính). Dùng để báo cáo tiến độ, nhận lệnh cấu hình cho các bot LTC/XAG.
  - **Mặc định:** Đây là kênh mặc định (`default_broadcast`) nhận các báo cáo nếu không có đích đến cụ thể.

- **sep_agent2 (Sếp ↔ Agent 2):**
  - **Mô tả:** Kênh giao tiếp trực tiếp giữa Sếp và Agent 2.

## 2. Phân Công Vai Trò (Agent Roles)

Để tối ưu hóa luồng công việc đa máy trạm, hệ thống phân chia rõ nhiệm vụ cốt lõi của từng Agent như sau:

- **Argo1 (Máy Chính):**
  - Đảm nhiệm giám sát, giao dịch và tối ưu hóa hệ thống Bot cho cặp tiền **LTC (Litecoin)**.
  - Xử lý các tác vụ quản trị cốt lõi và làm tổng trạm cho các tác vụ toàn cục.

- **Argo2 (Máy Nhánh / Auto-Tuning):**
  - **Nhiệm vụ ĐỘC QUYỀN:** Chịu trách nhiệm hoàn toàn về việc huấn luyện (training), backtest và tối ưu hóa siêu tham số (Hyperparameter tuning) cho các mô hình AI dự đoán cặp tiền **XAG (Bạc)**.
  - Không can thiệp vào tiến trình của LTC. Khi có kết quả huấn luyện XAG tốt, Argo2 sẽ báo cáo cho Sếp hoặc bắn lệnh qua mạng ngầm MQTT cho Argo1.

## 3. Giao Thức Liên Lạc (Communication Protocol)

Mỗi khi một Agent muốn báo cáo công việc hoặc ra lệnh cho thực thể khác, nó sẽ sử dụng hệ thống Telegram Router (thông qua `send_to_tele.py`).

**Cú pháp:**
```powershell
# Gửi tin nhắn mặc định vào kênh sep_agent1
python .agent/send_to_tele.py "Tin nhắn báo cáo bình thường..."

# Gửi tin nhắn vào kênh sep_agent2 để báo cho Agent 2
python .agent/send_to_tele.py "🤖 [Từ Sếp/Máy Chính] Yêu cầu báo cáo tiến độ phiên Á!" --channel sep_agent2

# Gửi thông báo khẩn cấp cho TẤT CẢ các kênh (Broadcast)
python .agent/send_to_tele.py "🚨 CẢNH BÁO TỪ MÁY CHÍNH: Dừng mọi tiến trình đào tạo để cập nhật code!" --channel all

# Gửi vào nhiều kênh cùng lúc
python .agent/send_to_tele.py "Thông báo chung cho cả 2 Agent" --channel sep_agent1,sep_agent2
```

## 4. Quản Trị Cấu Hình
Khi có nhóm chat mới (kênh mới) được tạo ra trong Telegram, người dùng chỉ cần thêm ID của nhóm chat tương ứng vào phần `channels` của `network_config.json`. Các Agent sẽ tự động cập nhật danh bạ này để giao tiếp chuẩn xác.
