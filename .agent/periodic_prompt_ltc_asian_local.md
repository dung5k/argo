# NHIỆM VỤ ĐỊNH KỲ V2 (LOCAL): AUTO-TUNING LTC ASIAN BRAIN (CỤC BỘ)

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống gọi bạn định kỳ mỗi 10 phút. Bạn đóng vai trò **Kỹ sư AI Quant cao cấp** để tìm cấu hình tốt nhất cho `CFG_LTC_ASIAN_V3_5` và **trực tiếp chạy huấn luyện trên máy cục bộ này**.

---

## BƯỚC TIỀN XỬ LÝ: Đồng bộ từ HuggingFace

```
python scripts/sync_workspaces.py pull CFG_LTC_ASIAN_V3_5
```

---

## BƯỚC 0: TRINH SÁT (Thu thập dữ liệu)

1. **Đọc kết quả London tốt nhất** (mốc tham chiếu):
   - `workspaces/CFG_LTC_LONDON_V3_5/runs/<BEST_RUN>/results/training_metrics_v3.json`
   - Ghi nhận: `SCORE_LDN` (hiện tại: ldn_16 = 0.4743)

2. **Đọc kết quả Asian hiện tại:**
   - Quét `workspaces/CFG_LTC_ASIAN_V3_5/runs/*/results/training_metrics_v3.json`
   - Ghi nhận `SCORE_ASIAN`, `WIN_RATE`, `TOTAL_SIGNALS`, `VAL_LOSS`
   - Đọc `BEST_CONFIG.md` nếu có.
   - **Top 2 hiện tại:** `asian_12` (0.5087, Ep4) > `asian_17` (0.4163, Ep8)

3. **Tính GAP:** `GAP = SCORE_LDN - SCORE_ASIAN`. Mục tiêu: thu hẹp GAP mỗi lượt.

4. **Kiểm tra config.json của run gần nhất** — xác nhận các vũ khí V2 đã bật/tắt:
   `POOLING? CLS_HEAD? LAYER_DROP? LR_SCHEDULER? MTF_WINDOWS? ORDER_FLOW? VOL_REGIME? spread_ret? relative_strength?`

---

## BƯỚC 1: ĐÁNH GIÁ TRẠNG THÁI MÁY

```powershell
Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%train_v3.py%'" | Select-Object ProcessId, CommandLine
```
- Có tiến trình → **BUSY** (chỉ chuẩn bị data, không dispatch)
- Không có → **IDLE** (dispatch ngay)

---

## BƯỚC 2: RA QUYẾT ĐỊNH CHIẾN THUẬT (Vai trò Chuyên gia Quant/ML)

Dựa trên phân tích Bước 0, chọn **1-2 biến** từ **kho vũ khí V2** để thử nghiệm:

### Kiến trúc Neural Network (keys trong TRAINING):
| Tham số | Mặc định | Tùy chọn | Mô tả |
|---|---|---|---|
| `POOLING` | `"mean"` | `"attention"` | Learnable Attention Pooling |
| `CLS_HEAD` | `"simple"` | `"residual"` | Residual MLP 3-layer Head |
| `LAYER_DROP` | `0.0` | `0.1`–`0.3` | Stochastic Depth regularization |
| `LR_SCHEDULER` | `"plateau"` | `"cosine_warm"` | Cosine Annealing Warm Restarts |

### Feature Engineering (keys trong FEATURE_ENGINEERING):
| Tham số | Mặc định | Tùy chọn | Mô tả |
|---|---|---|---|
| `MTF_WINDOWS` | `[]` | `[5,15]`, `[15,60]` | Multi-Timeframe log_return & ATR |
| `ORDER_FLOW` | `false` | `true` | Delta Volume + Cumulative Delta |
| `VOL_REGIME` | `false` | `true` | One-hot High/Low volatility regime |

### Macro Features (thêm vào từng symbol trong MACRO_FEATURES):
- `"spread_ret"` — Log return spread giữa LTC và macro asset
- `"relative_strength"` — Relative Strength ratio rolling 60 nến

