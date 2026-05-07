# KỸ NĂNG: GIAO TIẾP MẠNG NGẦM (MQTT INTER-AGENT COMMUNICATION)

> **CẢNH BÁO QUAN TRỌNG DÀNH CHO MỌI AGENT:** Từ phiên bản hệ thống 1.5.1, giao thức giao tiếp giữa các Bot đã được nâng cấp. BẠN TUYỆT ĐỐI KHÔNG ĐƯỢC dùng lệnh `send_to_tele.py` để gửi tin nhắn cho một Agent khác, vì giới hạn API của Telegram không cho phép Bot đọc tin nhắn của Bot.

## 1. Mục Đích
Kỹ năng này giúp bạn gửi yêu cầu, dữ liệu, hoặc ra lệnh cho một Agent khác (ví dụ: Argo1 gọi Argo2) thông qua mạng ngầm MQTT với độ trễ gần như bằng 0, xuyên thủng mọi tường lửa mà không phụ thuộc vào Telegram.

## 2. Công Cụ Sử Dụng
Bắt buộc sử dụng công cụ Python sau:
```bash
python .agent/send_mqtt.py "<Nội_dung_lệnh_chi_tiết>" --target <Tên_Agent_Đích>
```

## 3. Các Bước Thực Hiện (Workflow)

Khi Người điều hành (Sếp) hoặc hệ thống yêu cầu bạn "Hỏi Argo1" hoặc "Giao việc cho Argo2":
1. **Xác định thông điệp:** Tổng hợp nội dung cần nhắn nhủ (lệnh cần thực thi, câu hỏi, dữ liệu).
2. **Xác định đích đến:** Tên định danh của Agent bên kia (phân biệt hoa thường, ví dụ: `Argo1`, `Argo2`).
3. **Thực thi gọi MQTT:** Chạy lệnh `send_mqtt.py`. Mọi thao tác này sẽ tự động được hệ thống log lên Telegram Group, bạn không cần phải gọi `send_to_tele.py` nữa (hệ thống sẽ làm thay bạn).
4. **Kết thúc báo rảnh:** Sau khi gọi `send_mqtt.py` thành công, bạn phải dùng `send_to_tele.py "<Báo_cáo> --done` để giải phóng trạng thái BUSY của chính mình, để chờ phản hồi từ Agent kia gửi lại.

## 4. Ví Dụ Cụ Thể

**Tình huống:** Bạn là Argo2, Sếp yêu cầu bạn: "Hãy gửi lời chào và báo cho Argo1 biết hệ thống đã sẵn sàng".
**Hành động ĐÚNG:**
1. Chạy lệnh:
   ```bash
   python .agent/send_mqtt.py "Xin chào Argo1, tôi là Argo2. Hệ thống pipeline của tôi đã sẵn sàng. Hãy phản hồi nếu bạn nhận được tin nhắn này!" --target Argo1
   ```
2. Kết thúc ca làm việc của bạn:
   ```bash
   python .agent/send_to_tele.py "Đã phát lệnh MQTT ngầm tới Argo1 thành công." --done
   ```

**Hành động SAI (Nghiêm cấm):**
   ```bash
   # SAI: Bot kia sẽ không bao giờ đọc được!
   python .agent/send_to_tele.py "Chào Argo1" --channel agent1_agent2
   ```

Hãy học và áp dụng kỹ năng này cho mọi tương tác ngang hàng (Agent-to-Agent) từ nay về sau!
