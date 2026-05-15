import json
path = r'd:\DungLA\client1\bot_config_v6_ltc_weekend.json'
with open(path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['LIVE_BOT']['TRADE_PLATFORM'] = 'BINANCE'
config['EXECUTION_SYMBOL'] = 'LTCUSDT'

with open(path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
