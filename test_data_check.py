import pandas as pd
import os
import json

data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'
print("=== DATA DIR FILES ===")
for f in sorted(os.listdir(data_dir)):
    fpath = os.path.join(data_dir, f)
    size = os.path.getsize(fpath)
    print(f' [{size//1024}KB] {f}')
