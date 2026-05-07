# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 15:38:00] - Sửa lỗi hệ thống & Tái khởi động Run 124
- **Sự cố:** Phát hiện lỗi cú pháp (IndentationError) trong `train_v3.py` do quá trình vô hiệu hóa cơ chế xóa tự động gây ra. Điều này khiến Run 124 bị treo ngay khi khởi động.
- **Khắc phục:** Đã sửa lại thụt lề cho logic Push HF. Hệ thống huấn luyện hiện đã sẵn sàng 100%.
- **Tái khởi động:** Đang phát lệnh chạy lại **Run 124 (The Observer)** với cấu hình giữ nguyên: SL/TP 1.0%, Hold 30m.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
