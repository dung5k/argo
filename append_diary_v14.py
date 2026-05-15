import codecs

diary_text = """
### Tóm tắt Vòng 13 (Thử thách siêu hạn TP=0.0040, R:R=2.0):
- **Kết quả:** Đã chạm ngưỡng giới hạn! Khi đẩy Take Profit lên 0.40%, Win Rate bắt đầu giảm xuống **71.42%** và Composite Score lui về **0.5207**. 
- **Phân tích Sâu:** Biến động chậm chạp của phiên Á không đủ sức kéo giá đi một mạch 0.40% mà không vướng phải các đợt pullback nhỏ, dẫn đến việc bị quét Stoploss nhiều hơn. Do đó, mức TP lý tưởng nhất chính thức chốt ở mức **0.0035** (như Vòng 12).

### Ý tưởng tiếp theo (Vòng 14):
- **Hành động:** Quay lại mức Take Profit đỉnh cao của Vòng 12 (`TP=0.0035`). Lần này, ta sẽ siết chặt rủi ro bằng cách giảm **Stop Loss (SL) từ 0.0020 xuống 0.0015**.
- **Mục tiêu:** Mức SL cực ngắn này sẽ đẩy tỷ lệ R:R lên con số **2.33**. Mục đích là để kiểm tra xem "độ nhiễu" (noise) của phiên Á có thường xuyên quét qua mốc 0.15% trước khi đi đúng xu hướng hay không. Nếu Win Rate vẫn trụ được quanh mức 65-70%, thì đây sẽ là một cỗ máy in tiền thực sự nhờ R:R khổng lồ.
"""

with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)
