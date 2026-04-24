# MÔ TẢ CẤU HÌNH CFG_LTC_ASIAN_V3_5 TỐT NHẤT (TÂN VƯƠNG)

File này lưu trữ những mô tả cho AI về cấu hình TỐT NHẤT đã được tìm thấy cho `CFG_LTC_ASIAN_V3_5` sau khi hoàn tất chiến dịch Auto-Tuning với 22 lượt chạy.

## 1. Nguồn gốc & Điểm số
Chiến dịch Auto-Tuning đã cày nát không gian tham số và khóa cứng cấu hình mạnh nhất tại **Lượt chạy 12** (`run_20260424_014500_v3_asian_12`).
- **Composite Score:** **0.5086** (Kỷ lục tuyệt đối, cao nhất trong 22 lượt chạy).
- Điểm yếu của các cấu hình khác (Batch 384, Dropout 0.35, N_Heads 4, N_Layers 2/4/5) đều đã được chứng minh là gây sụt giảm hiệu năng. Lượt 12 là Tỷ Lệ Vàng.

## 2. Thông số Tối ưu Kỹ thuật (Kiến trúc Mạng)
- **N_LAYERS:** `3` (Mạng vừa đủ nông để xử lý nhanh, không bị Overfit bởi nhiễu sóng ngắn phiên Á).
- **N_HEADS:** `8` (Phân mảnh góc nhìn đủ rộng để tổng hợp các mối tương quan yếu thành tín hiệu mạnh).
- **D_MODEL:** `64` (Đủ sức chứa không gian vector, nén xuống 32 gây sụp đổ, tăng lên 128 gây thừa mứa).
- **DROPOUT:** `0.4` (Màng lọc hoàn hảo, nới xuống 0.35 hay tăng lên 0.45 đều làm giảm Score thê thảm).
- **LEARNING_RATE:** `2e-5` (Tốc độ học tiêu chuẩn hoàn mỹ, 1.5e-5 quá chậm).
- **BATCH_SIZE:** `256` (Cho mức Regularizing Noise tốt nhất, nhảy thoát khỏi Local Minima. Batch 384 và 128 đều làm rớt Score).

## 3. Điều chỉnh cho Asian session (00:00–07:00 UTC) - Đã chốt từ Base
| Tham số | Giá trị | Lý do |
|---|---|---|
| WINDOW_SIZE | 20 | Volume thấp, cần context dài hơn để thấy xu hướng. |
| MAX_HOLD_BARS | 12 | Asian ít volatile, nến hội tụ chậm hơn, cần gồng lâu hơn 1 chút. |
| WARMUP_EPOCHS | 15 | Dataset Asian nhỏ hơn London. |
| FREQ_MIN_N | 80 | Ít tín hiệu hơn trong đêm. |
| FREQ_MAX_N | 500 | Ít tín hiệu hơn trong đêm. |

## 4. MACRO_FEATURES (Hệ Sinh Thái Tương Quan)
Bộ tính năng được thiết kế riêng cho phiên Á (Giữ nguyên từ Base):
- **BTCUSDT:** Trục chính không thể thiếu (log_ret, bb_width, volume, corr_60).
- **ETHUSDT:** Dẫn dắt thị trường crypto đêm châu Á mạnh (log_ret, volume, corr_60).
- **XRPUSDT:** Tương quan cục bộ mạnh với LTC trong đêm (log_ret, volume).
- **XAUUSDm:** Đã loại bỏ do thiếu tương quan trực tiếp, tránh nhiễu API.
- **USTECm / DXYm:** Không sử dụng do thị trường Mỹ đóng cửa.
