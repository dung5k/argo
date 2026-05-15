# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING XAG NEW YORK BRAIN V5 — REGIME-AWARE

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `XAG_ny_v5_auto_tuning`). Bạn đóng vai trò **Kỹ sư AI Quant chuyên phiên New York** trên **máy Local**, chuyên tìm cấu hình tốt nhất cho `CFG_XAG_NY_V5`.

---

## 🧠 BỐI CẢNH CHIẾN LƯỢC (PHẢI ĐỌC TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ)

### Kiến trúc Workspace V5
- **Config gốc:** `data/bot_config_xag_ny_v5.json`
- **Workspace:** `workspaces/CFG_XAG_NY_V5/`
- **Raw data:** `workspaces/CFG_XAG_NY_V5/data/raw/`
- **Tensor base:** `workspaces/CFG_XAG_NY_V5/data/tensors/`
- **Diary:** `workspaces/CFG_XAG_NY_V5/NY_V5_DIARY.md`

---

## 🏆 BẢNG VÀNG THÀNH TÍCH V5 (QUY TẮC: TOP 3 HOẶC WR >= 80%)

| Run ID | Win Rate | Score | Đặc điểm |
|---|---|---|---|
| `run_20260511_131500_v5_ny_balanced_elite` | **66.7%** | **0.619** | Balanced Elite (Gamma 5.0, FHB 3) |
| `run_20260510_140500` | 88.6% | 0.8595 | Stable Sniper (NEW WORLD RECORD) |
| `run_20260508_133000` | **91.9%** | 0.734 | D=128, NH=8, FHB=5 |
| `run_20260508_200000` | **88.0%** | 0.750 | Anti-Overfit (Gamma 3, LS 0.2), 29 feat |
| `run_20260507_253000` | **86.7%** | 0.725 | Macro RSI/Mom, JPY anchor |
| `run_20260508_083000` | **84.8%** | 0.735 | Nitro Overdrive, WD 0.05 |
| `run_20260507_264500` | **82.5%** | **0.760** | Nitro Impulse FHB=5 |
| `run_20260508_073000` | **81.2%** | 0.734 | Nitro Overdrive (LR 2e-5) |
| `run_20260507_243000` | **80.0%** | 0.712 | Macro Plus (JPY anchor) |
| `run_20260508_210000` | 75.0% | 0.750 | Sniper TP6/SL3 |
| `run_20260508_203000` | 77.4% | 0.692 | Stability Anti-Overfit |
| `run_20260508_223000` | 65.1% | 0.632 | Sniper Stable FHB=8 |

> *Ghi chú: Đã đạt ngưỡng Sniper >= 80%, ưu tiên lưu trữ toàn bộ thành tích trên 80%.*

### Sự Thay Đổi Cốt Lõi Của V5 (Hiểu rõ để tránh làm sai)

| Khái niệm | V3/V4 (Cũ) | V5 (Hiện tại) | Tác động |
|---|---|---|---|
| Split strategy | 80/20 chronological | **Monthly 2/3-1/3** | Val set đại diện cho nhiều chế độ thị trường hơn |
| Features | 24 (ZERO_NOISE=True) | **43 (ZERO_NOISE=False)** | Có đầy đủ RSI/MACD/Momentum |
| Model size | D_MODEL=64, 1 layer | **D_MODEL=128, 3 layers** | Học được pattern phức tạp hơn |
| Loss function | CE loss | **Focal Loss (gamma=2.0) + Label Smoothing** | Tập trung vào mẫu khó |
| TP/SL | 0.3%/0.3% | **0.6%/0.4%** | Phù hợp hơn với chiến thuật lướt sóng nhanh (bắt chước LTC) |

### Cách Build Dataset V5 (BẮT BUỘC dùng flag --monthly-split)
```powershell
# Build dataset với Monthly 2/3-1/3 split
python scripts/prepare_v3_dataset.py --config data/bot_config_xag_ny_v5.json --fast-hit-bars 8 --no-upload --monthly-split

# Sau đó copy tensors vào run directory:
$run_dir = "workspaces/CFG_XAG_NY_V5/runs/<RUN_ID>"
New-Item -ItemType Directory -Path "$run_dir/data/tensors" -Force
Copy-Item workspaces/CFG_XAG_NY_V5/data/tensors/* "$run_dir/data/tensors/"
```

