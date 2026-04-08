import re

pattern = r"if len\(valid_cols\) < len\(active_inference_feats\):.*?return"

replacement = """if len(valid_cols) < len(active_inference_feats):
            missing_feats = [c for c in active_inference_feats if c not in df_feats.columns]
            print(f" \u26A0\uFE0F CẢNH BÁO LỰC: Thiếu {len(missing_feats)} Features! Tự động bù 0.0 do Sàn vắng mặt.", flush=True)
            for c in missing_feats:
                df_feats[c] = 0.0
            if 'is_imputed_flag' in df_feats.columns:
                df_feats['is_imputed_flag'] = 1.0 # Đánh cờ cho model
            valid_cols = active_inference_feats
            lbl_session.config(text=f"Thiếu {len(missing_feats)} Sensor (Đã bù 0)", fg="#ffcc00")
        else:
            if 'is_imputed_flag' in df_feats.columns:
                df_feats['is_imputed_flag'] = 0.0"""

with open('src/core/trade_mt5.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_text = re.sub(pattern, replacement, text, flags=re.DOTALL)

with open('src/core/trade_mt5.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("PATCH APPLIED SUCCESSFULLY")
