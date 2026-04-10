import os
import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import StandardScaler

# ==========================================
# CÔNG TẮC NGUỒN CẤP DỮ LIỆU (SOURCE TOGGLE)
# ==========================================
USE_MT5_DATA = True  # (False = Binance | True = MT5)

# Đọc config để lấy target
import sys
import json
_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config_path = os.path.join(_root_dir, "data", "bot_config.json")
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.endswith('.json'):
            config_path = arg

config = {}
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        TARGET_PREFIX = config.get("TARGET_PREFIX", "XAU_USD")
        CONFIG_ID = config.get("CONFIG_ID", TARGET_PREFIX)
else:
    TARGET_PREFIX = "XAU_USD"
    CONFIG_ID = "XAU_USD"

def add_time_embeddings(df):
    """
    Thêm đặc tính lượng giác (sin/cos) của Giờ và Ngày vào DataFrame.
    Giúp Neural Network hiểu Khái niệm vòng lặp (vd: 23h và 00h liền kề nhau).
    """
    hour = df.index.hour
    dayofweek = df.index.dayofweek
    
    df['hour_sin'] = np.sin(2 * np.pi * hour / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * hour / 24.0)
    df['dow_sin'] = np.sin(2 * np.pi * dayofweek / 7.0)
    df['dow_cos'] = np.cos(2 * np.pi * dayofweek / 7.0)
    return df

