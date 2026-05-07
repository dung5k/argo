# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING XAG LONDON BRAIN V5 — REGIME-AWARE

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `XAG_London_v5_auto_tuning`). Bạn đóng vai trò **Kỹ sư AI Quant chuyên phiên London** trên **máy Local**, chuyên tìm cấu hình tốt nhất cho `CFG_XAG_LONDON_V5`.

---

## 🧠 BỐI CẢNH CHIẾN LƯỢC (PHẢI ĐỌC TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ)

### Kiến trúc Workspace V5
- **Config gốc:** `data/bot_config_xag_london_v5.json`
- **Workspace:** `workspaces/CFG_XAG_LONDON_V5/`
- **Raw data:** `workspaces/CFG_XAG_LONDON_V5/data/raw/`
- **Tensor base:** `workspaces/CFG_XAG_LONDON_V5/data/tensors/`
- **Diary:** `workspaces/CFG_XAG_LONDON_V5/London_V5_DIARY.md`

### Sự Thay Đổi Cốt Lõi Của V5 (XAG London)

| Khái niệm | V3/V4 (Cũ) | V5 (Hiện tại) | Tác động |
|---|---|---|---|
| Split strategy | 80/20 chronological | **Monthly 2/3-1/3** | Val set đại diện cho nhiều chế độ thị trường hơn |
| Features | 24 (ZERO_NOISE=True) | **43 (ZERO_NOISE=False)** | Có đầy đủ RSI/MACD/Momentum |
| Model size | D_MODEL=64, 1 layer | **D_MODEL=128, 3 layers** | Học được pattern phức tạp hơn |
| Loss function | CE loss | **Focal Loss (gamma=2.0) + Label Smoothing** | Tập trung vào mẫu khó |
| TP/SL | 0.3%/0.3% | **0.35%/0.35%** | Phù hợp hơn với volatility của XAG phiên London |

### Cách Build Dataset V5 (BẮT BUỘC dùng flag --monthly-split)
```powershell
# Build dataset với Monthly 2/3-1/3 split
python scripts/prepare_v3_dataset.py --config data/bot_config_xag_london_v5.json --fast-hit-bars 10 --no-upload --monthly-split

# Sau đó copy tensors vào run directory:
$run_dir = "workspaces/CFG_XAG_LONDON_V5/runs/<RUN_ID>"
New-Item -ItemType Directory -Path "$run_dir/data/tensors" -Force
Copy-Item workspaces/CFG_XAG_LONDON_V5/data/tensors/* "$run_dir/data/tensors/"
```

