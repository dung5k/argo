import subprocess

msg = """Dạ báo cáo Sếp Lê,

Em vừa kiểm tra lại hệ thống Prompt chiến thuật định kỳ (London V6). Hiện tại **Prompt ĐÃ CHO PHÉP** quyền thêm/bớt chỉ số rồi ạ! 

Cụ thể trong Prompt có ghi rõ quyền hạn:
> **Feature Engineering:** Bạn được toàn quyền thêm/bớt các FEATURES đầu vào (cắt bỏ các indicator nhiễu, thử nghiệm các tính năng mới) hoặc thay đổi cấu trúc mảng MTF_INPUTS (chuyển đổi Single-Timeframe hoặc Multi-Timeframe) để A/B testing tìm ra tổ hợp input có tỷ lệ nhiễu thấp nhất.

Hiện tại em vẫn đang giữ nguyên số lượng Feature gốc vì tập trung tối ưu Learning Rate, Dropout và Warmup trước để xem đáy Val Loss nằm ở đâu. Nếu Sếp muốn, em có thể bắt đầu can thiệp cắt bớt các Indicator rác (hoặc thử nghiệm đổi cấu trúc Timeframe) ngay từ các Seed tiếp theo để kiểm chứng luôn ạ!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