def load_and_align_data(data_path):
    print("1. Đang gộp toàn bộ dữ liệu & CHUẨN HOÁ MÚI GIỜ (Timezone Alignment)...")
    
    if USE_MT5_DATA:
        print(">> Chế độ: ĐANG ĐỌC NGUỒN DỮ LIỆU MT5 TỔNG HỢP <<")
        files = [f for f in os.listdir(data_path) if f.endswith('.parquet') and 'usdt' not in f.lower() and 'target_' not in f.lower() and 'final_' not in f.lower()]
        
        # Nếu đang train/trade XAUUSD, dọn dẹp các mã gây nhiễu và ÉP NGHIÊM NGẶT dùng list của LIVE
        mt5_symbols = config.get("MT5_SYMBOLS", [])
        if not mt5_symbols:
            mt5_symbols = list(config.get("DATA_SOURCE", {}).get("ROUTING", {}).keys())
            
        dataset_suffix = config.get("DATA_SOURCE", {}).get("DATASET_SUFFIX", "")
        if dataset_suffix:
            print(f"🎯 Lọc chính xác file theo Date Suffix: {dataset_suffix}")
            files = [f for f in files if dataset_suffix in f]

        if mt5_symbols:
            filtered_files = []
            print(f"🔄 Đang map danh sách LIVE MT5 ({len(mt5_symbols)} mã) vào Kho Dữ Liệu Lịch Sử...")
            for sym in mt5_symbols:
                sym_clean = sym.upper().replace('M', '').replace('_', '')
                
                matched = None
                for f in files:
                    if '_MT5_1M_' in f.upper():
                        f_clean = f.upper().split('_MT5_1M_')[0].replace('_', '')
                    else:
                        f_clean = f.upper().replace('_MT5', '').replace('_1M', '').replace('_2025', '').replace('_2026', '').replace('.PARQUET', '').replace('_', '')
                    if sym_clean == f_clean or f_clean in sym_clean:
                        matched = f
                        break
                        
                if matched and matched not in filtered_files:
                    filtered_files.append(matched)
                    print(f"  + Ánh xạ {sym} -> {matched}")
                else:
                    print(f"  ⚠️ CẢNH BÁO: Không có nguồn {sym} ở Local!")
                    
            files = filtered_files
            print(f"✅ Đã Khớp Cấu Hình LIVE! Giữ lại {len(files)} files chuẩn MT5 để huấn luyện.")
        elif 'XAU' in TARGET_PREFIX.upper():
            useless_features = ['btc', 'eth', 'sol', 'xrp', 'ada', 'bnb', 'bch', 'ltc', 'usdjpy', 'jp225', 'us30', 'dxy']
            filtered_files = []
            for f in files:
                f_lower = f.lower()
                is_useless = any(u in f_lower for u in useless_features)
                if not is_useless:
                    filtered_files.append(f)
                else:
                    print(f"🗑️ Đã gạt bỏ nhiễu {f}")
            files = filtered_files
            print(f"✅ Số lượng Features (Files) được giữ lại gốc cho Vàng: {len(files)}")
    else:
        print(">> Chế độ: ĐANG ĐỌC NGUỒN DỮ LIỆU BINANCE (CCXT) <<")
        files = [f for f in os.listdir(data_path) if f.endswith('_usdt_1m_2025_2026.parquet')]
        
    df_list = []
    for file in files:
        if '_mt5_1m_' in file.lower():
            raw_sym = file.lower().split('_mt5_1m_')[0].upper()
        else:
            raw_sym = file.replace('_1m_2025_2026.parquet', '').upper()
            
        symbol = raw_sym    
        if raw_sym == TARGET_PREFIX.replace('_', ''):
            symbol = TARGET_PREFIX
        else:
            exacts = config.get('FEATURE_ENGINEERING', {}).get('EXACT_FEATURES', [])
            for f in exacts:
                if f.startswith(raw_sym + '_USD_'):
                    symbol = raw_sym + '_USD'
                    break
                elif f.startswith(raw_sym.replace('USD', '_USD') + '_'):
                    symbol = raw_sym.replace('USD', '_USD')
                    break
        if 'YIELD' in raw_sym: symbol = 'US_10Y_YIELD'
        elif 'NASDAQ' in raw_sym: symbol = 'NASDAQ_100'
        elif 'USTEC' in raw_sym: symbol = 'USTEC'

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
    
    # Rất quan trọng: Phải sort Index theo thời gian trước
    merged_df.sort_index(inplace=True)
    
    # 🌟 GỌT NẾN MA (GHOST CANDLE FIX): Lấy TARGET_PREFIX làm Xương Sống 🌟
    # Tập hợp các mã Tỉ Giá và Chỉ số vào Trục Thước Đo Chuẩn Của Target.
    xau_usd_col = [c for c in merged_df.columns if f'{TARGET_PREFIX}_close' in c]
    if xau_usd_col:
        xau_usd_series = merged_df[xau_usd_col[0]].dropna()
        merged_df = merged_df.loc[xau_usd_series.index]
        
    # -------------------------------------------------------------
    # CHIẾN LƯỢC ĐIỀN KHUYẾT ĐA HỆ DANH (IMPUTATION)
    # -------------------------------------------------------------
    # 1. Với Giá trị (Price) và Macro 1H: Bơm kế thừa mốc giá gần nhất (ffill) với GIỚI HẠN chặt chẽ 120 phút.
    fill_limit = config.get("FEATURE_ENGINEERING", {}).get("FILL_LIMIT", 120)
    merged_df.ffill(limit=fill_limit, inplace=True)

    # 2. Với Cột Thanh Khoản (Volume/Tick_Volume): Lấp bằng 0 (Thị trường đóng băng/Khớp lệnh = 0)
    vol_cols = [c for c in merged_df.columns if 'volume' in c.lower()]
    merged_df[vol_cols] = merged_df[vol_cols].fillna(0)
    
    # -------------------------------------------------------------
    
    # 🔥 BỘ LỌC TOÀN VẸN DỮ LIỆU (DATA INTEGRITY: MISSING TOLERANCE) 🔥
    missing_ratio = merged_df.isna().sum(axis=1) / len(merged_df.columns)
    
    # Huỷ diệt (Drop) ngay lập tức các cây nến có dữ liệu khuyết rách trên 15%
    MISSING_TOLERANCE = 0.15
    invalid_rows = missing_ratio > MISSING_TOLERANCE
    num_ghost_candles = invalid_rows.sum()
    merged_df = merged_df[~invalid_rows]
    missing_ratio = missing_ratio[~invalid_rows]
    
    print(f"   [DATA INTEGRITY] Đã phát hiện và tiêu huỷ {num_ghost_candles:,} Cây Nến Ma (Thiếu > {MISSING_TOLERANCE*100:.0f}% dữ liệu Vĩ mô).")
    
    # Tạo Cờ Vàng (Flag) để theo dõi Tỷ lệ Nến Ma theo Cửa Sổ Bề Ngang
    merged_df['is_imputed_flag'] = (missing_ratio > 0).astype(int)
    
    # Dọn dẹp nốt cặn bã nếu lấp 120 phút vẫn không kín (Nghĩa là có tài sản bị đứt Mạng luới > 2 tiếng)
    final_drop_count = merged_df.isna().any(axis=1).sum()
    merged_df.dropna(inplace=True)
    print(f"   [DATA INTEGRITY] Đã loại bỏ thêm {final_drop_count:,} Cây Nến bị đứt gãy dữ liệu kéo dài (>2 giờ).")
    
    # 🔥 MỞ RỘNG LỊCH SỬ DATA về 2024 🔥
    merged_df = merged_df[merged_df.index >= '2024-01-01']
    print(f"-> Khối lượng Nến Training hợp lệ còn lại: {len(merged_df):,} Nến (Từ 2024).")
    
    # 🌟 ĐỒNG BỘ THEO MÚI GIỜ CHUẨN MỸ 🌟
    merged_df.index = merged_df.index.tz_convert('America/New_York')
    
    print("-> Data Unlocked: Gộp Trọn Vẹn Giai Đoạn 2025-2026 (Full History)...")
    
    # --- THỦ TỤC TIME EMBEDDING (Học Hành Vi Múi Giờ Châu Lục) ---
    merged_df = add_time_embeddings(merged_df)
    
    # Rụng bỏ những ngày đầu tiên bị NaN do các mã lệch ngày xuất phát (MT5 vs Binance)
    merged_df.dropna(inplace=True)
    
    print(f"-> HOÀN TẤT GỘP: Ma trận Dữ liệu Full-Time ôm trọn {merged_df.shape[0]:,} dòng x {merged_df.shape[1]} cột tính năng.")
    return merged_df

