# Kế hoạch Thiết kế Chiến thuật XAG London (Dựa trên Thánh Giá NY)

Tiến trình Auto-tuning của XAG phiên New York đã chứng minh rằng một kiến trúc đơn giản (D_MODEL=16), kết hợp với dữ liệu Vĩ mô tinh khiết (XAU, DXY) và tỷ lệ Risk:Reward 1:1 là **Điểm Tối Ưu Toàn Cục (Global Optimum)**. 

Thay vì bắt đầu lại từ đầu với cấu hình rườm rà hiện tại của phiên London (`D_MODEL=32`, `NUM_LAYERS=2`, các chỉ báo phức tạp như `chop_14`, `bb_zscore`), chúng ta sẽ **kế thừa toàn bộ triết lý thiết kế** từ chiến thắng của phiên NY và áp dụng (sửa đổi biên độ) cho phiên London.

## Các Thay đổi đã triển khai (Cập nhật `base_config.json` của LDN)

### 1. Kiến trúc Bộ não (Neural Architecture)
- **Giảm `D_MODEL` từ 32 xuống 16**.
- **Giảm `NUM_LAYERS` từ 2 xuống 1**.
- Giữ nguyên `BATCH_SIZE=512` và `LEARNING_RATE=1e-05` (Bức tường chống nhiễu tuyệt đối).
- **Lý do:** London có ít tin tức giật gân hơn NY, dữ liệu "hiền" hơn. Nếu não D32 bị overfit ở NY, nó chắc chắn sẽ overfit ở London. D16 là dung lượng hoàn hảo để học tương quan Vĩ mô.

### 2. Cấu trúc Lợi nhuận (Hit & Run)
- London có biên độ dao động (Volatility) hẹp hơn NY. Mức 80/80 của NY là quá rộng đối với London (giá có thể không bao giờ chạm tới trong phiên).
- Cấu hình hiện tại của LDN là 30/30 (quá chật, dễ bị nhiễu chọc thủng).
- **Đề xuất:** Nâng lên mức **`TP_PIPS = 50`, `SL_PIPS = 50`** (Tỷ lệ 1:1 bất bại). Tăng `MAX_HOLD_BARS` lên **30** phút (giống NY) để giá có đủ thời gian chạy.

### 3. Tầm nhìn và Dữ liệu Vĩ mô (Macro Vision)
- Tăng `WINDOW_SIZE` từ 15 lên **20** (Đồng bộ với tốc độ 20 phút hoàn hảo của NY).
- **Làm sạch `MACRO_FEATURES`:**
  - Xóa bỏ `chop_14` và `bb_zscore` (Các chỉ báo phức tạp dễ gây nhiễu).
  - Thay bằng bộ Macro tinh khiết của NY: `log_ret`, `volume`, `bb_width`, `corr_60`, `spread_ret` cho cả XAUUSDm và DXYm.
  - (Đối với XAU, thêm tính năng `dxy_xau_anomaly` như bản thể NY).
- Giữ `ORDER_FLOW = false`, `VOL_REGIME = false`, `ZERO_NOISE_TARGET = false` (Đã chứng minh là độc hại ở NY).