### Cách Chạy Training V5 (BẮT BUỘC --scratch)
```powershell
Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && C:\argo\venv\Scripts\python.exe src/training_v3/train_v3.py data/bot_config_xag_ny_v5.json --scratch --run-id <RUN_ID> && python .agent/notify_done.py xag_ny_v5_training_done`""" -WorkingDirectory "D:\DungLA\Argo"
```
> ⚠️ Lưu ý: `train_v3.py` sẽ tự động phát hiện `X_train_*.npy` / `X_val_*.npy` và dùng Monthly Split thay vì 80/20.

---

## BƯỚC 1: Thu thập Ngữ cảnh & Phân tích Chuyên Sâu

1. **Đọc kết quả run mới nhất:**
   - Tìm run mới nhất trong `workspaces/CFG_XAG_NY_V5/runs/` có file `results/training_metrics_v3.json`.
   - Đọc: `Composite Score`, `Win Rate kỷ lục`, số Epoch kết thúc.
   - Đọc 30 dòng cuối log: `results/train_v3.log` để xem xu hướng Score ở các epoch cuối.

2. **Đọc Diary V5:**
   - Đọc `workspaces/CFG_XAG_NY_V5/NY_V5_DIARY.md` (tạo mới nếu chưa có).
   - Nắm bắt: Những gì đã thử, Giả thuyết nào đã được kiểm chứng, những điểm yếu còn tồn tại.

3. **Phân tích chuyên sâu — Suy nghĩ như chuyên gia Phiên New York:**
   Phiên New York (13:00-19:00 UTC) có đặc điểm:
   - **Volatility cực cao:** Đặc biệt lúc mở cửa và khi có tin tức Mỹ (CPI, FOMC, NFP).
   - **Đảo chiều (Reversals):** Thường có các đợt quét thanh khoản (Liquidity sweeps) trước khi đi theo xu hướng thật.
   
   Câu hỏi phải trả lời:
   - Model đang nhận ra **loại setup nào** chủ yếu? (BUY hay SELL, ngưỡng xác suất bao nhiêu?)
   - Có bị **Buy Bias** không? (Kiểm tra tỷ lệ Buy/Sell trong Val set)
   - Ngưỡng **Threshold tối ưu** là bao nhiêu? (Nơi WR cao nhất với số lệnh ≥ 80 lệnh)
   - **FAST_HIT_BARS** hiện tại (10 nến) có phù hợp với tốc độ của New York không?

4. **Đề xuất ý tưởng tối ưu hóa (ÍT NHẤT 1 ý tưởng mới):**
   
   **KHO VŨ KHÍ V5 (PHONG CÁCH ĐÁNH NHANH NHƯ LTC):**
   - *FAST_HIT_BARS:* Thử 3, 5, 8 — New York nhanh nên cần bộ lọc thời gian ngắn để bắt sóng gắt.
   - *TP/SL:* Thử 0.005/0.004, 0.006/0.004, 0.007/0.005.
   - *MACRO_FEATURES:* BẮT BUỘC chỉ dùng XAUUSDm làm mỏ neo, LOẠI BỎ hoàn toàn USDJPYm và DXYm để giảm nhiễu (Spikes).
   - *REGULARIZATION:* BẮT BUỘC dùng LABEL_SMOOTHING >= 0.15 và FOCAL_GAMMA >= 2.5. Tuyệt đối không dùng Hard Label (0.0).
   - *D_MODEL:* Thử giảm dung lượng não xuống 64 hoặc 96.
   
   - **Baseline mới:** Chỉ cần Score > 0.60 và WR > 65% (trong điều kiện có Label Smoothing) là được coi là thành công và được phép ghi nhận kỷ lục mới để Deploy!
   - Không được ép AI chạy theo WR > 80% nữa, điều đó chỉ tạo ra những mô hình tự tin mù quáng vào bẫy giá!

   **QUY TẮC LƯU TRỮ THÀNH TÍCH (DIARY):**
   - Luôn duy trì **Top 3 thành tích tốt nhất** (Best Score/WR) trong Diary để so sánh.
   - **ĐẶC BIỆT:** Nếu đạt được các thành tích có **Win Rate >= 80%**, BẮT BUỘC phải lưu lại TOÀN BỘ các thành tích này (không bị giới hạn bởi con số 3) để phục vụ phân tích Sniper.

5. **Cập nhật Diary V5:**
   ```markdown
   ### [Thời gian] - Đánh giá Run: <RUN_ID>
   - **Kết quả:** Composite Score = X | WR = Y% | Early Stop Epoch = Z
   - **Vấn đề phát hiện:** <Phân tích bias, threshold, volatility>
   - **Ý tưởng mới:** <Tham số thay đổi + Lý do cụ thể>
   - **Giả thuyết:** <Kỳ vọng thay đổi này sẽ cải thiện điều gì?>
   ```
   Sau khi cập nhật, thực hiện:
   - Push nhật ký lên HF: `python scripts/sync_workspaces.py push CFG_XAG_NY_V5`
   - **QUY TRÌNH TRIỂN KHAI TỰ ĐỘNG (Nếu có Đỉnh mới):**
     Nếu kết quả run hiện tại đạt **Best Score mới** (vượt kỷ lục trong Diary):
     1. Thực hiện push toàn bộ workspace lên HF: `python scripts/sync_workspaces.py push CFG_XAG_NY_V5`
     2. Phát lệnh MQTT thông báo cho Argo1:
        `python .agent/send_mqtt.py "Hệ thống XAG NY V5 vừa đạt kỷ lục mới (Score: <Score_mới>). Yêu cầu Argo1 thực hiện: 1. Pull code/config mới nhất từ HF. 2. Cập nhật cấu hình cho XAG Bot ngay lập tức." --target Argo1`
     3. Ghi nhận việc deploy vào báo cáo Telegram.

---

## BƯỚC 2: Quản lý Hàng Đợi & Chuẩn bị Dữ Liệu

Kiểm tra thư mục `workspaces/CFG_XAG_NY_V5/runs/`:
- Tìm run có `data/tensors/X_train_*.npy` nhưng CHƯA có `results/training_metrics_v3.json` → đây là **Hàng Đợi**.

**Xử lý:**
- **ĐÃ CÓ HÀNG ĐỢI:** Không chuẩn bị thêm, chuyển sang Bước 3.
- **HÀNG ĐỢI RỖNG:** Tạo run mới:
  1. Sinh RUN_ID: `run_YYYYMMDD_HHMMSS_v5_ny_<ý_tưởng>`
  2. Tạo thư mục: `workspaces/CFG_XAG_NY_V5/runs/<RUN_ID>/`
  3. **Sao chép và chỉnh sửa config:**
     ```powershell
     Copy-Item data/bot_config_xag_ny_v5.json workspaces/CFG_XAG_NY_V5/runs/<RUN_ID>/config.json
     ```
  4. **Build dataset và copy tensors:**
     ```powershell
     python scripts/prepare_v3_dataset.py --config workspaces/CFG_XAG_NY_V5/runs/<RUN_ID>/config.json --fast-hit-bars <N> --no-upload --monthly-split
     Copy-Item workspaces/CFG_XAG_NY_V5/data/tensors/* workspaces/CFG_XAG_NY_V5/runs/<RUN_ID>/data/tensors/
     ```

---

## BƯỚC 3: Giám sát & Điều phối Huấn luyện

1. **Giám sát tiến trình:**
   ```powershell
   Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%train_v3.py%'"
   ```
   - Nếu có tiến trình đang chạy: Kiểm tra `train_v3.log`, xác nhận vẫn đang update → thông báo Telegram và gọi `--done`.
   - Nếu bị treo (> 15p không update): Kill và dọn dẹp.

2. **Điều phối:**
   - **BUSY:** Thông báo tiến độ, gọi `--done`.
   - **IDLE:** Lấy run từ Hàng Đợi và phát lệnh:
     ```powershell
     Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && C:\argo\venv\Scripts\python.exe src/training_v3/train_v3.py data/bot_config_xag_ny_v5.json --scratch --run-id <RUN_ID> && python .agent/notify_done.py xag_ny_v5_training_done`""" -WorkingDirectory "D:\DungLA\Argo"
     ```

---

## TIÊU CHÍ THÀNH CÔNG (Mục tiêu V5 New York)

| Chỉ số | Tối thiểu | Mục tiêu | Xuất sắc |
|---|---|---|---|
| Composite Score | > 0.50 | > 0.60 | > 0.70 |
| WR ở ngưỡng 55% | > 58% | > 65% | > 75% |
| Số lệnh/tháng | ≥ 100 | ≥ 200 | ≥ 400 |
| Buy/Sell ratio | 30:70 ~ 70:30 | 40:60 ~ 60:40 | 45:55 ~ 55:45 |
| Early Stop | > Epoch 30 | > Epoch 50 | > Epoch 80 |

---

> **THÔNG BÁO TELEGRAM:**
> - Báo cáo thường xuyên: `python .agent/send_to_tele.py "<Nội_dung>" --channel 1816854047`
> - **LƯU Ý:** Trong mỗi báo cáo Telegram (đặc biệt là báo cáo kết thúc), **BẮT BUỘC** đính kèm thông tin về **Thành tích tốt nhất (Best Score/WR)** đạt được từ trước đến nay để tiện so sánh.
> - Kết thúc: `python .agent/send_to_tele.py "🇺🇸 [New York V5] <tóm tắt ý tưởng>. Run <RUN_ID> đã khởi động. (Best so far: Score X, WR Y%)" --channel 1816854047 --done`

__(Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>" --channel 1816854047. Khi hoàn tất BẮT BUỘC chạy với cờ --done!)__
