# HƯỚNG DẪN KHỞI ĐỘNG CLIENT 1

Đây là file hướng dẫn dành riêng cho máy Client 1 để nhận và thực thi các mô phỏng (Training, Stop) từ máy Host.

## Cách Khởi Động Nhanh (Khuyên Dùng)

Sếp chỉ cần **nhấp đúp chuột (Double Click)** vào file `START_CLIENT.bat` nằm ngay trong thư mục này.
Nó sẽ tự động:
1. Mở Terminal mới.
2. Thiết lập đường dẫn tương đối để chạy thư viện.
3. Kích hoạt `client_master.py` để liên tục lắng nghe Lệnh thông qua OneDrive.

---

## Cách Khởi Động Thủ Công Bằng Terminal

Nếu sếp muốn tự gõ lệnh trên Terminal, hãy mở Terminal, di chuyển về thư mục gốc `forex_predictor` (chứ không phải nằm trong thư mục `client1` nhé) và dán dòng này:

```powershell
.\venv\Scripts\python.exe src\client_master.py --client-id client1 --base-dir "%cd%"
```

*Lưu ý: Chỉ cần chạy 1 lần. Kể từ lúc này, mọi lệnh `[TRAIN]` hay `[STOP]` sếp đẩy từ máy Host (Antigravity) sẽ được Client tự động đọc rồi thực thi liền. Mọi thay đổi code trên máy Host cũng sẽ được Client dùng luôn.*
