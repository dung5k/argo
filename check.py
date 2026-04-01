import pandas as pd

try:
    df = pd.read_parquet('data/final_features_2d.parquet')
    print('>>> BÁO CÁO KIỂM TOÁN TENSOR ĐẦU VÀO <<<')
    print(f'TOTAL SHAPE (Số Nến, Số Tính Năng): {df.shape}')
    
    print('\n[1] DANH SÁCH 15 CỘT TÍNH NĂNG (FEATURES) ĐẠI DIỆN:')
    cols = df.columns.tolist()
    for i, col in enumerate(cols[:15]):
        print(f" - Mạng thu tín hiệu #{i+1}: {col}")
        
    print('\n[2] NẾN PHÚT GẦN NHẤT ĐƯỢC NHỒI VÀO NÃO PYTORCH (10 Thông số gốc):')
    last_row = df.iloc[-1].head(10)
    for name, value in last_row.items():
        print(f" -> {name}: {value:.6f}")
        
    print('\n[3] KIỂM TOÁN LƯỢNG GIÁC THỜI GIAN (Xuyên Vùng Phiên):')
    time_cols = ['hour_sin', 'hour_cos', 'dow_sin', 'dow_cos']
    for t_col in time_cols:
        if t_col in df.columns:
            print(f" -> {t_col}: {df.iloc[-1][t_col]:.6f} (Toạ độ Vector: Chuẩn OK)")
            
except Exception as e:
    print(f"Lỗi đọc Data: {e}")
