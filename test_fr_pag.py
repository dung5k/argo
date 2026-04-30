import ccxt
import time

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
since = exchange.parse8601('2024-01-01T00:00:00Z')
symbol = 'LTC/USDT:USDT'

try:
    fr = exchange.fetch_funding_rate_history(symbol, since=since, limit=500)
    print("FR chunk 1:", len(fr))
    if len(fr) > 0:
        print("First TS:", fr[0]['timestamp'])
        print("Last TS:", fr[-1]['timestamp'])
except Exception as e:
    print("Error:", e)
