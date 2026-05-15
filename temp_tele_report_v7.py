import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 7).
📊 Kết quả Vòng 6: THÀNH CÔNG RỰC RỠ! 
- Đạt Composite Score: 0.5188
- Win Rate: 63.04% (bứt phá mạnh mẽ từ 10% ở vòng cũ)
- Dừng sớm tại Epoch 67 (có dấu hiệu overfit nhẹ).

🚀 Triển khai Vòng 7:
1. Tăng Dropout lên 0.20 và giảm Learning Rate xuống 3e-5.
2. Mục tiêu: Chống overfitting, giúp mạng hội tụ sâu hơn, mượt hơn để phá vỡ mốc Win Rate 70%.
3. Tiến trình Vòng 7 (PID 6272) đã bắt đầu huấn luyện an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
