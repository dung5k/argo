import joblib
import json
import os
import numpy as np

def convert_scaler(pkl_path):
    if not os.path.exists(pkl_path):
        print(f"Not found: {pkl_path}")
        return
        
    try:
        obj = joblib.load(pkl_path)
    except Exception as e:
        print(f"Error loading {pkl_path}: {e}")
        return
        
    scaler = obj.get("scaler") if isinstance(obj, dict) else obj
    column_order = obj.get("column_order") if isinstance(obj, dict) else None
    
    data = {}
    if hasattr(scaler, "center_") and scaler.center_ is not None:
        data["center_"] = scaler.center_.tolist()
    if hasattr(scaler, "scale_") and scaler.scale_ is not None:
        data["scale_"] = scaler.scale_.tolist()
    if hasattr(scaler, "feature_names_in_") and scaler.feature_names_in_ is not None:
        data["feature_names_in_"] = scaler.feature_names_in_.tolist()
        
    result = {
        "scaler": data,
        "column_order": column_order
    }
    
    json_path = pkl_path.replace(".pkl", ".json")
    with open(json_path, "w") as f:
        json.dump(result, f)
    print(f"Successfully converted {pkl_path} to {json_path}")

data_dir = r"D:\DungLA\client1\data"
for f in os.listdir(data_dir):
    if f.startswith("scaler_CFG_XAG") and f.endswith(".pkl"):
        convert_scaler(os.path.join(data_dir, f))
