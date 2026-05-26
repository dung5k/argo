# Thông tin máy Argo2 (Chuyên XAG)

## 1. Thông tin chung
- **Vai trò:** Máy chuyên trách đào tạo mô hình XAG và chạy Trade Bot XAG.
- **IP Address:** `192.168.1.18`
- **Username:** `dungla`
- **Thư mục dự án:** `d:\DungLA\Argo`

## 2. Cấu hình bảo mật
- Đã được thiết lập kết nối **SSH Key** tự động (không cần mật khẩu) từ máy chủ chính (Argo1).
- Key xác thực được lưu tại hệ thống của Windows Admin: `C:\ProgramData\ssh\administrators_authorized_keys`
- Đã được nạp đầy đủ các token môi trường cần thiết (Telegram, Gemini, HuggingFace).

## 3. Cách theo dõi tiến trình (Log Real-time)
Do lệnh đào tạo (`autonomous_training_loop.py`) được khởi chạy ngầm qua SSH để đảm bảo ổn định và không chiếm dụng màn hình, bạn không thể nhìn thấy cửa sổ CMD vật lý trên máy Argo2. 

Tuy nhiên, bạn có thể **kéo log trực tiếp về máy hiện tại (Argo1)** để xem real-time giống hệt như lệnh `tail -f` trên Linux.

### Lệnh PowerShell để xem log từ xa:
Mở PowerShell trên máy Argo1 và chạy lệnh sau (thay đổi đường dẫn file log tùy theo phiên đang chạy):

```powershell
# Ví dụ xem log của phiên ASIAN V6
ssh dungla@192.168.1.18 "Get-Content D:\DungLA\Argo\workspaces\CFG_XAG_ASIAN_V6\runs\*\train_v6.log -Wait -Tail 20"
```

*Giải thích:*
- `-Wait`: Liên tục chờ và cập nhật nội dung mới khi file log được ghi thêm.
- `-Tail 20`: Chỉ hiển thị 20 dòng cuối cùng trước khi bắt đầu stream.

Để thoát chế độ xem log, nhấn `Ctrl + C`. Tiến trình đào tạo trên Argo2 **vẫn sẽ tiếp tục chạy ngầm** một cách an toàn.