import joblib

def create_stationary_features(df, is_live=False):
    print("2. Chuyển đổi dữ liệu sang dạng dừng (Stationary) bằng Log Returns & Đúc T.A cho XAUUSD...")
    new_features = {}
    
    # Tách is_imputed_flag để không bị scale
    imputed_flags = df['is_imputed_flag'].copy() if 'is_imputed_flag' in df.columns else pd.Series(0, index=df.index)
    if 'is_imputed_flag' in df.columns:
        df = df.drop(columns=['is_imputed_flag'])
        
    # [GIÁC QUAN ĐẶC BIỆT]: Tính toán Chỉ báo Điểm chạm của XAUUSD
    if f'{TARGET_PREFIX}_close' in df.columns:
        # 1. Đo lường sức mạnh giá (RSI động từ Config)
        rsi_periods = config.get("FEATURE_ENGINEERING", {}).get("RSI_PERIODS", [14])
        delta = df[f'{TARGET_PREFIX}_close'].diff()
        for p in rsi_periods:
            gain = (delta.where(delta > 0, 0)).rolling(window=p).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=p).mean()
            rs = gain / (loss + 1e-9)
            name = f'{TARGET_PREFIX}_RSI' if len(rsi_periods) == 1 and p == 14 else f'{TARGET_PREFIX}_RSI_{p}'
            new_features[name] = 100 - (100 / (1 + rs))
        
        # 2. Đo lường sức mạnh Xu Hướng mượt (EMA động từ config)
        ema_periods = config.get("FEATURE_ENGINEERING", {}).get("EMA_PERIODS", [9, 21])
        for p in ema_periods:
            new_features[f'{TARGET_PREFIX}_EMA{p}_dist'] = np.log(df[f'{TARGET_PREFIX}_close'] / df[f'{TARGET_PREFIX}_close'].ewm(span=p, adjust=False).mean())
        
        # 3. Phân tách Cấu trúc Râu Nến và Thân Nến Cổ Điển (Nhận diện PinBar, Doji)
        if all(k in df.columns for k in [f'{TARGET_PREFIX}_open', f'{TARGET_PREFIX}_high', f'{TARGET_PREFIX}_low']):
            new_features[f'{TARGET_PREFIX}_Body'] = np.log(df[f'{TARGET_PREFIX}_close'] / df[f'{TARGET_PREFIX}_open'].replace(0, np.nan))
            new_features[f'{TARGET_PREFIX}_Upper_Shadow'] = np.log(df[f'{TARGET_PREFIX}_high'] / df[[f'{TARGET_PREFIX}_open', f'{TARGET_PREFIX}_close']].max(axis=1).replace(0, np.nan))
            new_features[f'{TARGET_PREFIX}_Lower_Shadow'] = np.log(df[[f'{TARGET_PREFIX}_open', f'{TARGET_PREFIX}_close']].min(axis=1) / df[f'{TARGET_PREFIX}_low'].replace(0, np.nan))
        
        # 4. [MỚI] MULTI-HORIZON RETURN FEATURES - Đo Quán Tính Giá Đa Khung
        for horizon in [5, 10, 30]:
            past_close = df[f'{TARGET_PREFIX}_close'].shift(horizon).replace(0, np.nan)
            new_features[f'{TARGET_PREFIX}_ret_{horizon}m'] = np.log(df[f'{TARGET_PREFIX}_close'] / past_close)
        
        # 5. [MỚI] ATR RATIO - Tỷ lệ biến động Hiện Tại so với Trung bình 60p
        if all(k in df.columns for k in [f'{TARGET_PREFIX}_high', f'{TARGET_PREFIX}_low']):
            curr_range = df[f'{TARGET_PREFIX}_high'] - df[f'{TARGET_PREFIX}_low']
            avg_range = curr_range.rolling(60).mean()
            new_features[f'{TARGET_PREFIX}_ATR_ratio'] = curr_range / (avg_range + 1e-9)

    for col in df.columns:
        if col in ['hour_sin', 'hour_cos', 'dow_sin', 'dow_cos']:
            new_features[col] = df[col]
        elif 'volume' in col.lower() or 'spread' in col.lower():
            new_features[col] = np.log1p(df[col].fillna(0))
        else:
            shifted_col = df[col].shift(1).replace(0, np.nan)
            new_features[f"{col}_log_ret"] = np.log(df[col] / shifted_col)
            
    # Xây dựng DataFrame một lần ở cuối (Chống Phân Mảnh / Fragmentation)
    feature_df = pd.DataFrame(new_features, index=df.index)
            
    # Loại bỏ các giá trị Inf do phép chia sinh ra và các hàng NaN
    feature_df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # 🛡️ CHỈ DROPNA THEO TARGET: Cắt bỏ phần đầu NaN do EMA/RSI rolling của XAUUSD
    # Không cho phép 1 mã Macro thiếu nến kéo sập toàn bộ Cây XAUUSD!
    target_cols = [c for c in feature_df.columns if c.startswith(TARGET_PREFIX)]
    if target_cols:
        feature_df.dropna(subset=target_cols, inplace=True)
    else:
        feature_df.dropna(inplace=True)
        
    # Lấp toàn bộ NaNs còn sót lại của Macro bằng 0.0 (Zero-Pad các mã thiếu nến cục bộ)
    feature_df.fillna(0.0, inplace=True)

    # --- [EXACT SHIELD] GỌT TENSOR ĐẦU VÀO Y NHƯ CẤU HÌNH ---
    exact_features = config.get("FEATURE_ENGINEERING", {}).get("EXACT_FEATURES", [])
    if exact_features:
        missing_cols = [c for c in exact_features if c not in feature_df.columns]
        if missing_cols:
            print(f"⚠️ [EXACT SHIELD] Cảnh báo: Thiếu {len(missing_cols)} Features từ danh sách yêu cầu (VD: {missing_cols[:5]}). Đang Zero-Pad...")
            pad_df = pd.DataFrame(0.0, index=feature_df.index, columns=missing_cols)
            feature_df = pd.concat([feature_df, pad_df], axis=1)
            
        extra_cols = [c for c in feature_df.columns if c not in exact_features]
        if extra_cols:
            print(f"🛡️ [EXACT SHIELD] Loại bỏ {len(extra_cols)} Features nhiễu không có trong cấu hình EXACT_FEATURES (VD: {extra_cols[:5]}).")
            
        # Sắp xếp và Gọt đúng kích thước Tensor
        feature_df = feature_df[exact_features]
    
    # Scale tất cả thành Mean=0, Std=1 để đẩy lưới Nơ-ron chạy hội tụ siêu tốc
    # KHOÁ LÕI SCALER (TRÁNH LỆCH PHA GIỮA TRAIN VÀ LIVE)
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(script_dir, "data")
    
    if is_live:
        scaler = joblib.load(os.path.join(data_path, f'scaler_{CONFIG_ID}.pkl'))
        
        # --- [AUTO-ALIGN SHIELD] TỰ ĐỘNG CHUẨN HOÁ CỘT (CHỐNG CRASH) ---
        expected_cols = list(scaler.feature_names_in_)
        missing_cols = [c for c in expected_cols if c not in feature_df.columns]
        if missing_cols:
            print(f"⚠️ [SHIELD] Cảnh báo: Thiếu {len(missing_cols)} Features từ MT5 (vd: {missing_cols[:5]}). Đang Zero-Pad...")
            pad_df = pd.DataFrame(0.0, index=feature_df.index, columns=missing_cols)
            feature_df = pd.concat([feature_df, pad_df], axis=1)
            
        extra_cols = [c for c in feature_df.columns if c not in expected_cols]
        if extra_cols:
            print(f"⚠️ [SHIELD] Cảnh báo: Thừa {len(extra_cols)} Features rác từ MT5 (vd: {extra_cols[:5]}). Đang tự động ném bỏ...")
            
        feature_df = feature_df[expected_cols]
        
        scaled_data = scaler.transform(feature_df)
    else:
        print(f"-> [TRAIN MODE] Đang tính toán Độ Lệch Chuẩn 15 Tháng và Đúc scaler_{CONFIG_ID}.pkl...")
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(feature_df)
        joblib.dump(scaler, os.path.join(data_path, f'scaler_{CONFIG_ID}.pkl'))
        
    scaled_df = pd.DataFrame(scaled_data, index=feature_df.index, columns=feature_df.columns)
    
    # [DUAL-STREAM METADATA] Đếm và lưu số lượng Feature thuộc mục tiêu để Model biết cách tách luồng
    xau_cols = [c for c in scaled_df.columns if c.startswith(TARGET_PREFIX)]
    num_xau_features = len(xau_cols)
    
    # Chèn cờ báo hiệu nến lắp ghép lại vào Dataset cuối
    scaled_df['is_imputed_flag'] = imputed_flags.loc[scaled_df.index]
    
    # Sắp xếp lại cột: XAU features đứng TRƯỚC để Model slice dễ dàng
    other_cols = [c for c in scaled_df.columns if not c.startswith(TARGET_PREFIX) and c != 'is_imputed_flag']
    scaled_df = scaled_df[xau_cols + other_cols + ['is_imputed_flag']]
    
    # Lưu metadata ra JSON để train_final.py đọc
    import json
    meta_path = os.path.join(data_path, f"feature_meta_{CONFIG_ID}.json")
    with open(meta_path, "w") as f:
        json.dump({
            "num_xau_features": num_xau_features, 
            "total_features": len(scaled_df.columns),
            "target_prefix": TARGET_PREFIX,
            "config_id": CONFIG_ID
        }, f)
    
    print(f"-> Hoàn tất Stationarity & Scaling. Kích thước Tensor: {scaled_df.shape}")
    print(f"-> [DUAL-STREAM] XAU Features: {num_xau_features} | Macro Features: {len(other_cols)}")
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
    
    _root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(_root_dir, "data")
    
    # 1. Gộp toàn bộ Data
    merged_df = load_and_align_data(data_path)
    
    # Lưu giá Close của VÀNG (XAU) làm Cột Mục tiêu Chỉ Lối (Target)
    xau_usd_close = merged_df[f'{TARGET_PREFIX}_close']
    
    # 2. Xử lý tính năng tĩnh (Stationary Log Returns & Scaling)
    scaled_features, scaler = create_stationary_features(merged_df, is_live=is_live)
    
    # Cân bằng index do hàm tạo Log Return làm mất 1 dòng đầu tiên
    target_aligned = xau_usd_close.loc[scaled_features.index]
    
    print("3. Khởi tạo Target Momentum T+5 (Close[T+5] > Close[T])...")
    lookahead_minutes = 5
    
    # [LIVE MODE FIX]
    if is_live:
        final_features = scaled_features
    else:
        # [A] XỬ LÝ TARGET TRÁNH SIDEWAYS (LỌC NHIỄU)
        # Thay vì bắt AI đoán bừa khi giá chỉ nhích thêm 0.00001, ta Xoá Bỏ các cây nến Đi Ngang
        future_close = xau_usd_close.shift(-lookahead_minutes)
        pct_change = (future_close / xau_usd_close) - 1.0
        
        # Ngưỡng biến động (Tối thiểu 0.02% để coi là xu hướng)
        MIN_MOVE_PCT = 0.0002
        valid_trend_mask = pct_change.abs() > MIN_MOVE_PCT
        
        raw_labels = (future_close > xau_usd_close).astype(float)
        # Gán NaN cho nến vô hướng để thả rơi, giúp AI không học Rác (Noise Bias)
        raw_labels[~valid_trend_mask] = np.nan

        target_direction = raw_labels.loc[scaled_features.index].copy()
        valid_mask = target_direction.notna()
        target_direction = target_direction[valid_mask]
        final_features = scaled_features.loc[target_direction.index]
        
        n_buy = (target_direction == 1).sum()
        n_sell = (target_direction == 0).sum()
        print(f"-> [Momentum Label T+5] Tổng: {len(target_direction):,} | BUY: {n_buy:,} ({n_buy/len(target_direction)*100:.1f}%) | SELL: {n_sell:,} ({n_sell/len(target_direction)*100:.1f}%)")
        
        target_direction.to_frame(name='target').to_parquet(os.path.join(data_path, f"target_direction_{CONFIG_ID}.parquet"))
    
    print(f"-> Dữ liệu Input cuối cùng: {final_features.shape}")
    if is_live:
        final_features.to_parquet(os.path.join(data_path, f"live_features_{CONFIG_ID}.parquet"))
        print(f"\n[OK] Feature Engineering (LIVE) hoàn tất! Sẵn sàng báo tín hiệu.")
    else:
        final_features.to_parquet(os.path.join(data_path, f"final_features_{CONFIG_ID}.parquet"))
        print(f"\n[OK] Feature Engineering (TRAIN) hoàn tất! Chuyển qua huấn luyện.")


