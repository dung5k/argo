# NHIỆM VỤ ĐỊNH KỲ V2 (LOCAL): AUTO-TUNING LTC LONDON BRAIN (CỤC BỘ)

> **🇻🇳 NGUYÊN TẮC GIAO TIẾP BẮT BUỘC:** Toàn bộ phân tích, báo cáo, thông báo Telegram và phản hồi người dùng **PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT CÓ DẤU**. Không dùng tiếng Anh hay tiếng Việt không dấu trong bất kỳ output nào.

Hệ thống sẽ gọi bạn chạy lại prompt này định kỳ mỗi 10 phút một lần. Trách nhiệm của bạn là đóng vai trò một Kỹ sư AI tự động hóa để điều phối, đi tìm cấu hình và phương án tốt nhất cho bộ não `CFG_LTC_LONDON_V3_5` và **trực tiếp chạy huấn luyện (train) trên máy cục bộ này**.

Hãy thực thi nghiêm ngặt theo các bước sau trong mỗi lần được gọi:

---

## BƯỚC TIỀN XỬ LÝ: Đồng bộ kết quả mới nhất từ HuggingFace về máy cục bộ

**BẮT BUỘC chạy lệnh này đầu tiên**, trước khi làm bất cứ điều gì khác, để đảm bảo dữ liệu là mới nhất:
```
python scripts/sync_workspaces.py pull CFG_LTC_LONDON_V3_5
```

Sau đó mới tiếp tục các bước bên dưới.

---

## BƯỚC 1: Đánh giá Trạng thái Máy Cục Bộ (Local Status)

Kiểm tra xem máy có đang rảnh (IDLE) hay đang bận chạy huấn luyện (BUSY):
Sử dụng lệnh PowerShell sau để kiểm tra xem tiến trình `train_v3.py` có đang chạy hay không:
```powershell
Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%train_v3.py%'" | Select-Object ProcessId, CommandLine
```
Nếu có tiến trình đang chạy, máy ở trạng thái **BUSY**. Nếu không có, máy ở trạng thái **IDLE**.
Ghi nhận trạng thái.

---

## BƯỚC 2: Phân tích Lịch sử & Tư duy Tối ưu hóa (Quant/ML Expert)

Thay vì đoán mò ngẫu nhiên, bạn phải phân tích có hệ thống dựa trên lịch sử để tìm ra **hướng tối ưu (Gradient of Improvement)**.

