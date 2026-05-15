import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình: Tạo Run Mới (Vòng 6).
🚨 Tình trạng Vòng 5: Đã phát hiện tiến trình bị CRASH NGẦM (Lỗi PyTorch STATUS_STACK_BUFFER_OVERRUN) do `CONFIG_ID` bị sai, dẫn đến việc mạng load nhầm trọng số khổng lồ của phiên London sang phiên Asian.
✅ Hành động khắc phục:
1. Sửa triệt để mã nguồn setup, gắn cứng `CONFIG_ID` về đúng `CFG_LTC_ASIAN_V6`.
2. Khởi tạo Vòng 6 với cờ `--scratch` để chặn kế thừa rác, ép AI tự học lại từ đầu trên cấu trúc siêu nhỏ nhẹ của phiên Châu Á.
3. Tiến trình Vòng 6 (PID 10056) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
