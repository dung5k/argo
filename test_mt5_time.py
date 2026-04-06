import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime

path = r'C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe'
if mt5.initialize(path=path):
    sym = 'XAUUSDm'
    mt5.symbol_select(sym, True)
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 5)
    if rates is not None:
        df = pd.DataFrame(rates)
        print('Raw rates time:')
        for r in rates:
            print(f"{r['time']} -> {datetime.utcfromtimestamp(r['time'])}")
        
        tick = mt5.symbol_info_tick(sym)
        t_tick = tick.time if tick else 0
        t_sys = int(time.time())
        offset_sec = (t_tick - t_sys)
        offset_hours = round(offset_sec / 3600)
        
        print(f'tick.time: {t_tick}  -> {datetime.utcfromtimestamp(t_tick)}')
        print(f'sys.time:  {t_sys}  -> {datetime.utcfromtimestamp(t_sys)}')
        print(f'offset_hours: {offset_hours}')
        
        df['time'] = df['time'] - (offset_hours * 3600)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        df.index = df.index.tz_localize('UTC')
        
        print('\nAdjusted DF Index:')
        print(df.index)
        
        dt_utc_now = datetime.utcnow().replace(tzinfo=None)
        dt = df.index[-1].tz_convert('UTC').tz_localize(None)
        
        print('\nChecking staleness:')
        print('UTC Now:', dt_utc_now)
        print('Last DF Time (UTC):', dt)
        print('diff_mins:', (dt_utc_now - dt).total_seconds() / 60.0)
    else:
        print('no rates')
    mt5.shutdown()
