# NHIỆM VỤ ĐỊNH KỲ (LOCAL): AUTO-TUNING LTC ASIAN BRAIN V5 — REGIME-AWARE

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `ltc_asian_v5_auto_tuning`). Bạn đóng vai trò **Kỹ sư AI Quant chuyên phiên Châu Á** trên **máy Local**, chuyên tìm cấu hình tốt nhất cho `CFG_LTC_ASIAN_V5`.

---

## 🧠 BỐI CẢNH CHIẾN LƯỢC (PHẢI ĐỌC TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ)

### Kiến trúc Workspace V5
- **Config gốc:** `data/bot_config_ltc_asian_v5.json`
- **Workspace:** `workspaces/CFG_LTC_ASIAN_V5/`
- **Raw data:** `workspaces/CFG_LTC_ASIAN_V5/data/raw/`
- **Tensor base:** `workspaces/CFG_LTC_ASIAN_V5/data/tensors/`
- **Diary:** `workspaces/CFG_LTC_ASIAN_V5/ASIAN_V5_DIARY.md`

### Sự Thay Đổi Cốt Lõi Của V5 (Hiểu rõ để tránh làm sai)

| Khái niệm | V3/V4 (Cũ) | V5 (Hiện tại) | Tác động |
|---|---|---|---|
| Split strategy | 80/20 chronological | **Monthly 2/3-1/3** | Val set đại diện cho nhiều chế độ thị trường hơn |
| Features | 24 (ZERO_NOISE=True) | **43 (ZERO_NOISE=False)** | Có đầy đủ RSI/MACD/Momentum |
| Model size | D_MODEL=64, 1 layer | **D_MODEL=128, 3 layers** | Học được pattern phức tạp hơn |
| Loss function | CE loss | **Focal Loss (gamma=2.0) + Label Smoothing** | Tập trung vào mẫu khó |
| TP/SL | 0.3%/0.3% | **0.4%/0.3%** | Phù hợp hơn với volatility phiên Á hiện tại |

### Cách Build Dataset V5 (BẮT BUỘC dùng flag --monthly-split)
```powershell
# Build dataset với Monthly 2/3-1/3 split
python scripts/prepare_v3_dataset.py --config data/bot_config_ltc_asian_v5.json --fast-hit-bars 5 --no-upload --monthly-split

# Sau đó copy tensors vào run directory:
$run_dir = "workspaces/CFG_LTC_ASIAN_V5/runs/<RUN_ID>"
New-Item -ItemType Directory -Path "$run_dir/data/tensors" -Force
Copy-Item workspaces/CFG_LTC_ASIAN_V5/data/tensors/* "$run_dir/data/tensors/"
```

