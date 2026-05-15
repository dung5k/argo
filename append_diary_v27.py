# -*- coding: utf-8 -*-
import codecs

diary_text = """
### Tóm tắt Vòng 26 (Tăng D_MODEL lên 64):
- **Kết quả:** Thảm họa! Mở rộng không gian Embedding từ 32 lên 64 chiều đã phá hủy hoàn toàn mô hình. Win Rate cắm đầu xuống **55.0%** với tín hiệu tối đa chỉ đạt ngưỡng 0.57.
- **Phân tích Sâu:** Đây là hiện tượng Overparameterization (Dư thừa tham số) kinh điển. Dữ liệu phiên Á quá mỏng và đầy rẫy nhiễu ngẫu nhiên. Việc cấp cho Transformer không gian học quá lớn (`D_MODEL=64`) khiến nó "học vẹt" (overfit) toàn bộ lượng nhiễu này thay vì tìm ra tín hiệu OrderFlow thật sự, dẫn đến khả năng tổng quát hóa (generalization) bằng 0.

### Ý tưởng tiếp theo (Vòng 27):
- **Hành động:** Trả `D_MODEL` về mốc lý tưởng 32. Chuyển sang tối ưu chiều sâu: Hạ số lượng lớp Transformer (`NUM_LAYERS`) từ mức chuẩn 2 xuống **1**. Tất cả các tham số Golden Config (LR 2e-5, Dropout 0.25, TP/SL chuẩn) được bảo toàn.
- **Mục tiêu:** Áp dụng nguyên lý Occam's Razor (Dao cạo Ockham): Nếu phiên Á quá nhiễu, một mô hình cực kỳ đơn giản (siêu mỏng) có thể sẽ chống lại nhiễu tốt hơn một mô hình phức tạp. Việc chỉ dùng 1 layer Transformer ép mô hình phải tập trung vào các đặc trưng nguyên thủy nhất (primitive features), kỳ vọng giữ nguyên được Win Rate 77% nhưng tăng đáng kể tốc độ suy luận (Inference Speed) của Live Bot.
"""

with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)
