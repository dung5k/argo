import re

with open('src/core/trade_mt5.py', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r"if len\(valid_cols\) == len\(active_inference_feats\):.*?continue"

replacement = """if len(valid_cols) == len(active_inference_feats):
                        last_60_candles = df[valid_cols].iloc[-window_size:].values
                    else:
                        gui_status = "Đã bù 0 cho Sàn"
                        missing_feats = [c for c in active_inference_feats if c not in df.columns]
                        for c in missing_feats:
                            df[c] = 0.0
                        if 'is_imputed_flag' in df.columns:
                            df['is_imputed_flag'] = 1.0
                        last_60_candles = df[active_inference_feats].iloc[-window_size:].values"""

new_text = re.sub(pattern, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('src/core/trade_mt5.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("PATCHED LOOP")
else:
    print("NO CHANGE")
