import json, warnings
warnings.filterwarnings('ignore')
from src.bot_v3.data_processor_v3 import V3DataProcessor
from src.bot_v3.inference_engine_v3 import V3InferenceEngine
from src.core.mt5_data_manager import MT5DataManager

with open('data/bot_config_xau_ny_v3_5.json', 'r') as f:
    cfg = json.load(f)

mt5 = MT5DataManager(target_sym='XAUUSDm', config_path='data/bot_config_xau_ny_v3_5.json')
inference_feats = ['log_return_open', 'log_return_high', 'log_return_low', 'log_return_close', 'upper_wick_pct', 'lower_wick_pct', 'atr_normalized', 'bb_width', 'macd_hist', 'DXY_log_ret', 'US_10Y_YIELD_log_ret', 'USDJPY_log_ret']
mt5.force_reload_dynamic_features(inference_feats)
df, _, err1 = mt5.get_live_merged_data_in_memory(window=120)

if err1:
    print('ERR_MT5:', err1)
    exit()

dp = V3DataProcessor(
    scaler_path='data/scaler_CFG_XAU_NY_V3_5.pkl',
    inference_feats=['log_return_open', 'log_return_high', 'log_return_low', 'log_return_close', 'upper_wick_pct', 'lower_wick_pct', 'atr_normalized', 'bb_width', 'macd_hist', 'DXY_log_ret', 'US_10Y_YIELD_log_ret', 'USDJPY_log_ret'],
    window_size=60,
    config=cfg
)

t, err = dp.ingest_and_scale(df)
if err:
    print('ERR_PIPELINE:', err)
else:
    engine = V3InferenceEngine()
    engine.load_weights('data/v3_xauusd_ny_weights.pth', num_features=12, d_model=128, nhead=8, num_attn_layers=4, window_size=60)
    action, mse, probs = engine.predict(t)
    print(f'Mã: XAUUSDm')
    print(f'Loss: {mse:.4f} (MSE)')
    print(f'Rate: Buy {probs["buy"]*100:.1f}% | Sell {probs["sell"]*100:.1f}%')
    print(f'Action: {action}')
