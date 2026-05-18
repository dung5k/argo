import io

path = r'd:\DungLA\client1\.agent\periodic_prompt_ltc_all_sessions_v6_local.md'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep lines 1-62 (index 0-61), replace rest with new template
keep = lines[:62]

new_section = """
## 📋 MẪU BÁO CÁO TELEGRAM BẮT BUỘC (THEO MẪU MỚI)
> 
> Mỗi lần kết thúc State Machine, BẮT BUỘC gửi báo cáo theo đúng mẫu sau:
> 
> ```
> 🤖 Argo2 (ĐIỀU PHỐI TOÀN CỤC LTC V6):
> 
> 🌍 TỔNG HỢP KẾT QUẢ TỐT NHẤT 3 PHIÊN:
> | Phiên      | WR Tốt Nhất | Hòa Vốn (BE) | Biên LN   | TP/SL       |
> |------------|-------------|--------------|-----------|-------------|
> | 🏯 ASIAN   | <W_A>%      | <BE_A>%      | <+pp_A>pp | <TP>/<SL>   |
> | 🗽 NY      | <W_N>%      | <BE_N>%      | <+pp_N>pp | <TP>/<SL>   |
> | 💂 LONDON  | <W_L>%      | <BE_L>%      | <+pp_L>pp | <TP>/<SL>   |
> 
> 📌 Hòa Vốn = SL/(TP+SL). Biên LN = WR - Hòa Vốn. Phiên nào Biên LN cao hơn là vượt trội hơn thực tế.
> 
> 🎯 QUYẾT ĐỊNH ĐÀO TẠO TIẾP THEO:
> 👉 Đã chọn phiên: **<TÊN PHIÊN (ASIAN/LONDON/NY)>**
> Lý do: <Phiên có Biên LN thấp nhất / đang có đà tốt nhất cần chạy tiếp>
> 
> 📊 Cấu hình Run chuẩn bị chạy (<Tên Run>):
> - Base TF: <TF> | LR: <LR> | TP/SL: <TP/SL> | Hòa Vốn mục tiêu: <BE%>
> - Leading Indicators: <Liệt kê các mã>
> - Dropout: <D> | Warmup: <W> Epochs
> 
> <Phân tích lý do tại sao lại chọn phiên này để đào tạo tiếp. Đưa ra kỳ vọng đột phá dựa trên dữ liệu tổng hợp.>
> ```
> 
> **LƯU Ý:** 
> - Hòa Vốn (BE) = SL / (TP + SL). Ví dụ: TP=0.5%, SL=0.3% → BE = 0.3/0.8 = **37.5%**.
> - Biên LN = WR - BE. Phiên nào có Biên LN cao nhất là phiên đang hoạt động hiệu quả nhất thực tế.
> - Lấy dữ liệu từ Diary và các file `training_metrics_v3.json` của từng phiên để điền vào.
> - Luôn gọi lệnh: `python .agent/send_to_tele.py "<Nội_dung_theo_mẫu>" --done`
"""

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(keep)
    f.write(new_section)

print('SUCCESS')
