import os
import pandas as pd
from datetime import timedelta

def prepare_v8_data_local():
    print("Loading M1 Data from 2021 to 2026...")
    df = pd.read_parquet("data/XAUUSDm_M1_2021_2026.parquet")
    
    df_session = df.copy()
    print(f"Total rows (keeping 24/7 continuous sequence): {len(df_session)}")
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "v8_splits"))
    os.makedirs(out_dir, exist_ok=True)
    
    # Clean up old splits
    for f in os.listdir(out_dir):
        if f.endswith('.parquet'):
            os.remove(os.path.join(out_dir, f))
            
    min_date = df_session.index.min()
    max_date = df_session.index.max()
    
    current_start = min_date
    split_id = 1
    
    print("Generating 48-week Train / 12-week Test splits from M1 Data...")
    while current_start + timedelta(weeks=60) <= max_date:
        train_end = current_start + timedelta(weeks=48)
        test_end = train_end + timedelta(weeks=12)
        
        train_df = df_session[(df_session.index >= current_start) & (df_session.index < train_end)]
        test_df = df_session[(df_session.index >= train_end) & (df_session.index < test_end)]
        
        if len(train_df) > 0 and len(test_df) > 0:
            train_df.to_parquet(os.path.join(out_dir, f"split_{split_id}_train.parquet"))
            test_df.to_parquet(os.path.join(out_dir, f"split_{split_id}_test.parquet"))
            
        current_start += timedelta(weeks=12) # Walk-forward cuộn lên 12 tuần
        split_id += 1
        
    print(f"Generated {split_id-1} splits successfully in {out_dir}")

if __name__ == "__main__":
    prepare_v8_data_local()
