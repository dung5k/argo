import ccxt
import time

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
since = exchange.parse8601('2024-01-01T00:00:00Z')
symbol = 'LTC/USDT:USDT'

try:
    oi = exchange.fetch_open_interest_history(symbol, timeframe='5m', since=since, limit=500)
    print("OI chunk 1:", len(oi))
    if len(oi) > 0:
        print("Last TS:", oi[-1]['timestamp'])
        
        oi2 = exchange.fetch_open_interest_history(symbol, timeframe='5m', since=oi[-1]['timestamp'] + 300000, limit=500)
        print("OI chunk 2:", len(oi2))
        if len(oi2) > 0:
            print("First TS:", oi2[0]['timestamp'])
except Exception as e:
    print("Error:", e)
