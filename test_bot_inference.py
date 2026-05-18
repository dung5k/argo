import os
import sys
import time
import json

safe_script_dir = os.path.dirname(os.path.abspath(__file__))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.bot_v3.config_loader_v3 import V3ConfigLoader
from src.bot_v6.data_processor_v6 import V6DataProcessor
from src.bot_v6.inference_engine_v6 import V6InferenceEngine
from src.core.mt5_data_manager import MT5DataManager
from src.bot_v3.cloud_manager_v3 import V3CloudManager

def test_inference():
    print("Testing Asian Bot Inference...")
    config_file = "bot_config_v6_ltc.json"
    schedule_file = "bot_schedule_v6_ltc.json"
    
    loader = V3ConfigLoader(config_file, schedule_file)
    CONFIG = loader.load_base_config()
    
    with open(schedule_file, "r") as f:
        s_data = json.load(f)
    asian_info = s_data["schedule"]["asian"]
    CONFIG = loader.apply_schedule_overrides(CONFIG, asian_info, False)
    
    print("Loaded CONFIG for ASIAN")
    print("ROUTING:", CONFIG.get("DATA_SOURCE", {}).get("ROUTING", {}))
    print("MTF_INPUTS:", [m['SYMBOL'] for m in CONFIG.get("FEATURE_ENGINEERING", {}).get("MTF_INPUTS", [])])
    
    engine = V6InferenceEngine(log_callback=print)
    mt5_manager = MT5DataManager(log_callback=print, target_sym="LTCUSDT", config_path=config_file)
    mt5_manager.config = CONFIG
    
    target_run_id = CONFIG.get("HF_RUN_ID")
    cfg_id = CONFIG.get("CONFIG_ID")
    print(f"Target Run ID: {target_run_id}")
    
    cloud = V3CloudManager("LTCUSDT", "LTCUSDT", "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", CONFIG, log_callback=print)
    m_path, s_path, i_feats, n_feat = cloud.sync_session_model(cfg_id)
    
    print(f"Model path: {m_path}")
    engine.load_weights(m_path, CONFIG)
    
    processor = V6DataProcessor(s_path, i_feats, config=CONFIG, log_callback=print)
    processor._init_fe()
    
    all_feats = []
    for co in processor.column_orders:
        all_feats.extend(co)
    for mtf_cfg in CONFIG.get('FEATURE_ENGINEERING', {}).get('MTF_INPUTS', []):
        sym = mtf_cfg.get('SYMBOL')
        if sym:
            all_feats.append(f"{sym}_dummy")
            
    mt5_manager.force_reload_dynamic_features(list(set(all_feats)))
    
    print("Fetching live merged data...")
    merged_df, sym_data, err = mt5_manager.get_live_merged_data_in_memory(window=2880)
    
    if err or merged_df is None:
        print(f"Failed to fetch data: {err}")
        return
        
    print(f"Fetched {len(merged_df)} rows of data.")
    
    X_list, latest_time = processor.process(merged_df)
    if X_list is None:
        print("Data Processor rejected data")
        return
        
    print("Running inference...")
    pred = engine.predict(X_list)
    
    print("="*50)
    print("INFERENCE RESULT:")
    print(f"Action: {pred['action']}")
    print(f"MSE: {pred['mse']:.4f}")
    print(f"Probabilities: BUY={pred['raw'][1]:.2%}, SELL={pred['raw'][0]:.2%}")
    print("="*50)

if __name__ == "__main__":
    test_inference()