### Cách Chạy Training V5 (BẮT BUỘC --scratch)
```powershell
Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && C:\argo\venv\Scripts\python.exe src/training_v3/train_v3.py data/bot_config_ltc_asian_v5.json --scratch --run-id <RUN_ID> && python .agent/notify_done.py ltc_asian_v5_training_done`""" -WorkingDirectory "D:\DungLA\client1"
```
> ⚠️ Lưu ý: `train_v3.py` sẽ tự động phát hiện `X_train_*.npy` / `X_val_*.npy` và dùng Monthly Split thay vì 80/20.

---

## BƯỚC 1: Thu thập Ngữ cảnh & Phân tích Chuyên Sâu

1. **Đọc kết quả run mới nhất:**
   - Tìm run mới nhất trong `workspaces/CFG_LTC_ASIAN_V5/runs/` có file `results/training_metrics_v3.json`.
   - Đọc: `Composite Score`, `Win Rate kỷ lục`, số Epoch kết thúc (Early Stop hay chạy đủ).
   - Đọc 30 dòng cuối log: `results/train_v3.log` để xem xu hướng Score ở các epoch cuối.

2. **Đọc Diary V5:**
   - Đọc `workspaces/CFG_LTC_ASIAN_V5/ASIAN_V5_DIARY.md` (tạo mới nếu chưa có).
   - Nắm bắt: Những gì đã thử, Giả thuyết nào đã được kiểm chứng, những điểm yếu còn tồn tại.

3. **Phân tích chuyên sâu — Suy nghĩ như chuyên gia Phiên Á:**
   Phiên Á (00:00-07:00 UTC) có đặc điểm riêng biệt:
   - **Thanh khoản mỏng:** Giá di chuyển theo momentum yếu, dễ bị "quét stop".
   - **Volatility không đồng đều:** Khoảng 01:00-03:00 UTC có tin tức Nhật/Úc, còn lại rất flat.
   - **Xu hướng của thị trường hiện tại (Apr-May 2026):** Volatility giảm ~4x so với 2025, LTC đang trong vùng tích lũy.
   
   Câu hỏi phải trả lời:
   - Model đang nhận ra **loại setup nào** chủ yếu? (BUY hay SELL, ngưỡng xác suất bao nhiêu?)
   - Có bị **Buy Bias** như V4 không? (Buy/Sell ratio trong val set)
   - Ngưỡng **Threshold tối ưu** là bao nhiêu? (Nơi WR cao nhất với số lệnh đủ nhiều ≥ 80 lệnh)
   - **FAST_HIT_BARS** hiện tại (5 nến) có phù hợp không? Thị trường flat cần nhiều thời gian hơn để chạm TP.

4. **Đề xuất ý tưởng tối ưu hóa (ÍT NHẤT 1 ý tưởng mới):**
   
   **KHO VŨ KHÍ V5:**
   - *FAST_HIT_BARS:* Thử 3, 5, 8, 10 — ảnh hưởng trực tiếp đến số lượng setup "chất lượng cao" được chọn.
   - *TP/SL:* Thử 0.003/0.003, 0.004/0.003, 0.005/0.003, 0.005/0.004 — calibrate cho volatility thực tế.
   - *MACRO_FEATURES:* Thử bỏ XRP, BCH, DOGE (chỉ giữ BTC+ETH) để giảm nhiễu macro; hoặc thêm BTC_volume.
   - *WINDOW_SIZE:* Thử 45 hoặc 30 thay vì 60 — phiên Á flat cần lookback ngắn hơn.
   - *Architecture:* Thử `POOLING=attention` thay vì `mean` — có thể focus tốt hơn vào các nến quan trọng.
   - *LAYER_DROP:* Thử 0.15, 0.2, 0.25 — regularization mạnh hơn để tránh overfit trên data flat.
   - *LEARNING_RATE:* Thử 1e-4 (nhanh hơn) hoặc 2e-5 (ổn định hơn).
   
   **NGUYÊN TẮC VÀNG V5:** Thay đổi TỐI ĐA 2 tham số mỗi lần. Ưu tiên thay đổi `TP/SL` và `FAST_HIT_BARS` trước vì chúng ảnh hưởng trực tiếp đến **chất lượng nhãn** — cái gốc rễ của mọi vấn đề.

5. **Cập nhật Diary V5:**
   ```markdown
   ### [Thời gian] - Đánh giá Run: <RUN_ID>
   - **Kết quả:** Composite Score = X | WR = Y% | Early Stop Epoch = Z
   - **Vấn đề phát hiện:** <Buy/Sell Bias? Threshold quá cao? Volatility mismatch?>
   - **Ý tưởng mới:** <Tham số thay đổi + Lý do cụ thể>
   - **Giả thuyết:** <Kỳ vọng thay đổi này sẽ cải thiện điều gì, bao nhiêu%?>
   ```
   Sau khi cập nhật, push lên HF: `python scripts/sync_workspaces.py push CFG_LTC_ASIAN_V5`

---

## BƯỚC 2: Quản lý Hàng Đợi & Chuẩn bị Dữ Liệu

Kiểm tra thư mục `workspaces/CFG_LTC_ASIAN_V5/runs/`:
- Tìm run có `data/tensors/X_train_*.npy` nhưng CHƯA có `results/training_metrics_v3.json` → đây là **Hàng Đợi**.

**Xử lý:**
- **ĐÃ CÓ HÀNG ĐỢI:** Không chuẩn bị thêm, chuyển sang Bước 3.
- **HÀNG ĐỢI RỖNG:** Tạo run mới:
  1. Sinh RUN_ID: `run_YYYYMMDD_HHMMSS_v5_asian_<tên_ý_tưởng>` (VD: `run_20260507_010000_v5_tp04_fasthi8`)
  2. Tạo thư mục: `workspaces/CFG_LTC_ASIAN_V5/runs/<RUN_ID>/`
  3. **Sao chép và chỉnh sửa config:**
     ```powershell
     Copy-Item data/bot_config_ltc_asian_v5.json workspaces/CFG_LTC_ASIAN_V5/runs/<RUN_ID>/config.json
     # Sau đó chỉnh sửa config.json với tham số mới qua Python/json
     ```
  4. **Build dataset và copy tensors:**
     ```powershell
     python scripts/prepare_v3_dataset.py --config workspaces/CFG_LTC_ASIAN_V5/runs/<RUN_ID>/config.json --fast-hit-bars <N> --no-upload --monthly-split
     Copy-Item workspaces/CFG_LTC_ASIAN_V5/data/tensors/* workspaces/CFG_LTC_ASIAN_V5/runs/<RUN_ID>/data/tensors/
     ```

---

## BƯỚC 3: Giám sát & Điều phối Huấn luyện

1. **Giám sát tiến trình:**
   ```powershell
   Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%train_v3.py%'"
   ```
   - Nếu có tiến trình đang chạy: Kiểm tra log, xác nhận vẫn đang update → thông báo Telegram và gọi `--done`.
   - Nếu tiến trình bị treo (log không update > 15 phút): Kill, điều tra lỗi, xóa run lỗi, tiếp tục.

2. **Điều phối:**
   - **BUSY:** Thông báo Telegram tóm tắt ý tưởng mới, gọi `--done`.
   - **IDLE:** Lấy run từ Hàng Đợi và phát lệnh:
     ```powershell
     Start-Process cmd.exe -ArgumentList "/c `"set PYTHONIOENCODING=utf8 && chcp 65001 && C:\argo\venv\Scripts\python.exe src/training_v3/train_v3.py data/bot_config_ltc_asian_v5.json --scratch --run-id <RUN_ID> && python .agent/notify_done.py ltc_asian_v5_training_done`""" -WorkingDirectory "D:\DungLA\client1"
     ```

---

## TIÊU CHÍ THÀNH CÔNG (Mục tiêu V5)

| Chỉ số | Tối thiểu | Mục tiêu | Xuất sắc |
|---|---|---|---|
| Composite Score | > 0.55 | > 0.65 | > 0.75 |
| WR ở ngưỡng 55% | > 60% | > 70% | > 80% |
| Số lệnh/tháng | ≥ 80 | ≥ 150 | ≥ 300 |
| Buy/Sell ratio | 30:70 ~ 70:30 | 40:60 ~ 60:40 | 45:55 ~ 55:45 |
| Early Stop | > Epoch 30 | > Epoch 50 | > Epoch 80 |

---

> **THÔNG BÁO TELEGRAM:**
> - Báo cáo thường xuyên: `python .agent/send_to_tele.py "<Nội_dung>"`
> - **LƯU Ý:** Trong mỗi báo cáo Telegram (đặc biệt là báo cáo kết thúc), **BẮT BUỘC** đính kèm thông tin về **Thành tích tốt nhất (Best Score/WR)** đạt được từ trước đến nay để tiện so sánh.
> - Kết thúc: `python .agent/send_to_tele.py "🏯 [Asian V5] <tóm tắt ý tưởng>. Run <RUN_ID> đã khởi động. (Best so far: Score X, WR Y%)" --done`

__(Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi hoàn tất BẮT BUỘC chạy với cờ --done!)__

__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__
