import os
import pickle
import json
import numpy as np
from sklearn.preprocessing import RobustScaler

def fix_scaler():
    scaler_path = "data/scaler_CFG_XAG_NY_V5.pkl"
    with open(scaler_path, "rb") as f:
        data = pickle.load(f)
        
    scaler_obj = data["scaler"]
    
    if isinstance(scaler_obj, RobustScaler) and hasattr(scaler_obj, "feature_names_in_"):
        cols = list(scaler_obj.feature_names_in_)
    else:
        cols = data["column_order"]
        
    print(f"Original cols ({len(cols)}):", cols)
    
    # Identify indices to remove
    to_remove = ["XAUUSDm_rsi_14", "XAUUSDm_momentum_10"]
    indices_to_remove = [cols.index(c) for c in to_remove if c in cols]
    
    if not indices_to_remove:
        print("Không tìm thấy các cột cần xóa!")
        return
        
    print(f"Removing indices: {indices_to_remove}")
    new_cols = [c for c in cols if c not in to_remove]
    data["column_order"] = new_cols
    if isinstance(scaler_obj, RobustScaler):
        if hasattr(scaler_obj, "center_") and scaler_obj.center_ is not None:
            scaler_obj.center_ = np.delete(scaler_obj.center_, indices_to_remove)
        if hasattr(scaler_obj, "scale_") and scaler_obj.scale_ is not None:
            scaler_obj.scale_ = np.delete(scaler_obj.scale_, indices_to_remove)
        if hasattr(scaler_obj, "feature_names_in_"):
            scaler_obj.feature_names_in_ = np.array(new_cols)
    elif isinstance(scaler_obj, dict):
        if "center_" in scaler_obj:
            scaler_obj["center_"] = np.delete(np.array(scaler_obj["center_"]), indices_to_remove).tolist()
        if "scale_" in scaler_obj:
            scaler_obj["scale_"] = np.delete(np.array(scaler_obj["scale_"]), indices_to_remove).tolist()
        if "feature_names_in_" in scaler_obj:
            scaler_obj["feature_names_in_"] = new_cols
            
    with open(scaler_path, "wb") as f:
        pickle.dump(data, f)
        
    print(f"Fixed scaler saved to {scaler_path}. New shape: {len(new_cols)}")

if __name__ == "__main__":
    fix_scaler()
