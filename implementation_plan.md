# Kế Hoạch Cải Tổ Dữ Liệu & Transfer Learning

Dự án đang chuyển đổi cấu trúc Dữ liệu đầu vào để tăng cường sức mạnh dự đoán Vàng (XAU) bằng cách loại bỏ các mã không giá trị và thêm các mã vĩ mô mạnh hơn.

## User Review Required

> [!WARNING]
> Mạng Nơ-ron (Transformer) có một luật bất thành văn: **Nếu thay đổi số lượng Cột (Features), kiến trúc Lớp Đầu Vào (Input Layer) sẽ bị thay đổi kích thước, dẫn đến lỗi KHÔNG THỂ nạp lại nguyên vẹn file `.pth` cũ.** 

Tuy nhiên, em sẽ vận dụng kỹ thuật **Transfer Learning (Chuyển giao học tập)** để xử lý vấn đề này. Cụ thể:
1. Ta sẽ bẻ khóa hàm `model.load_state_dict()` trong Pytorch. 
2. Chỉ loại bỏ/reset duy nhất Lớp Cổng Ngõ (`input_fc`, `pos_encoder`).
3. Giữ nguyên toàn bộ trí nhớ cốt lõi (Core Attention) của các lõi `TransformerEncoder` và Lớp Não Phân Loại (`output`).
4. **Hệ quả:** Mô hình sẽ cần mất khoảng vài epoch đầu để "làm quen" với các cột dữ liệu mới, nhưng tốc độ phục hồi lên Win-rate 85-90% sẽ siêu nhanh vì khả năng nhận dạng Pattern của não bộ vẫn còn nguyên!

Sếp duyệt cơ chế "Lắp Não Nửa Vời" này nhé?

## Proposed Changes

---

### Cập Nhật Thu Thập Dữ Liệu (Crawlers & Feature Engineering)

#### [MODIFY] [crawl_macro.py](file:///c:/Users/Le%20Anh%20Dung/OneDrive/Apps/ck/forex_predictor/src/crawl_macro.py)
*   Thêm mã `^VIX` của Yahoo Finance vào thư viện `macro_symbols` để hút chỉ số sợ hãi.

#### [MODIFY] [crawl_mt5.py](file:///c:/Users/Le%20Anh%20Dung/OneDrive/Apps/ck/forex_predictor/src/crawl_mt5.py)
*   Bổ sung mã `XAGUSD` (Bạc) vào mảng danh sách `symbols`.

#### [MODIFY] [feature_engineering.py](file:///c:/Users/Le%20Anh%20Dung/OneDrive/Apps/ck/forex_predictor/src/feature_engineering.py)
*   Khi `TARGET_PREFIX` là `XAU`, ta sẽ lập trình để tự động **XÓA BỎ BỚT** các Crypto Parquet (như `BTC`, `XRP`, `SOL`...) khỏi DataFrame tổng để giảm nhiễu (Dựa theo bài test Importance vừa rồi). 
*   Việc làm này tại file `feature_engineering.py` vừa làm sạch não bộ cho mẫu Vàng, vừa giữ nguyên được sự toàn vẹn của Data cho việc train Crypto Bot sau này (vì Crypto bot vẫn dùng chung đống Dữ kiện đó).

---

### Khắc phục File Nhựt Ký Huấn Luyện (Metrix)

#### [MODIFY] [training_metrix.json (Tương lai)]
*   Em xin giải thích với sếp: Ở block dữ liệu quá khứ em tự chạy Tool vá file thủ công nên chèn dòng `"data_features": "Danh sách..."` để sếp dễ thấy. Nhưng trong file `train_unified.py` hiện tại em đã viết cứng code là `"data_features": features.columns.tolist()`. Do đó ở **lượt chạy ngay sau đây của sếp**, mục đó sẽ trải dài 100% danh sách hàng trăm cột thực tế để sếp soi!

---

### Lập Trình Cơ Chế Tái Sinh Trọng Số (Transfer Learning)

#### [MODIFY] [train_unified.py](file:///c:/Users/Le%20Anh%20Dung/OneDrive/Apps/ck/forex_predictor/src/train_unified.py)
*   Tìm block Load Model: `model.load_state_dict(...)`
*   Viết lại logic lọc Weights (Lọc bỏ các Key thuộc Layer bị thay đổi kích cỡ do `num_features` thay đổi). Nạp với `strict=False`.
*   Giữ lại baseline Metric cho lần lưu tiếp theo.

## Verification Plan

### Automated Tests
*   Chạy lại `feat_eng` mới để kiểm chứng `num_features` tụt xuống do loại Crypto và tăng do VIX/XAG.
*   Theo dõi `Train_XAU.bat` 3 phút đầu để thấy Model không báo lỗi `Size Mismatch` mà nạp thành công Weight.

### Manual Verification
*   Sếp nhìn Console thấy Log: `Đã cắt bỏ Input Weights cũ... Giữ lại Core Transformer!` là đã hoàn hảo.
