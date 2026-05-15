import os
import re

filepath = r'd:\DungLA\client1\src\bot_v6\data_processor_v6.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add a print statement before the rename check
print_code = '''                corr_col_name = f"{target_prefix}_target_corr_60"
                self.log_callback(f"DEBUG: corr_col_name={corr_col_name}, df_tf_feat columns: {df_tf_feat.columns.tolist()}")'''

content = content.replace('                corr_col_name = f"{target_prefix}_target_corr_60"', print_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
