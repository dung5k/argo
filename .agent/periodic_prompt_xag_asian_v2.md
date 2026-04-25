# NHIỆM VỤ CHIẾN THUẬT V2: AUTO-TUNING XAG ASIAN BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `xag_asian_v2_tuning`). Bạn đóng vai trò **Kỹ sư AI Quant cao cấp** trên máy cục bộ để phục hồi hiệu suất bộ não `CFG_XAG_ASIAN_V3_5` — phiên XAG KÉMM NHẤT hiện tại.

## BƯỚC 0: TRINH SÁT (Thu thập dữ liệu)

1. **Đọc score phiên London (tốt nhất):**
   - `workspaces/CFG_XAG_LDN_V3_5/runs/<BEST_RUN>/results/training_metrics_v3.json`
   - Ghi nhận: `SCORE_LDN`.

2. **Đọc kết quả Asian run gần nhất:**
   - Quét `workspaces/CFG_XAG_ASIAN_V3_5/runs/*/results/training_metrics_v3.json`
   - Ghi nhận: `SCORE_ASIAN`, `WIN_RATE`, `TOTAL_SIGNALS`, `VAL_LOSS`.

3. **Tính GAP:** `GAP = SCORE_LDN - SCORE_ASIAN`. Mục tiêu: thu hẹp GAP mỗi lượt.

4. **Kiểm tra config.json của run gần nhất** — xác định vũ khí mới nào đã bật:
   POOLING? CLS_HEAD? LAYER_DROP? LR_SCHEDULER? MTF_WINDOWS? ORDER_FLOW? VOL_REGIME? spread_ret? relative_strength?

## BƯỚC 1: RA QUYẾT ĐỊNH (Vai trò Chuyên gia)

Bạn là **chuyên gia Quant/ML**. Dựa trên dữ liệu Bước 0, hãy tự phân tích nguyên nhân Asian kém và quyết định hướng tối ưu. Nguyên tắc duy nhất: **mỗi lượt chỉ thay đổi 1-2 biến** để đo lường tác động.

Base config đã có sẵn tham số cơ bản từ London. Dưới đây là **kho vũ khí mới** bạn có thể sử dụng:

### Kiến trúc Neural Network (keys trong TRAINING):
- `"POOLING"`: `"mean"` (mặc định) hoặc `"attention"` — Learnable Attention Pooling
- `"CLS_HEAD"`: `"simple"` (mặc định) hoặc `"residual"` — Residual MLP 3-layer Head
- `"LAYER_DROP"`: `0.0` (tắt) đến `0.3` — Stochastic Depth / LayerDrop
- `"LR_SCHEDULER"`: `"plateau"` (mặc định) hoặc `"cosine_warm"` — Cosine Annealing w/ Warm Restarts

### Feature Engineering (keys trong FEATURE_ENGINEERING):
- `"MTF_WINDOWS"`: `[]` (tắt) hoặc `[5, 15]`, `[15, 60]`... — Multi-Timeframe log_return & ATR
- `"ORDER_FLOW"`: `true/false` — Delta Volume + Cumulative Delta proxy
- `"VOL_REGIME"`: `true/false` — One-hot High/Low volatility regime

### Macro Features (thêm vào từng symbol trong MACRO_FEATURES):
- `"spread_ret"` — Log return spread giữa XAG và macro asset
- `"relative_strength"` — Relative Strength ratio rolling 60 nến


## BƯỚC 2: TẠO CONFIG MỚI (Nguyên tắc A/B Testing)

1. Kiểm tra `workspaces/CFG_XAG_ASIAN_V3_5/runs/`. Tìm Pending Runs (chưa có `training_metrics_v3.json`).
2. Nếu hàng đợi rỗng:
   - Tạo `<RUN_ID>` mới: `run_YYYYMMDD_HHMMSS_v3_asian_X`
   - Copy `base_config.json` thành `config.json` trong thư mục run mới.
   - Áp dụng quyết định từ Bước 1. **CHỈ THAY ĐỔI 1-2 BIẾN SO VỚI LƯỢT TRƯỚC!**
   - **BẮT BUỘC:** Tạo file `tuning_notes.txt` trong run directory:
     ```
     Thay đổi: [liệt kê 1-2 tham số đổi]
     Lý do: [tại sao chọn hướng này dựa trên phân tích Bước 0]
     Kỳ vọng: [dự đoán kết quả]
     Nguồn cảm hứng: [LDN run X đạt score Y với config Z]
     ```

3. Chạy chuẩn bị dữ liệu:
```
python scripts/crawl_crypto_v3.py workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json
python scripts/upload_v3_dataset.py --config workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json
```

4. Commit Git: `auto-tuning XAG Asian V2 data ready: <RUN_ID>`

## BƯỚC 3: TRAINING CỤC BỘ

```
python src/training_v3/train_v3.py workspaces/CFG_XAG_ASIAN_V3_5/runs/<RUN_ID>/config.json --session asian --scratch --run-id <RUN_ID>; python .agent/notify_done.py xag_asian_training_done
```

## BƯỚC 4: ĐÁNH GIÁ KẾT QUẢ & TỰ ĐIỀU CHỈNH

Sau khi training xong:
1. Đọc `training_metrics_v3.json` → so sánh Composite Score với:
   - Best Asian run trước đó
   - Best LDN run (mục tiêu: rút ngắn khoảng cách)
2. Nếu score **TĂNG**: tiếp tục hướng đi, đẩy thêm tham số cùng chiều.
3. Nếu score **GIẢM**: quay lui, thử hướng ngược lại hoặc trục tối ưu khác.

## BƯỚC 5: EARLY STOPPING

Tắt task (`"enabled": false` trong `.agent/tasks.json`, id `xag_asian_v2_tuning`) NẾU:
1. Composite Score đạt >= 0.60 (ngang NY).
2. Đã thử 5+ trục tối ưu khác nhau mà không vượt qua mốc cao nhất sau 20 lượt.

## BƯỚC 6: BÁO CÁO

```
python .agent/send_to_tele.py "<Báo cáo chi tiết: Score, so sánh LDN/NY, hướng đi tiếp theo>" --done
```
