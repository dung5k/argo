import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

def load_and_align_data(data_path):
    print("1. Đang gộp toàn bộ dữ liệu & CHUẨN HOÁ MÚI GIỜ (Timezone Validation)...")
    # Lấy danh sách file nhưng loại trừ ngay 2 file thành phẩm đầu ra để tránh lỗi vòng lặp đệ quy ma trận
    files = [f for f in os.listdir(data_path) if f.endswith('.parquet') and not f.startswith('final') and not f.startswith('target')]
    
    df_list = []
    for file in files:
        symbol = file.replace('_1m_2025_2026.parquet', '').replace('_1h_2025_2026.parquet', '').upper()
        df = pd.read_parquet(os.path.join(data_path, file))
        
        # ĐỒNG BỘ MÚI GIỜ (Timezone Alignment) VỀ CHUẨN UTC TRƯỚC KHI GỘP
        # Dữ liệu do crawl_mt5 rút về ĐÃ ĐƯỢC CHUẨN HOÁ THÀNH UTC. Tuyệt đối không tính lại!
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
            
        # Tiêu hao nến trùng lặp ở Châu Âu do giờ mùa Đông lặp lại 1 tiếng (02:00 -> 02:59 lặp 2 lần)
        df = df[~df.index.duplicated(keep='last')]
        
        # Bám tiền tố (Prefix) tên mã vào tất cả các cột
        rename_map = {col: f"{symbol}_{col}" for col in df.columns}
        df = df.rename(columns=rename_map)
        df_list.append(df)
        
    print("-> Đang hợp nhất (Outer Join) tất cả các mã vào 1 bảng duy nhất...")
    merged_df = pd.concat(df_list, axis=1)
    
    # 🌟 GỌT NẾN MA (GHOST CANDLE FIX): Lấy XAUUSD làm Xương Sống 🌟
    # Nếu Crypto cào data muộn hơn và nòi ra 1 phút tương lai, ta Rụng bỏ phút đó đi!
    xauusd_col = [c for c in merged_df.columns if 'XAUUSD_close' in c]
    if xauusd_col:
        xauusd_series = merged_df[xauusd_col[0]].dropna()
        merged_df = merged_df.reindex(xauusd_series.index)
    
    # Rất quan trọng: Phải sort Index theo thời gian trước, nếu không ffill sẽ bị điền rác.
    merged_df.sort_index(inplace=True)
    
    # 🌟 ĐỒNG BỘ THEO MÚI GIỜ CHUẨN MỸ 🌟
    merged_df.index = merged_df.index.tz_convert('America/New_York')
    
    # Điền khuyết (ffill) các thông số Macro (Vĩ mô) chạy theo ngày hoặc giờ
    merged_df.ffill(inplace=True)
    
    print("-> Data Unlocked: Gộp Trọn Vẹn Giai Đoạn 2025-2026 (Full History)...")
    
    # --- THỦ TỤC TIME EMBEDDING (Học Hành Vi Múi Giờ Châu Lục) ---
    # Phân tích đặc tính Thời Gian giúp AI phân loại Ranh Giới Giao Dịch (Phiên Á / Âu / Mỹ)
    hour = merged_df.index.hour
    dayofweek = merged_df.index.dayofweek
    
    # Vector hóa Hình Lượng giác (Sin/Cos) để AI hiểu Khái niệm vòng lặp (23h và 00h kề nhau 1 góc tròn)
    merged_df['hour_sin'] = np.sin(2 * np.pi * hour / 24.0)
    merged_df['hour_cos'] = np.cos(2 * np.pi * hour / 24.0)
    merged_df['dow_sin'] = np.sin(2 * np.pi * dayofweek / 7.0)
    merged_df['dow_cos'] = np.cos(2 * np.pi * dayofweek / 7.0)
    
    # Rụng bỏ những ngày đầu tiên bị NaN do các mã lệch ngày xuất phát (MT5 vs Binance)
    merged_df.dropna(inplace=True)
    
    print(f"-> HOÀN TẤT GỘP: Ma trận Dữ liệu Full-Time ôm trọn {merged_df.shape[0]:,} dòng x {merged_df.shape[1]} cột tính năng.")
    return merged_df

import joblib

