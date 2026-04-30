import ccxt
import pandas as pd
exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

try:
    oi = exchange.fetch_open_interest_history('LTC/USDT:USDT', timeframe='5m', limit=10)
    print("OI Success:", len(oi))
    if len(oi) > 0:
        print(oi[0])
except Exception as e:
    print("OI Error:", e)

try:
    fr = exchange.fetch_funding_rate_history('LTC/USDT:USDT', limit=10)
    print("FR Success:", len(fr))
    if len(fr) > 0:
        print(fr[0])
except Exception as e:
    print("FR Error:", e)
