import MetaTrader5 as mt5
import time

def get_crypto_from_terminal(path, name):
    print(f"\n[{name}] Đang kết nối vào: {path}")
    if not mt5.initialize(path=path):
        print(f"Lỗi: Không thể kết nối {name}. Có thể terminal đang bận (Error code: {mt5.last_error()})")
        return []
        
    symbols = mt5.symbols_get()
    if symbols is None:
        print(f"Không lấy được danh sách lệnh từ {name}")
        mt5.shutdown()
        return []
        
    crypto_list = []
    for s in symbols:
        p = getattr(s, 'path', '').upper()
        d = getattr(s, 'description', '').upper()
        n = getattr(s, 'name', '').upper()
        
        is_crypto = False
        if "CRYPTO" in p or "BITCOIN" in p:
            is_crypto = True
        elif "USDT" in n and "UST" not in n:  
            is_crypto = True
        elif "CRYPTO" in d or "BITCOIN" in d or "ETHEREUM" in d:
            is_crypto = True
            
        if is_crypto:
            crypto_list.append(f" - {s.name:<15} | [{p}] {s.description}")
                
    mt5.shutdown()
    
    crypto_list = sorted(list(set(crypto_list)))
    print(f">> Tìm thấy {len(crypto_list)} mã Crypto trên {name}.\n")
    return crypto_list

if __name__ == "__main__":
    t_exness = get_crypto_from_terminal(r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe", "MT5 - Exness")
    
    with open("crypto_sources_exness.txt", "w", encoding="utf-8") as f:
        f.write("=== DANH SÁCH TIỀN MÃ HÓA TỪ MT5 EXNESS ===\n")
        f.write("\n".join(t_exness) if t_exness else "Không tìm thấy hoặc không kết nối được.")
    
    print("Hoàn tất! Đã ghi kết quả vào crypto_sources_exness.txt")
