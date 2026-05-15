import os
import re

def refactor_train():
    path = "src/training_v6/train_v6.py"
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Update scaler loading to read mtf_inputs
    old_scaler = """        scaler_bundle = pickle.load(f)
    scalers = scaler_bundle["scalers"]
    mtf_config = scaler_bundle["mtf_config"]"""
    
    new_scaler = """        scaler_bundle = pickle.load(f)
    scalers = scaler_bundle["scalers"]
    mtf_inputs = scaler_bundle.get("mtf_inputs", [])"""
    
    if old_scaler in code:
        code = code.replace(old_scaler, new_scaler)
    
    # 2. Update Telegram start_msg
    old_msg_block = """        mtf_configs = fe_cfg.get("MULTI_TIMEFRAME", [])
        
        # Tạo chuỗi chi tiết cho từng mã (Target + Macro)
        target_sym = config.get('TARGET_SYMBOL', '?')
        mtf_format = ", ".join([f"{m.get('TIMEFRAME', '?')} ({m.get('WINDOW_SIZE', '?')} nến)" for m in mtf_configs])
        
        symbols_list = [f"  • 🎯 {target_sym}: <code>{mtf_format}</code>"]
        for mk in macro_keys:
            symbols_list.append(f"  • 🌐 {mk}: <code>{mtf_format}</code>")
        symbols_str = "\\n".join(symbols_list)"""
        
    new_msg_block = """        mtf_inputs = scaler_bundle.get("mtf_inputs", fe_cfg.get("MTF_INPUTS", []))
        
        symbols_list = []
        for inp in mtf_inputs:
            sym = inp.get("SYMBOL", "?")
            tf = inp.get("TIMEFRAME", "?")
            w = inp.get("WINDOW_SIZE", "?")
            feats = inp.get("FEATURES", [])
            symbols_list.append(f"  • 🌐 {sym}: <code>{tf} ({w} nến) - {len(feats)} features</code>")
        symbols_str = "\\n".join(symbols_list)"""
        
    if old_msg_block in code:
        code = code.replace(old_msg_block, new_msg_block)

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("XONG REFAC_TRAIN")

if __name__ == "__main__":
    refactor_train()
