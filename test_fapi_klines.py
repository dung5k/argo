import ccxt
import time

exchange = ccxt.binance({'enableRateLimit': True})
symbol = 'LTCUSDT'

try:
    # fapiPublicGetKlines for futures, publicGetKlines for spot
    res = exchange.fapiPublicGetKlines({'symbol': symbol, 'interval': '1m', 'limit': 2})
    print("fapi klines:")
    print(res)
except Exception as e:
    print("Error:", e)
