import subprocess

msg = """🏯 [ASIAN V6 MTF] Ổn định.
- Hàng đợi hiện tại: Đang xử lý Run `run_20260513_224229_v6_ASIAN_1m_W20_STF_MaxHold60`.
- Tình trạng: Tiến trình đang thực thi an toàn trong giai đoạn Warm-up Autoencoder.
- Hành động: Giữ nguyên trạng thái (Ổn định) chờ Run hoàn tất để phân tích metrics."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
