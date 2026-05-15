# NHIỆM VỤ ĐỊNH KỲ (GH): AUTO-TUNING XAG ASIAN BRAIN (CỤC BỘ)

Hệ thống gọi bạn từ bộ quản lý Task JSON (task id: `xag_asian_auto_tuning`). Bạn đóng vai trò Kỹ sư AI tự động hóa trên **máy GH** để tìm cấu hình tốt nhất cho bộ não `CFG_XAG_ASIAN_V3_5`. 

**GIÁM SÁT SỨC KHỎE (HEALTH CHECK):**
- Nếu nhận thấy lượt chạy (Run) hiện tại kéo dài bất thường (ví dụ > 2 giờ) mà không có kết quả, phải chủ động `taskkill` tiến trình treo, thực hiện điều tra nguyên nhân qua logs (`bg_train.log` hoặc console) và kích hoạt chạy lại (Restart).

## BƯỚC 1: Phân tích Lịch sử & Tư duy Tối ưu hóa (Quant/ML Expert)

### 1. Thu thập Ngữ cảnh (Context Gathering):
- Đọc kết quả của lượt chạy mới nhất `workspaces/CFG_XAG_ASIAN_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
- **KỶ LỤC CẦN PHÁ (Baseline - CẬP NHẬT):** 
  - **Run Real Price V3 (run_20260515_113510_v3):** Win Rate **58.96%**, Score = **0.5774**. (Sử dụng Evaluator P_tensor Giá Thực, TP30/SL30).
- **MỤC TIÊU TIẾP THEO:** Duy trì Win Rate > 60% và đẩy N lên cao hơn nữa (> 150) hoặc nâng Win Rate lên > 65% với N > 50.

### 2. Phân tích Hiệu suất & Dọn dẹp (Cleanup/Push):
- So sánh `Composite Score`, `Win Rate`, `Loss` của lượt mới nhất với Baseline. 
- **HÀNH ĐỘNG BẮT BUỘC:** 
  - NẾU Win Rate < 60% HOẶC N < 50: **XÓA NGAY** (`rm -rf`) thư mục run đó.
  - NẾU Win Rate >= 60% VÀ N >= 50: Đồng bộ lên Hugging Face và báo cáo chiến thắng.
- **BÁO CÁO TỔNG QUAN:** Cập nhật `training_report.md`. Ghi rõ: Run ID, tham số thay đổi, kết quả, và quyết định tiếp theo.

### 3. Nguyên tắc Tối ưu hóa (Strict Rules):
- **Luật 1/2:** CHỈ thay đổi 1 đến tối đa 2 tham số mỗi lượt.
- **Quant Rationale:** Mỗi khi tạo run mới, phải viết rõ **Luận điểm Quant/ML** vào `training_report.md`.
- **Session-Specific (Asian):** 
  - Cấu hình TP30/SL30 + MAX_HOLD 20 đang là "Long-Momentum" tốt nhất.
  - `AUDUSDm` là bắt buộc. `USTECm` là nhiễu.

### 4. Gợi ý hướng đi tiếp theo:
- Thử **TP30 / SL40** (mở rộng SL để tránh quét râu nến) trên nền Run 23.
- Thử tăng `LEARNING_RATE` nhẹ (1.2e-05) trên nền Run 23 để hội tụ nhanh hơn.
- Thử **Label Smoothing** cực nhẹ (0.005) để xem có ổn định được WR ở mức cao hơn không.

## BƯỚC 2: Chuẩn bị dữ liệu (Hàng Đợi)
... (Giữ nguyên các bước kỹ thuật) ...
