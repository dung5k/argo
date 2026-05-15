import sys
import os
import time
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '.agent'))
try:
    import send_to_tele
except ImportError:
    pass

def check_mt5():
    # 1. Khởi tạo kết nối MT5
    mt5_path = r"D:\mt5\MetaTrader 5 EXNESS\terminal64.exe"
    if not os.path.exists(mt5_path):
        mt5_path = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
        
    if not mt5.initialize(path=mt5_path):
        msg = f"❌ Không thể kết nối đến phần mềm MT5 tại đường dẫn: {mt5_path}"
        send_to_tele.send_to_telegram(msg, is_done=True, target_channels='1816854047')
        return

    # 2. Lấy dữ liệu 2 ngày gần nhất (May 8 - May 9)
    now = datetime.now()
    yesterday = now - timedelta(days=2)
    
    # Lấy history deals (lệnh đã đóng)
    deals = mt5.history_deals_get(yesterday, now)
    
    # Lấy open positions (lệnh đang mở)
    positions = mt5.positions_get()
    
    report = "📊 BÁO CÁO LỊCH SỬ GIAO DỊCH TRỰC TIẾP TỪ MT5 (08/05 - 09/05)\n\n"
    
    # Phân tích lệnh đã đóng
    xag_deals = []
    ltc_deals = []
    total_pnl = 0.0
    
    if deals is None:
        report += "⚠️ Không lấy được lịch sử lệnh đã đóng (Deals).\n"
    elif len(deals) > 0:
        for deal in deals:
            # deal.entry == 1 (DEAL_ENTRY_OUT) nghĩa là lệnh đóng vị thế (có lợi nhuận/lỗ)
            if deal.entry == 1:
                symbol = deal.symbol
                profit = deal.profit
                time_str = datetime.fromtimestamp(deal.time).strftime('%d/%m %H:%M')
                order_type = "BÁN" if deal.type == mt5.ORDER_TYPE_SELL else "MUA"
                total_pnl += profit
                
                info = f"[{time_str}] {order_type} {symbol}: {profit:+.2f}$"
                if 'XAG' in symbol.upper():
                    xag_deals.append(info)
                elif 'LTC' in symbol.upper():
                    ltc_deals.append(info)
    
    # Thống kê XAG
    report += f"🥈 BOT XAG (Bạc) - Tổng {len(xag_deals)} lệnh đã đóng:\n"
    if xag_deals:
        report += "\n".join(xag_deals[-10:]) + ("\n...(và nhiều lệnh khác)" if len(xag_deals)>10 else "")
    else:
        report += "Không có lệnh nào.\n"
        
    report += "\n"
    # Thống kê LTC
    report += f"🪙 BOT LTC (Litecoin) - Tổng {len(ltc_deals)} lệnh đã đóng:\n"
    if ltc_deals:
        report += "\n".join(ltc_deals[-10:]) + ("\n...(và nhiều lệnh khác)" if len(ltc_deals)>10 else "")
    else:
        report += "Không có lệnh nào.\n"
        
    report += f"\n💰 Tổng Lãi/Lỗ thực tế (Closed): {total_pnl:+.2f}$\n\n"
    
    # Phân tích lệnh đang mở
    report += "--------------------\n"
    report += "🟢 CÁC LỆNH ĐANG MỞ (OPEN POSITIONS):\n"
    if positions is None or len(positions) == 0:
        report += "Không có lệnh nào đang giữ trên MT5 (All Flat)."
    else:
        for pos in positions:
            symbol = pos.symbol
            profit = pos.profit
            order_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            vol = pos.volume
            report += f"- {order_type} {vol} {symbol} | Đang chạy PnL: {profit:+.2f}$\n"
            
    mt5.shutdown()
    
    send_to_tele.send_to_telegram(report, is_done=True, target_channels='1816854047')

if __name__ == "__main__":
    check_mt5()
