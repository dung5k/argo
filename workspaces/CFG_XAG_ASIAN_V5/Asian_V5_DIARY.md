# Nhật ký Huấn luyện XAG Asian V5 - Regime-Aware

## 🏆 Bảng Vàng Thành Tích V5
| Run ID | Win Rate | Score | Đặc điểm |
|---|---|---|---|
| `run_20260511_102100_v5_asian_ultimate_sniper` | **86.67%** | **0.7840** | MSE Gate 0.05, Diverse features, D160-L3 (CHAMPION) |
| `run_20260511_093300_v5_asian_diverse_sniper` | **84.38%** | 0.7405 | Diverse features, D160-L3 |
| `run_20260511_022400_v5_asian_pure_focus` | **76.70%** | 0.7250 | Pure Focus XAU, D160-L3 |

---

### [2026-05-11 10:23:00] - Đánh giá Run: run_20260511_102100_v5_asian_ultimate_sniper
- **Kết quả:** Composite Score = **0.7840** | Win Rate = **86.67%** | Epoch **39**
- **Insight:** Việc áp dụng `MSE Gate 0.05` đã chứng minh sức mạnh trong việc lọc nhiễu. Mô hình chỉ học từ những mẫu dữ liệu chuẩn mực nhất, dẫn đến Win Rate tăng vọt lên 86.67%.
- **Hành động:** Đóng gói bản Ultimate này làm cấu hình sản xuất vĩnh viễn cho Phase V5 trước đó.

---

### [2026-05-26 18:55:00] - Đánh giá Toàn cục (State 0) & Khởi chạy Run: run_20260526_185500_v5_asian_gold_anchor_v2
- **Đánh giá Toàn cục:** Champion hiện tại của Asian V5 đang có Win Rate rất cao (86.67%) nhưng Composite Score (0.7840) lại thấp hơn New York (0.8595) và London (20.9032). Nguyên nhân là do bộ lọc MSE Gate 0.05 quá khắt khe làm hạn chế nghiêm trọng số lượng giao dịch thực tế (N). Hệ thống quyết định chọn Asian V5 làm tiêu điểm tối ưu để mở rộng số lượng lệnh chất lượng mà vẫn giữ vững WR cao.
- **Ý tưởng cải tiến tối thượng (Asian Gold Anchor v2):**
  - **Mỏ neo vĩ mô tinh giản:** Loại bỏ hoàn toàn Crypto (BTC, ETH) khỏi `MACRO_FEATURES` để tránh nhiễu động chéo. Chỉ sử dụng cặp đôi Vàng (`XAUUSDm`) và DXY (`DXYm`) làm macro features (lấy cảm hứng từ sự thành công rực rỡ của London).
  - **Mở rộng cơ hội giao dịch:** Nới nhẹ `MSE_GATE_PERCENTILE` từ **0.05** lên **0.08** để cho phép AI học từ tập dữ liệu phong phú hơn một chút, giúp tăng số lượng lệnh giao dịch thực tế (N) nhằm đẩy Composite Score vượt mốc 0.85.
  - **Mở rộng Window size:** Đẩy `WINDOW_SIZE` lên **60** nến (từ 45) để mô hình Transformer có cái nhìn momentum dài hạn và vững chắc hơn trong phiên Á.
  - **Bảo hiểm vận hành & Phần cứng:** Đặt `BATCH_SIZE` = **64** và chạy hoàn toàn trên **CPU** (`CUDA_VISIBLE_DEVICES="-1"`) để tránh tuyệt đối các lỗi tràn bộ nhớ ảo (Virtual Memory OOM) của Windows khi ổ C bị đầy.
- **Giả thuyết:** Cấu hình Gold Anchor v2 tinh giản kết hợp mở rộng nhẹ cổng MSE sẽ giúp mô hình bắt được nhiều cơ hội giao dịch chất lượng cao hơn, công phá mục tiêu Composite Score vượt ngưỡng 0.85 một cách bền bỉ.
