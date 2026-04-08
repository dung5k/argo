import os
import re
import json
import shutil
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download

class V2CloudManager:
    """Quản lý việc tương tác đồng bộ dữ liệu với HuggingFace Dataset"""
    def __init__(self, target_symbol: str, target_prefix: str, hf_token: str, log_callback=None):
        self.target_symbol = target_symbol.lower()
        self.target_prefix = target_prefix.upper()
        self.hf_token = hf_token
        self.log_callback = log_callback or print
        
        self.safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(self.safe_script_dir, "data")
        self.runs_dir = Path(os.path.join(self.safe_script_dir, "runs"))
        self.models_dir = os.path.join(self.safe_script_dir, "models")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)

    def _translate_weight_name(self, base_weight_name: str, session_id: str) -> str:
        s_map = {"asian": "asia", "european": "london", "us": "ny", 0: "asia", 1: "london", 2: "ny"}
        session_str = s_map.get(session_id, "unified")
        weight_file = base_weight_name
        if "v2_weights_" in base_weight_name:
            weight_file = base_weight_name.replace("v2_weights_", f"{session_str}_weights_")
        elif "unified_weights" in base_weight_name:
            weight_file = base_weight_name.replace("unified_weights.pth", f"{session_str}_weights_BEST_VLOSS.pth")
        return weight_file

    def get_latest_run_id(self, api: HfApi, weight_file: str) -> str:
        files = api.list_repo_files("dung5k/argo_data", repo_type="dataset")
        # Ensure target_prefix matches like _xauusd_
        run_dirs = [f.split('/')[1] for f in files if f.startswith('runs/') and f'_{self.target_prefix.lower()}_' in f and weight_file in f]
        valid_runs = [r for r in run_dirs if r != 'old']
        if not valid_runs:
            raise FileNotFoundError("Không tìm thấy thư mục run_ tương thích trên Repo!")
        return max(valid_runs)

    def sync_session_model(self, base_weight_name: str, session_id: str, hf_run_cfg: str = None) -> tuple:
        """
        Đồng bộ model từ HF, fallback về local nếu lỗi.
        Returns: (model_path, active_brain_name, num_xau_features, num_features, inference_feats)
        """
        weight_file = self._translate_weight_name(base_weight_name, session_id)
        active_brain_name = weight_file
        model_path = ""
        num_xau_features = 8
        num_features = 86
        inference_feats = []
        
        self.log_callback(f"[CloudManager] Đang nạp cho Phiên: {session_id} - File: {weight_file}...")
        
        try:
            # 1. Kéo mây (Cloud First)
            api = HfApi(token=self.hf_token)
            latest_run = hf_run_cfg if hf_run_cfg else self.get_latest_run_id(api, weight_file)
            active_brain_name = latest_run
            
            model_path = hf_hub_download(
                repo_id="dung5k/argo_data", repo_type="dataset", token=self.hf_token,
                filename=f"runs/{latest_run}/{weight_file}"
            )
            
            # Kéo Scaler V2
            try:
                scaler_cloud_path = hf_hub_download(
                    repo_id="dung5k/argo_data", repo_type="dataset", token=self.hf_token,
                    filename=f"runs/{latest_run}/scaler_v2.pkl"
                )
                scaler_local = os.path.join(self.data_dir, "scaler_v2.pkl")
                shutil.copy(scaler_cloud_path, scaler_local)
                self.log_callback(f" ├─ ✅ [SCALE SHIELD] Đã đồng bộ Scaler V2: {latest_run}")
            except Exception as e:
                self.log_callback(f" ├─ ⚠️ Lỗi tải Scaler V2: {e}")
                
            # Kéo Metrix V2
            try:
                metrix_path = hf_hub_download(
                    repo_id="dung5k/argo_data", repo_type="dataset", token=self.hf_token,
                    filename=f"runs/{latest_run}/training_metrix_v2.json"
                )
                with open(metrix_path, "r", encoding='utf-8') as fm:
                    metrix = json.load(fm)
                inference_feats = metrix.get("data_features", [])
                if inference_feats:
                    num_features = len(inference_feats)
                # Override via dimensions if present (tương thích training_metrix cập nhật)
                dims = metrix.get("dimensions", {})
                if dims:
                    num_xau_features = dims.get("num_features_xau", num_xau_features)
                    num_macro = dims.get("num_features_macro", num_features - num_xau_features)
                    num_features = num_xau_features + num_macro
            except Exception as e:
                self.log_callback(f" ├─ ⚠️ Lỗi tải Metrix V2: {e}")
                
            self.log_callback(f"[CloudManager] ✅ Đã tải thành công HỆ TƯ TƯỞNG từ Đám mây!")
                
        except Exception as e:
            self.log_callback(f"[CloudManager] ⚠️ Tải đám mây thất bại ({e}). Chuyển Local Cache...")
            found_models = list(self.runs_dir.rglob(weight_file))
            if found_models:
                model_path = str(max(found_models, key=os.path.getctime))
            else:
                old_model_path = os.path.join(self.models_dir, f"{self.target_symbol}_{session_id}_weights.pth")
                if os.path.exists(old_model_path):
                    model_path = old_model_path
        
        if not model_path or not os.path.exists(model_path):
            raise FileNotFoundError(f"[CloudManager] Lỗi Trầm Trọng: Không tìm thấy {weight_file} ở Mây lẫn Đĩa!")
            
        # Tìm chuẩn metadata cục bộ (Chỉ dùng làm Fallback nếu Cloud không khai báo Dimensions)
        meta_path_local = os.path.join(self.data_dir, f"feature_meta_{self.target_prefix}.json")
        if os.path.exists(meta_path_local):
            with open(meta_path_local, "r", encoding='utf-8') as mf:
                local_xau = json.load(mf).get("num_xau_features", 8)
                # Nếu giá trị đựơc giữ nguyên ở mặc định (8) thì mới lấy Cache ở Đĩa!
                if num_xau_features == 8:
                    num_xau_features = local_xau
                
        self.log_callback(f"[CloudManager] Nạp thành công: {model_path}")
        return model_path, active_brain_name, num_xau_features, num_features, inference_feats
