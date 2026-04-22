# NHIỆM VỤ ĐỊNH KỲ (HOST): AUTO-TUNING LTC NY BRAIN (PHÂN TÁN)

Hệ thống sẽ gọi bạn chạy lại prompt này định kỳ mỗi 10 phút một lần. Trách nhiệm của bạn là đóng vai trò một Kỹ sư AI tự động hóa trên máy HOST để điều phối, đi tìm cấu hình và phương án tốt nhất cho bộ não `CFG_LTC_NY_V3_5` và giao việc cho `client1`.

Hãy thực thi nghiêm ngặt theo các bước sau trong mỗi lần được gọi:

## BƯỚC 1: Kiểm tra tiến trình Training hiện tại trên Client
Sử dụng công cụ `host_controller.py` để kiểm tra trạng thái của `client1` xem nó có đang bận huấn luyện hay không.
- Gợi ý: Chạy lệnh `python src/orchestration/host_controller.py listen --client-id client1 --time 10` để xem log trực tiếp, hoặc kiểm tra trạng thái Busy.
- **1.1 Đang Training**: Nếu log/trạng thái cho thấy tiến trình đang chạy (ví dụ: `BUSY — task: train`), bạn BỎ QUA phiên làm việc này. Dừng lại và kết thúc công việc ngay.
- **1.2 Không Training**: Nếu tiến trình đã hoàn thành (hoặc Client đang `IDLE`), chuyển sang BƯỚC 2.

## BƯỚC 2: Đồng bộ và Kiểm tra kết quả huấn luyện mới nhất từ Mây
Trước khi đánh giá, bạn phải kéo dữ liệu mới nhất từ HuggingFace về máy HOST.
- Chạy kịch bản đồng bộ: `python sync_workspaces.py` để lấy các thư mục `brains/` mới nhất về.
Sử dụng công cụ File/Thư mục để truy cập vào `workspaces/CFG_LTC_NY_V3_5/runs/`.
Hãy tìm thư mục `run_...` mới nhất và đọc file báo cáo kết quả (như `training_metrics_v3.json` nằm trong `brains/`).
- **2.2.1 Lần chạy đầu tiên (Chưa có kết quả)**: Nếu không có thư mục nào hoặc không tìm thấy file metrics, có nghĩa là chưa training lần nào. Chuyển thẳng tới BƯỚC 4 để khởi tạo lần chạy đầu.
- **2.2.2 Đã có kết quả**: Nếu có file kết quả, đọc và phân tích toàn bộ các chỉ số bên trong. Chuyển sang BƯỚC 3.

## BƯỚC 3: Review và Sửa đổi Cấu hình (Góc nhìn Chuyên gia)
Dựa vào phân tích ở Bước 2.2.2, **BẠN PHẢI ĐÓNG VAI TRÒ LÀ MỘT CHUYÊN GIA AI & ĐỊNH LƯỢNG TÀI CHÍNH (QUANT EXPERT) HÀNG ĐẦU**. 
Hãy suy luận sâu sắc, phân tích đa chiều các chỉ số (Win Rate, Composite Score, Sharpe, Max Drawdown nếu có) và đối chiếu với lịch sử những cấu hình đã chạy trong các thư mục `runs/` trước đó. Bạn cần tìm ra quy luật xem thông số nào mang lại kết quả tốt nhất.
Mọi quyết định đưa ra phải dựa trên tư duy phản biện sắc bén của chuyên gia để tránh overfitting và tìm ra "Alpha" thực sự. Đưa ra lập luận logic vững chắc trước khi thực hiện các thay đổi.
Những thay đổi BẠN CÓ QUYỀN VÀ NÊN làm:
- **Thay đổi Input Features**: Thử nghiệm thêm hoặc bớt các chỉ số vĩ mô trong `MACRO_FEATURES` (như DXYm, Crypto, Vàng...).
- **Thay đổi Thông số Trading**: Tinh chỉnh lại `TP_PCT`, `SL_PCT`, `MAX_HOLD_BARS` xem tỷ lệ Risk/Reward nào tối ưu.
- **Thay đổi Hyperparameters**: Điều chỉnh `WINDOW_SIZE`, `LEARNING_RATE`, `BATCH_SIZE` hoặc bất kỳ tham số gì trong file cấu hình.
- **Thay đổi Code**: Bạn được phép sửa đổi logic mã nguồn trong `src/` (như thuật toán sinh Feature, kiến trúc Model, hay hàm Loss) nếu có ý tưởng đột phá.
> LƯU Ý QUAN TRỌNG: **TUYỆT ĐỐI KHÔNG ĐƯỢC CHỈNH SỬA FILE `base_config.json` GỐC!** Bạn phải giữ nguyên file gốc làm mẫu.
> Khi quyết định thay đổi, bạn BẮT BUỘC phải thực hiện 2 bước:
> 1. Tự sinh ra một chuỗi thời gian (VD: `20260422_143008`) và TẠO MỚI một thư mục lượt chạy, ví dụ: `workspaces/CFG_LTC_NY_V3_5/runs/run_20260422_143008_v3/`.
> 2. Copy file `base_config.json` vào thư mục vừa tạo và đặt tên là `config.json`. Thực hiện thay đổi thông số trên file mới này. File này tuyệt đối KHÔNG ĐƯỢC XÓA vì sẽ dùng cho Live Trade sau này.

## BƯỚC 4: Tạo Lượt Chạy Mới, Đẩy HF & Yêu Cầu Client Đào Tạo
1. **Chuẩn bị Dữ liệu và Tạo Run Mới**: Bạn BẮT BUỘC phải gọi script cào dữ liệu trước, sau đó mới gọi script sinh lại bộ dữ liệu. Các script sẽ nhận diện và lưu thẳng Tensors vào thư mục Run vừa tạo, và đẩy toàn bộ lên HuggingFace.
   - Chạy lệnh cào dữ liệu: `python scripts/crawl_crypto_v3.py workspaces/CFG_LTC_NY_V3_5/runs/run_20260422_143008_v3/config.json`
   - Chạy lệnh sinh Tensor: `python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_NY_V3_5/runs/run_20260422_143008_v3/config.json`
   - Đảm bảo lệnh trên chạy hoàn tất không có lỗi.

2. **Commit Git**: Commit mọi thay đổi code/config lên Git để dự phòng. (`git add . ; git commit -m "auto-tuning LTC NY" ; git push`)

3. **Giao Việc Cho Client (Điều phối Đào tạo)**: Gọi lệnh của `host_controller.py` để ra lệnh cho `client1` thực hiện quá trình training. *Lưu ý: Truyền đường dẫn của file config mới tạo vào cờ --file.*
   - Chạy lệnh: `python src/orchestration/host_controller.py train --client-id client1 --session ny --file workspaces/CFG_LTC_NY_V3_5/runs/run_20260422_143008_v3/config.json --script src/training_v3/train_v3.py --scratch`

4. **Thông báo Telegram**: Sử dụng script `.agent/send_to_tele.py` để báo cáo ngắn gọn về việc: Bạn vừa đánh giá kết quả ra sao, thay đổi những gì ở Cấu hình/Code, Lượt chạy mới (Run ID) là gì, và đã kích hoạt quá trình huấn luyện phân tán trên `client1`.

Chỉ kết thúc toàn bộ công việc và gọi `--done` sau khi `client1` đã xác nhận nhận lệnh và báo trạng thái BUSY! Chúc bạn tìm ra "chén thánh" thành công!
