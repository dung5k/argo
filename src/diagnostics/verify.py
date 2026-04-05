import pandas as pd

df = pd.read_parquet('btc_usdt_1m_2026.parquet')
print('\n--- MẪU DỮ LIỆU ĐẦU TIÊN ---')
print(df.head(3))

print('\n--- MẪU DỮ LIỆU CUỐI CÙNG ---')
print(df.tail(3))

print('\n--- KIỂM TRA BƯỚC THỜI GIAN ---')
time_diffs = df.index.to_series().diff().dt.total_seconds().dropna()
unique_diffs = time_diffs.unique()

print(f"Các khoảng thời gian đo được (giây): {unique_diffs}")
print(f"Tổng số nến (candle): {len(df):,}")

if len(unique_diffs) == 1 and unique_diffs[0] == 60.0:
    print("-> DATA VALID: Tất cả các nến đều chênh nhau chính xác 1 phút (60s). Không bị thiếu nến.")
else:
    print("-> WARNING: Có bước nhảy thời gian bất thường (Khả năng sàn bảo trì hoặc mất kết nối trong chốc lát).")
    
    # In ra số lượng các bước nhảy khác
    print(time_diffs.value_counts())
