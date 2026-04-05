import MetaTrader5 as mt5

def check_symbols_with_desc():
    MT5_MAIN_PATH = r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe"
    print(f"Đang khởi động kết nối vào MT5 tại {MT5_MAIN_PATH}...")
    
    if not mt5.initialize(path=MT5_MAIN_PATH):
        print("Lỗi: Khởi tạo thư viện MetaTrader5 thất bại!")
        print(f"Error code: {mt5.last_error()}")
        return
        
    symbols = mt5.symbols_get()
    if symbols is None:
        print("Không thể lấy danh sách symbol.")
        mt5.shutdown()
        return
        
    # Search for VIX or US10 terms
    keywords = ["VIX", "US10", "10Y", "YIELD", "TNX", "S10", "BOND", "TREASURY"]
    
    found = []
    for s in symbols:
        name = s.name.upper()
        desc = s.description.upper()
        for kw in keywords:
            if kw in name or kw in desc:
                found.append(f" - {name}: {desc}")
                break
                
    with open("symbols_out_2.txt", "w", encoding="utf-8") as f:
        f.write(f"Các symbol liên quan VIX/US10Y trên MT5-2 ({len(symbols)} tổng cộng):\n")
        if not found:
            f.write("Không tìm thấy symbol nào.\n")
        else:
            for line in sorted(list(set(found))):
                f.write(line + "\n")
                
    print("Hoàn tất tìm kiếm. Đã ghi kết quả vào symbols_out_2.txt")
    mt5.shutdown()

if __name__ == "__main__":
    check_symbols_with_desc()
