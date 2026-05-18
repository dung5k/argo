import re
import os

workspaces = ['CFG_LTC_ASIAN_V6', 'CFG_LTC_LONDON_V6', 'CFG_LTC_NY_V6', 'CFG_LTC_WEEKEND_V6']
base_dir = r'd:\DungLA\client1\workspaces'

for w in workspaces:
    diary_path = os.path.join(base_dir, w, f'{w.replace("CFG_LTC_", "")}_DIARY.md')
    if os.path.exists(diary_path):
        with open(diary_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            matches = re.findall(r'Win Rate.*?([\d\.]+)%', content, re.IGNORECASE)
            matches += re.findall(r'WR.*?([\d\.]+)%', content, re.IGNORECASE)
            matches += re.findall(r'([\d\.]+)%\s*Win Rate', content, re.IGNORECASE)
            
            floats = []
            for m in matches:
                try:
                    f_val = float(m)
                    if f_val <= 100:
                        floats.append(f_val)
                except:
                    pass
            best = max(floats) if floats else 0
            print(f'{w}: Best Win Rate found is {best}%')
    else:
        print(f'{w}: Diary not found at {diary_path}')
