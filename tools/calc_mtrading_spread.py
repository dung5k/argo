import MetaTrader5 as mt5
import pandas as pd
import time
import os

t_name = "MT5 Mtrading"
t_path = r"C:\Program Files\Mtrading MetaTrader 5\terminal64.exe"

results = []

def is_valid_group(path):
    if not path: return False
    p = path.lower()
    if "stock" in p or "share" in p or "equity" in p: return False
    
    valid_keywords = ["forex", "crypto", "metals", "energies", "indices", "commodities", "bonds", "cfd"]
    for k in valid_keywords:
        if k in p: return True
    return False

print("="*60)
print("🚀 HỆ THỐNG QUÉT SPREAD NÂNG CAO (1 NGÀY NẾN 5 PHÚT)")
print("="*60)

print(f"\n[🔄] Đang kết nối: {t_name} ({t_path})...")
if not mt5.initialize(path=t_path):
    print(f"  ❌ Không thể kết nối hoặc MT5 chưa mở.")
    exit(1)
    
symbols = mt5.symbols_get()
if not symbols:
    print("  ❌ Không lấy được mã giao dịch.")
    mt5.shutdown()
    exit(1)

filtered_symbols = [s for s in symbols if is_valid_group(s.path)]
total = len(filtered_symbols)

print(f"  ✅ Đã tìm thấy {total} mã tiềm năng (Đã lọc bỏ Cổ phiếu rác).")

count = 0
valid_count = 0
t_start = time.time()
for s in filtered_symbols:
    count += 1
    # 1 NGÀY nến 5 Phút = 1 * 24 * 60 / 5 = 288 nến
    rates = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M5, 0, 288)
    if rates is None or len(rates) < 100:
        continue
        
    df = pd.DataFrame(rates)
    df['height'] = df['high'] - df['low']
    df['spread_price'] = df['spread'] * s.point
    
    valid = df[df['height'] > 0].copy()
    if len(valid) < 50: 
        continue
    
    valid['ratio'] = valid['spread_price'] / valid['height']
    avg_ratio = valid['ratio'].mean() * 100 
    
    group = s.path.split('\\')[0] if s.path else "Other"
    
    results.append({
        'Sàn MT5': t_name,
        'Nhóm': group,
        'Mã Giao Dịch': s.name,
        'Spread / Nến 5M (%)': round(avg_ratio, 2)
    })
    valid_count += 1
    if count % 20 == 0:
        print(f"  Đang quét: {count}/{total} mã | Thời gian: {round(time.time() - t_start, 1)}s")

print(f"\n  ✨ Hoàn tất {t_name} - Lấy được {valid_count} mã có thanh khoản thật.")
mt5.shutdown()

df_res = pd.DataFrame(results)
if not df_res.empty:
    df_res = df_res.sort_values(by='Spread / Nến 5M (%)', ascending=True)
    
    csv_path = os.path.abspath("spread_analysis_mtrading.csv")
    df_res.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    print("\n" + "="*70)
    print("🏆 BẢNG VÀNG: TOP 30 MÃ GIAO DỊCH TỐT NHẤT THẾ GIỚI CHO SCALPING M5")
    print("="*70)
    print(df_res.head(30).to_string(index=False))
    
    print("\n" + "="*70)
    print("☠️ CÁO PHÓ: TOP 15 MÃ LÀ TỬ HUYỆT (CẤM SCALP VÌ SPREAD QUÁ TO)")
    print("="*70)
    if len(df_res) > 30:
        print(df_res.tail(15).to_string(index=False))
else:
    print("\n❌ Không lấy được dữ liệu thanh khoản nào.")
