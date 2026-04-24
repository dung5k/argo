import MetaTrader5 as mt5
from datetime import datetime as dt
import pytz

mt5.initialize(r'D:\mt5\MetaTrader 5 EXNESS\terminal64.exe')
tz = pytz.timezone('UTC')
end_dt = tz.localize(dt(2026, 4, 23))

rates = mt5.copy_rates_from('XAUUSDm', mt5.TIMEFRAME_M1, int(end_dt.timestamp()), 500000)
print("XAUUSDm rates:", len(rates) if rates is not None else "None", "Error:", mt5.last_error())
mt5.shutdown()
