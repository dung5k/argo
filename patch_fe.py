import os
import re

filepath = r'd:\DungLA\client1\src\core_v3\feature_engineering_v3.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('cols = {c.lower(): c for c in df.columns}', 'cols = {c.lower(): c for c in df.columns}\n        print(f"[DEBUG FE] target_prefix={self.target_prefix}, cols={list(cols.keys())}")')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