1. **Thu thập Ngữ cảnh (Context Gathering):**
   - Đọc kết quả của lượt chạy mới nhất trong `workspaces/CFG_LTC_LONDON_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
   - Đọc thêm `tuning_notes.txt` của **3 run gần nhất** để biết lần trước đã thay đổi gì và kỳ vọng gì — tránh lặp lại thử nghiệm đã thất bại.
   - Nếu tồn tại file `workspaces/CFG_LTC_LONDON_V3_5/BEST_CONFIG.md`, đọc để lấy **mốc so sánh (Baseline)** tốt nhất hiện có.

2. **Phân tích Hiệu suất (Performance Analysis):**
   - So sánh `Composite Score`, `Win Rate`, `Val Loss` của lượt mới nhất với Baseline.
   - Đánh giá bias tín hiệu: Mô hình có đang **thiên lệch Buy/Sell** quá nhiều không? (Tỷ lệ Buy:Sell lý tưởng ≈ 45:55 đến 55:45)
   - Phát hiện **Overfitting**: Train loss giảm nhưng Val loss tăng?
   - Nếu `Composite Score` của run mới **cao hơn Baseline**, hãy cập nhật file `workspaces/CFG_LTC_LONDON_V3_5/BEST_CONFIG.md` với config và score mới.

3. **Đánh giá & Điều chỉnh Features (Feature Engineering):**
   - **Phiên London (Châu Âu):** LTC chịu ảnh hưởng bởi biến động thị trường Châu Âu mở cửa, tin tức kinh tế EU và tương quan với vàng (XAU), chứng khoán Châu Âu.
   - Các chỉ số hiện dùng: BTC, ETH, XAU... Tự đánh giá sự đóng góp của từng chỉ số.
   - *Chiến lược:* Nếu mô hình chững lại, thử **THÊM** features đo lường biến động (Volatility) như `bb_width`, `vroc`; **HOẶC LOẠI BỎ** features nghi ngờ gây nhiễu. Không giữ nguyên bộ features nếu điểm số không tăng sau 3 lượt liên tiếp.

4. **Ra quyết định Siêu tham số (Hyperparameter Strategy):**

   **🆕 KHO VŨ KHÍ V2 — ƯU TIÊN THỬ TRƯỚC khi lặp lại tham số cũ:**

   *Kiến trúc Neural Network (keys trong TRAINING):*
   | Tham số | Mặc định | Tùy chọn | Mô tả |
   |---|---|---|---|
   | `POOLING` | `"mean"` | `"attention"` | Learnable Attention Pooling |
   | `CLS_HEAD` | `"simple"` | `"residual"` | Residual MLP 3-layer Head |
   | `LAYER_DROP` | `0.0` | `0.1`–`0.3` | Stochastic Depth regularization |
   | `LR_SCHEDULER` | `"plateau"` | `"cosine_warm"` | Cosine Annealing Warm Restarts |

   *Feature Engineering (keys trong FEATURE_ENGINEERING):*
   | Tham số | Mặc định | Tùy chọn | Mô tả |
   |---|---|---|---|
   | `MTF_WINDOWS` | `[]` | `[5,15]`, `[15,60]` | Multi-Timeframe log_return & ATR |
   | `ORDER_FLOW` | `false` | `true` | Delta Volume + Cumulative Delta |
   | `VOL_REGIME` | `false` | `true` | One-hot High/Low volatility regime |

   *Macro Features (thêm vào từng symbol):*
   - `"spread_ret"` — Log return spread LTC vs macro asset
   - `"relative_strength"` — Relative Strength ratio rolling 60 nến

   *Siêu tham số cơ bản:*
   - `WINDOW_SIZE`: 15, 30, 60, 90, 120
   - `LEARNING_RATE`: 1e-5 đến 5e-5
   - `BATCH_SIZE`: 64, 128, 256
   - `D_MODEL` / `NUM_LAYERS`: 64/2, 128/3, 256/4

   - **🏆 Baseline hiện tại: ldn_16=0.4743 (WIN=30, BATCH=128, LR=3e-5)** — combo vàng đã xác nhận
   - **NGUYÊN TẮC A/B TESTING — BẮT BUỘC:** Mỗi lượt config mới, **CHỈ THAY ĐỔI TỐI ĐA 2 THAM SỐ** so với lượt trước để cô lập tác động.

5. **Early Stopping (Dừng Task) — Kích hoạt khi thoả MỘT TRONG HAI điều kiện sau:**

   **Điều kiện A — Không cải thiện sau nhiều lượt:**
   - Nếu đã thử thay đổi tuần tự nhưng `Composite Score` không vượt qua Baseline trong **25 lượt gần nhất**, hãy tắt task.

   **Điều kiện B — Đã cạn kiệt ý tưởng thử nghiệm:**
   - Nếu bạn đã lần lượt khai thác hết các hướng sau mà vẫn không cải thiện, hãy khai báo "hết ý tưởng" và dừng task:
     + Đã thử đủ các mức `LEARNING_RATE` (từ 1e-5 đến 5e-4)
     + Đã thử đủ `WINDOW_SIZE` ở nhiều mức (15, 30, 60, 90, 120)
     + Đã thử thay đổi `D_MODEL` / `NUM_LAYERS` (kiến trúc model)
     + Đã thử thêm và bớt nhiều bộ `MACRO_FEATURES` khác nhau
     + Đã thử điều chỉnh `TP_PCT` / `SL_PCT` (risk/reward ratio)
     + Đã thử `BATCH_SIZE` ở các mức khác nhau
     + **🆕 Đã thử đủ vũ khí V2:** `POOLING=attention`, `CLS_HEAD=residual`, `LAYER_DROP`, `LR_SCHEDULER=cosine_warm`, `MTF_WINDOWS`, `ORDER_FLOW`, `VOL_REGIME`, `spread_ret`, `relative_strength`
   - Khi khai báo hết ý tưởng, **BẮT BUỘC** ghi rõ trong báo cáo Telegram: danh sách tất cả những gì đã thử và lý do không còn hướng nào khả thi.

   **Hành động khi kích hoạt Early Stopping (cho cả hai điều kiện):**
   Sửa `.agent/tasks.json`, tìm id `ltc_london_auto_tuning_local` và đặt `"enabled": false`. Báo cáo Telegram đầy đủ và gọi `--done`.

---

## BƯỚC 3: Quản lý Hàng Đợi (Queue Management) & Chuẩn bị Data Trước

Mục tiêu: Đảm bảo có sẵn dữ liệu cho lượt chạy tiếp theo, nhưng KHÔNG ĐƯỢC CHUẨN BỊ THỪA.
Kiểm tra thư mục `workspaces/CFG_LTC_LONDON_V3_5/runs/`:
- Tìm các `<RUN_ID>` đã có thư mục `data/tensors/`, nhưng CHƯA CÓ file `results/training_metrics_v3.json` (tức là chưa chạy xong).
- Đối chiếu với kết quả Bước 1: Loại trừ `<RUN_ID>` mà máy cục bộ đang BUSY chạy.
- Còn lại chính là **HÀNG ĐỢI (Pending Runs)**.

**Xử lý:**
- **NGUYÊN TẮC: NẾU ĐÃ CÓ HÀNG ĐỢI (DÙ CHỈ CÒN 1 RUN), TUYỆT ĐỐI KHÔNG ĐƯỢC TẠO HAY CHUẨN BỊ THÊM RUN MỚI.**
- CHỈ KHI HÀNG ĐỢI HOÀN TOÀN RỖNG (0 runs), bạn MỚI CẦN TẠO 1 RUN MỚI:
  1. Sinh `<RUN_ID>` mới theo format `run_YYYYMMDD_HHMMSS_v3_ldn_X` (X là số thứ tự tiếp theo).
  2. Tạo thư mục `workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/` và copy `base_config.json` thành `config.json`. Áp dụng các quyết định từ **Bước 2.4** vào `config.json` mới. **BẮT BUỘC KHÔNG SỬA `base_config.json` GỐC!**
     - **LƯU Ý QUAN TRỌNG — BINANCE-ONLY:** Vì máy cục bộ KHÔNG thể chạy MT5 Exness headless, **BẮT BUỘC** loại bỏ các MACRO_FEATURES phụ thuộc MT5 (`DXYm`, `USTECm`, `XAUUSDm`). Chỉ dùng Binance crypto: `BTCUSDT`, `ETHUSDT`, `BCHUSDT`, `DOGEUSDT`, `XRPUSDT`, `SOLUSDT`.
     - Tạo thêm file **`tuning_notes.txt`** trong cùng thư mục run, viết đúng **3-5 câu** theo mẫu:
       ```
       Run: <RUN_ID>
       Thay đổi so với run trước: <tên tham số cũ → giá trị mới>
       Lý do: <tại sao nghĩ rằng thay đổi này sẽ cải thiện?>
       Kỳ vọng: <Composite Score tăng? Win Rate tăng? Bias giảm?>
       Baseline hiện tại: <Composite Score tốt nhất đang có>
       ```
  3. Chạy lệnh sau để **CHUẨN BỊ TENSOR** trước:
     ```
     python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json
     ```
  4. Commit và đẩy lên Git:
     ```
     git add . && git commit -m "auto-tuning LTC London local data ready: <RUN_ID>" && git push
     ```

---

## BƯỚC 4: Điều Phối Huấn Luyện Cục Bộ (Local Dispatching)

- **Nếu máy đang BUSY**:
  Thông báo Telegram: "`máy cục bộ` đang bận, đã chuẩn bị sẵn data cho `<RUN_ID>` vào hàng đợi" và gọi `--done` để kết thúc.
- **Nếu máy đang IDLE**:
  Lấy `<RUN_ID>` từ Hàng Đợi (hoặc vừa tạo xong ở Bước 3) và phát lệnh chạy huấn luyện:
  ```powershell
  python src/training_v3/train_v3.py --session london --file workspaces/CFG_LTC_LONDON_V3_5/runs/<RUN_ID>/config.json --scratch --run-id <RUN_ID>
  ```

Chỉ kết thúc và gọi `--done` sau khi:
1. Đã chuẩn bị xong data (nếu cần).
2. Phát lệnh huấn luyện (nếu máy IDLE).
3. Thông báo đầy đủ kết quả, giả thuyết và hành động lên Telegram.

### Điều chỉnh Lịch trình (Tuỳ chọn)
Nếu quá trình training mất nhiều thời gian, hãy tự sửa trường `nextRunTime` của task này trong file `.agent/tasks.json` thành `(timestamp_hiện_tại + N * 60) * 1000`.

---

## BƯỚC 5: Dọn dẹp ổ cứng (Storage Cleanup)

**BẮT BUỘC** chạy script dọn dẹp sau khi đã hoàn thành mọi thứ:
```
python scripts/cleanup_host_storage.py
```
Ghi nhận số GB rác đã dọn dẹp vào nội dung báo cáo Telegram cuối cùng.

---

> **LƯU Ý QUAN TRỌNG VỀ THÔNG BÁO TELEGRAM:**
> - Trong quá trình thực hiện, bạn có thể gọi lệnh này nhiều lần để cập nhật tiến độ:
>   `python .agent/send_to_tele.py "<Nội_dung_cập_nhật>"`
> - Khi đã hoàn tất toàn bộ tiến trình, **BẮT BUỘC** chạy lệnh cuối cùng với flag `--done`:
>   `python .agent/send_to_tele.py "<Kết_quả_cuối_cùng>" --done`


__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__
