import os
import re

filepath = r'd:\DungLA\client1\src\bot_v6\bot_v6.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the force_reload call
old_code = '''                # MT5 manager chỉ cần feature names (strings) để cào data, dùng i_feats gốc
                mt5_manager.force_reload_dynamic_features(i_feats)'''

new_code = '''                # V6 MT5 manager needs ALL features across all MTF
                all_feats = []
                for co in processor.column_orders:
                    all_feats.extend(co)
                mt5_manager.force_reload_dynamic_features(list(set(all_feats)))'''

content = content.replace(old_code, new_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