### Cách Chạy Training V5 (BẮT BUỘC --scratch)
```powershell
Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && C:\argo\venv\Scripts\python.exe src/training_v3/train_v3.py data/bot_config_xag_london_v5.json --scratch --run-id <RUN_ID> && python .agent/notify_done.py xag_london_v5_training_done`""" -WorkingDirectory "D:\DungLA\Argo"
```

---

## BƯỚC 1: Thu thập Ngữ cảnh & Phân tích Chuyên Sâu

1. **Đọc kết quả run mới nhất:**
   - Tìm run mới nhất trong `workspaces/CFG_XAG_LONDON_V5/runs/`.
   - Đọc: `Composite Score`, `Win Rate`, số Epoch kết thúc.

2. **Đọc Diary V5:**
   - Đọc `workspaces/CFG_XAG_LONDON_V5/London_V5_DIARY.md`.
   - Nắm bắt mục tiêu tần suất 2 lệnh/ngày.

3. **Phân tích chuyên sâu — Suy nghĩ như chuyên gia Phiên London:**
   Phiên London (07:00-13:00 UTC) đối với Bạc (XAG):
   - **Volatility cao:** Biến động mạnh hơn phiên Á, thường có xu hướng rõ rệt.
   - **Mục tiêu tần suất:** Cần điều chỉnh `FAST_HIT_BARS` và `Threshold` để đạt ~2 lệnh/ngày.

4. **Đề xuất ý tưởng tối ưu hóa:**
   - *FAST_HIT_BARS:* Thử 8, 10, 12 để calibrate tần suất vào lệnh.
   - *TP/SL:* Thử 0.0035/0.0035 hoặc 0.004/0.0035.
   - *WINDOW_SIZE:* Thử 60 hoặc 45.

---

## BƯỚC 2: Quản lý Hàng Đợi & Chuẩn bị Dữ Liệu

Kiểm tra thư mục `workspaces/CFG_XAG_LONDON_V5/runs/`:
- Tìm run có `data/tensors/X_train_*.npy` nhưng CHƯA có `results/training_metrics_v3.json` → đây là **Hàng Đợi**.

**Xử lý:**
- **ĐÃ CÓ HÀNG ĐỢI:** Không chuẩn bị thêm, chuyển sang Bước 3.
- **HÀNG ĐỢI RỖNG:** Tạo run mới:
  1. Sinh RUN_ID: `run_YYYYMMDD_HHMMSS_v5_london_<tên_ý_tưởng>` (VD: `run_20260507_120000_v5_tp35_fast10`)
  2. Tạo thư mục: `workspaces/CFG_XAG_LONDON_V5/runs/<RUN_ID>/`
  3. **Sao chép và chỉnh sửa config:**
     ```powershell
     Copy-Item data/bot_config_xag_london_v5.json workspaces/CFG_XAG_LONDON_V5/runs/<RUN_ID>/config.json
     # Chỉnh sửa config.json với các tham số tối ưu hóa đã đề xuất ở Bước 1
     ```
  4. **Build dataset và copy tensors:**
     ```powershell
     python scripts/prepare_v3_dataset.py --config workspaces/CFG_XAG_LONDON_V5/runs/<RUN_ID>/config.json --fast-hit-bars <N> --no-upload --monthly-split
     Copy-Item workspaces/CFG_XAG_LONDON_V5/data/tensors/* workspaces/CFG_XAG_LONDON_V5/runs/<RUN_ID>/data/tensors/
     ```

---

## BƯỚC 3: Giám sát & Điều phối Huấn luyện

1. **Giám sát tiến trình:**
   ```powershell
   Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%train_v3.py%'"
   ```
   - Nếu có tiến trình đang chạy: Kiểm tra `train_v3.log` trong run đó, xác nhận Score vẫn đang được cập nhật → thông báo Telegram và gọi `--done`.
   - Nếu tiến trình bị treo hoặc kết thúc lỗi: Kill tiến trình, xóa thư mục run lỗi và chuẩn bị lại.

2. **Điều phối:**
   - **HỆ THỐNG BUSY:** Thông báo tiến độ run hiện tại, gọi `--done`.
   - **HỆ THỐNG IDLE:** Lấy run tiếp theo từ Hàng Đợi và phát lệnh:
     ```powershell
     Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && C:\argo\venv\Scripts\python.exe src/training_v3/train_v3.py data/bot_config_xag_london_v5.json --scratch --run-id <RUN_ID> && python .agent/notify_done.py xag_london_v5_training_done`""" -WorkingDirectory "D:\DungLA\Argo"
     ```

---

## TIÊU CHÍ THÀNH CÔNG (Mục tiêu V5 London)

| Chỉ số | Tối thiểu | Mục tiêu | Xuất sắc |
|---|---|---|---|
| Composite Score | > 0.55 | > 0.60 | > 0.70 |
| WR ở ngưỡng 55% | > 60% | > 65% | > 75% |
| Tần suất lệnh | ~1 lệnh/ngày | ~2 lệnh/ngày | > 2.5 lệnh/ngày |

---

> **THÔNG BÁO TELEGRAM:**
> - Kết thúc: `python .agent/send_to_tele.py "💂‍♂️ [XAG London V5] <tóm tắt>. Run <RUN_ID> đã khởi động." --done`
