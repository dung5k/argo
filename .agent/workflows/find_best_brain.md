---
description: Công cụ tìm kiếm Model HF hiệu quả nhất dựa trên Toán học Nội suy (Interpolation) và Cập nhật Bot.
---

# 🧠 Skill Workflow: Tìm Kiếm & Nâng Cấp Cấu Hình Não Bot (Find Best Brain)

Ngữ cảnh: Khi Model được huấn luyện liên tục trên Hugging Face (V2.1, V2...), file log `training_metrix_v2.json` sẽ chứa ma trận các mốc cắt (threshold) khác nhau. 
Bằng cách Nội suy (Interpolation), Skill này sẽ tìm một **điểm giao cắt có tổng số Tín hiệu phát ra (Total Signals) xấp xỉ mức mục tiêu** (mặc định = 100). Sau đó so sánh xem con AI nào cho ra tỷ lệ Win Rate tại điểm nội suy đó cao nhất. Cuối cùng tự động kéo thông số của "Người Vô Địch" và nhúng đè vào cấu hình của Giao dịch Bot.

## Cách sử dụng lệnh:

Sử dụng công cụ `run_command` để kích hoạt vòng chạy săn tìm Bộ não trên Cloud và cập nhật tự động bằng lệnh sau:

```powershell
python scripts/find_brain_skill.py
```

### Các Tùy chọn Mở Rộng:

- **Thay đổi Mốc nội suy Tín hiệu:** (Ví dụ muốn so sánh trên khía cạnh bot ra lệnh nhiều hơn ~150 lệnh)
  ```powershell
  python scripts/find_brain_skill.py --signals 150
  ```

- **Chỉ Scan kiểm tra, Không Đè file JSON:**
  ```powershell
  python scripts/find_brain_skill.py --no-apply
  ```

## 🛠️ Nguyên tắc Hoạt động bên trong:
1. Load Token từ `tg_config.json` và kết nối API phân luồng đống file `.json` của `Hugging Face`.
2. Trích xuất Array đệ quy tìm `threshold_metrics`.
3. Khớp và dùng hàm `numpy.interp` để nội suy kết quả `Threshold` và `Win Rate` tại mốc signal truyền vào cho toàn bộ model được tìm thấy ở mỗi khoảng phiên giao dịch.
4. Chọn lựa những bản thể có Win Rate cao nhất, và nhét cấu hình `run_id`, `weights`, và `entry_thresh` trực tiếp vào `bot_v2_brain_schedule.json`. 
5. LƯU Ý: Quá trình thiết lập vào Cấu hình Bot (**CỰC KỲ AN TOÀN**) không làm ghi đè hay hỏng các giá trị liên quan khác như `tp_pips` hay `sl_pips` vốn đã được thiết lập chặt chẽ bên trong file `json`.