def create_stationary_features(df, is_live=False):
    print("2. Chuyển đổi dữ liệu sang dạng dừng (Stationary) bằng Log Returns...")
    feature_df = pd.DataFrame(index=df.index)
    
    for col in df.columns:
        if col in ['hour_sin', 'hour_cos', 'dow_sin', 'dow_cos']:
            # Giữ nguyên giá trị Vector hình học thuần khiết, KHÔNG tính Log Return
            feature_df[col] = df[col]
        elif 'volume' in col.lower() or 'spread' in col.lower():
            # Log(Volume + 1) để chuẩn hóa khối lượng và tránh lỗi chia rỗng
            feature_df[col] = np.log1p(df[col].fillna(0))
        else:
            # Trừ khử "Tính không dừng" (Trend) bằng Log Return của giá
            # Cẩn thận xử lý lỗi chia cho 0 bằng cách thay 0 thành NaN trước
            shifted_col = df[col].shift(1).replace(0, np.nan)
            feature_df[f"{col}_log_ret"] = np.log(df[col] / shifted_col)
            
    # Loại bỏ các giá trị Inf do phép chia sinh ra và các hàng NaN
    feature_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    feature_df.dropna(inplace=True)
    
    # Scale tất cả thành Mean=0, Std=1 để đẩy lưới Nơ-ron chạy hội tụ siêu tốc
    # KHOÁ LÕI SCALER (TRÁNH LỆCH PHA GIỮA TRAIN VÀ LIVE)
    scaler_path = os.path.join(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data", "scaler.pkl")
    
    if is_live and os.path.exists(scaler_path):
        print("-> [LIVE MODE] Đang dùng Khuôn Đúc Scaler.pkl từ Mốc Huấn Luyện...")
        scaler = joblib.load(scaler_path)
        scaled_data = scaler.transform(feature_df)
    else:
        print("-> [TRAIN MODE] Đang tính toán Độ Lệch Chuẩn 15 Tháng và Đúc Scaler.pkl...")
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(feature_df)
        joblib.dump(scaler, scaler_path)
        
    scaled_df = pd.DataFrame(scaled_data, index=feature_df.index, columns=feature_df.columns)
    
    print(f"-> Hoàn tất Stationarity & Scaling. Kích thước Tensor: {scaled_df.shape}")
    return scaled_df, scaler

def create_3d_sequences(features_df, target_series, window_size=60, forecast_horizon=5):
    print(f"3. Cắt ma trận thành khối 3D Tensor (Window={window_size}m, Dự báo T+{forecast_horizon}m)...")
    
    X, y = [], []
    feature_values = features_df.values
    target_values = target_series.values
    
    # Cắt trượt (Sliding Window) 
    for i in range(len(features_df) - window_size - forecast_horizon + 1):
        # Lấy X cây nến làm Input (Ma trận 2D)
        window_data = feature_values[i : i + window_size]
        X.append(window_data)
        
        # Nhãn (Label): Đoán giá mục tiêu ở T+y
        current_price = target_values[i + window_size - 1]
        future_price = target_values[i + window_size + forecast_horizon - 1]
        
        # Bài toán Classification (Dự đoán giá Up hay Down)
        # 1: Up hoặc Đứng im, 0: Down
        direction = 1 if future_price >= current_price else 0
        y.append(direction)
        
    X = np.array(X)
    y = np.array(y)
    
    print(f"-> [THÀNH CÔNG] Dữ liệu Input X: {X.shape} - (Samples, Nến, Tính năng)")
    print(f"-> [THÀNH CÔNG] Dữ liệu Output y: {y.shape} - (Samples, Label Biên)")
    return X, y

if __name__ == "__main__":
    import sys
    is_live = len(sys.argv) > 1 and sys.argv[1] == "live"
    
    data_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data"
    
    # 1. Gộp toàn bộ Data
    merged_df = load_and_align_data(data_path)
    
    # Lưu giá Close của Vàng làm cột Mục tiêu (Target) trước khi Feature Engineering biến đổi nó
    xauusd_close = merged_df['XAUUSD_close']
    
    # 2. Xử lý tính năng tĩnh (Stationary Log Returns & Scaling)
    scaled_features, scaler = create_stationary_features(merged_df, is_live=is_live)
    
    # Cân bằng index do hàm tạo Log Return làm mất 1 dòng đầu tiên
    target_aligned = xauusd_close.loc[scaled_features.index]
    
    print("3. Khởi tạo mảng Target T+5 (Phương án Triple Barrier T+5 phút)...")
    lookahead_minutes = 5
    tp_threshold = 0.5  # Chạm chốt lời 0.5 giá vàng (+5 pip)
    sl_threshold = 0.5  # Chạm cắt lỗ 0.5 giá vàng (-5 pip)
    
    # [LIVE MODE FIX] Nếu Live thì không DropNA! Giữ trọn vẹn điểm Giao dịch Cuối cùng.
    if is_live:
        final_features = scaled_features
    else:
        # Cắt ma trận chênh lệch giá 5 phút trong tương lai
        future_diffs = []
        for i in range(1, lookahead_minutes + 1):
            future_diffs.append((xauusd_close.shift(-i) - xauusd_close).loc[scaled_features.index].values)
            
        diff_matrix = np.array(future_diffs).T  # Shape: (N_Samples, 5)
        
        print("-> Đang gán rào cản SL/TP bằng Numpy...")
        labels = np.zeros(len(diff_matrix))
        
        for i in range(len(diff_matrix)):
            row = diff_matrix[i]
            if np.isnan(row[-1]):  # Đuôi dữ liệu khuyết
                labels[i] = np.nan
                continue
                
            hit_tp = np.where(row >= tp_threshold)[0]
            hit_sl = np.where(row <= -sl_threshold)[0]
            
            first_tp = hit_tp[0] if len(hit_tp) > 0 else 999
            first_sl = hit_sl[0] if len(hit_sl) > 0 else 999
            
            if first_tp < first_sl and first_tp != 999:
                labels[i] = 1.0  # Lên chạm TP trước
            elif first_sl < first_tp and first_sl != 999:
                labels[i] = 0.0  # Xuống chạm SL trước
            else:
                # Không chạm biên, chốt sổ theo giá tại T+5
                labels[i] = 1.0 if row[-1] > 0 else 0.0
                
        target_direction = pd.Series(labels, index=scaled_features.index)
        target_direction.dropna(inplace=True)
        final_features = scaled_features.loc[target_direction.index]
        target_direction.to_frame(name='target').to_parquet(os.path.join(data_path, "target_direction.parquet"))
    
    print(f"-> Dữ liệu Input cuối cùng: {final_features.shape}")
    
    # Lưu file siêu nhẹ ra Parquet để PyTorch DataLoader đọc (Tránh quá tải 7GB RAM bằng ma trận 3D cục bộ)
    final_features.to_parquet(os.path.join(data_path, "final_features_2d.parquet"))
    
    print("\n[OK] Pipeline Feature Engineering siêu nén đã lưu thành công. Chuyển qua khởi động PyTorch Dataset!")