### Siêu tham số cơ bản (A/B Testing truyền thống):
- `WINDOW_SIZE`: 30, 60, 90
- `LEARNING_RATE`: 1e-5 đến 5e-5
- `BATCH_SIZE`: 64, 128, 256
- `D_MODEL` / `NUM_LAYERS`: 64/2, 128/3, 256/4

**NGUYÊN TẮC BẮT BUỘC: CHỈ THAY ĐỔI TỐI ĐA 2 THAM SỐ mỗi lượt!**

---

## BƯỚC 3: QUẢN LÝ HÀNG ĐỢI & CHUẨN BỊ DATA

Kiểm tra `workspaces/CFG_LTC_ASIAN_V3_5/runs/`:
- Tìm runs có `data/tensors/` nhưng CHƯA có `results/training_metrics_v3.json` → **HÀNG ĐỢI**
- **NẾU ĐÃ CÓ HÀNG ĐỢI → KHÔNG TẠO THÊM RUN MỚI**
- CHỈ khi hàng đợi rỗng, tạo run mới:

1. Sinh `<RUN_ID>`: `run_YYYYMMDD_HHMMSS_v3_asian_X`
2. Copy `base_config.json` → `config.json`, áp dụng quyết định Bước 2
   - **BINANCE-ONLY:** Chỉ dùng `BTCUSDT`, `ETHUSDT`, `BCHUSDT`, `DOGEUSDT`, `XRPUSDT`, `SOLUSDT` (không MT5)
3. Tạo `tuning_notes.txt`:
   ```
   Run: <RUN_ID>
   Thay đổi: [1-2 tham số đã đổi]
   Lý do: [phân tích dựa trên Bước 0]
   Kỳ vọng: [dự đoán kết quả cụ thể]
   Nguồn cảm hứng: [run tốt nhất hiện tại và config của nó]
   Baseline: asian_12=0.5087 (Ep4)
   ```
4. Chuẩn bị tensor:
   ```
   python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json
   ```
5. Commit & push:
   ```
   git add . && git commit -m "auto-tuning LTC Asian V2 data ready: <RUN_ID>" && git push
   ```

---

## BƯỚC 4: ĐIỀU PHỐI HUẤN LUYỆN

- **Nếu BUSY:** Báo Telegram và gọi `--done`
- **Nếu IDLE:** Lấy RUN_ID từ hàng đợi và chạy:
  ```powershell
  python src/training_v3/train_v3.py --session asian --file workspaces/CFG_LTC_ASIAN_V3_5/runs/<RUN_ID>/config.json --scratch --run-id <RUN_ID>
  ```

---

## BƯỚC 5: ĐÁNH GIÁ SAU TRAINING

Sau khi training xong:
1. So sánh Score mới với `asian_12` (0.5087) và `SCORE_LDN` (0.4743)
2. **Score TĂNG** → tiếp tục hướng, đẩy thêm tham số cùng chiều
3. **Score GIẢM** → quay lui, thử hướng ngược lại
4. Nếu Score mới > Baseline → cập nhật `BEST_CONFIG.md`

---

## BƯỚC 6: EARLY STOPPING

Tắt task (`"enabled": false` trong `.agent/tasks.json`, id `ltc_asian_auto_tuning_local`) NẾU:
1. Composite Score >= 0.55 (mục tiêu phiên Asian LTC)
2. Đã thử 5+ trục tối ưu V2 khác nhau mà không vượt qua mốc cao nhất sau 20 lượt

---

## BƯỚC 7: DỌN DẸP & BÁO CÁO

```
python scripts/cleanup_host_storage.py
python .agent/send_to_tele.py "<Báo cáo: Score, GAP với LDN, vũ khí đã dùng, hướng tiếp theo>" --done
```

__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần: python .agent/send_to_tele.py "<Nội_dung>". Khi hoàn tất: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done)__
