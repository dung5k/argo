# XAG London V3.5 - Auto-Tuning Report

Báo cáo tiến trình tối ưu hóa bộ não `CFG_XAG_LDN_V3_5` cho phiên London.

## Lịch sử Auto-Tuning

### Khởi động lại kỷ nguyên mới (Dựa trên Thánh Giá NY)
Cấu trúc cũ của London (D32, Layer 2, TP/SL=30/30) đã đem lại kết quả rất tệ ở Run 27 (Composite Score 0.258). Kể từ Run 28, tôi quyết định áp dụng nguyên vẹn triết lý thiết kế đã thành công vang dội ở phiên NY:
- Kiến trúc đơn giản: `D_MODEL=16`, `NUM_LAYERS=1`
- Lọc nhiễu tối đa: `BATCH_SIZE=512`, `LR=1e-05`
- Tầm nhìn: `WINDOW=20`
- Pure Macro: Loại bỏ USTECm, chỉ dùng XAUUSDm và DXYm. Loại bỏ các chỉ báo rườm rà (chop_14, bb_zscore).
- Tỷ lệ Lợi nhuận: Do London dao động hẹp hơn NY, thay vì 80/80, tôi set `TP=50, SL=50` (Tỷ lệ 1:1).

---

### 1. `run_20260429_081500_v4_ldn_28` (Đang tiến hành)
- **Tham số thay đổi:** Thiết lập Baseline mới (D16, W20, TP/SL 50/50, B512).
- **Kỳ vọng:** Kiến trúc siêu việt của phiên NY sẽ chứng minh sức mạnh của nó trên phiên London, tạo ra một Kỷ lục Baseline mới cao hơn nhiều so với 0.258 của quá khứ.
- **Trạng thái:** Đang trong quá trình cào dữ liệu và chuẩn bị huấn luyện.
