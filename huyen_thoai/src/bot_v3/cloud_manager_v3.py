import os
import shutil
import json
import joblib
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download


class V3CloudManager:
    """Quản lý đồng bộ Model AAMT và Scaler V3 từ HuggingFace về máy cục bộ.
    """
    def __init__(self, target_symbol: str, target_prefix: str, hf_token: str, config: dict, log_callback=None):
        self.target_symbol = target_symbol.lower()
        self.target_prefix = target_prefix.upper()
        self.hf_token = hf_token
        self.config = config
        self.log_callback = log_callback or print

        cloud_cfg = self.config.get('HF_CLOUD', {})
        self.model_repo = cloud_cfg.get('MODEL_REPO', 'dung5k/trading_models_v3')
        self.dataset_repo = cloud_cfg.get('DATASET_REPO', 'dung5k/xau_v3_tensor_ny')

        self.safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(self.safe_script_dir, "data")
        self.runs_dir = Path(os.path.join(self.safe_script_dir, "runs"))
        self.models_dir = os.path.join(self.safe_script_dir, "models")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        self.log_callback(
            f"[CloudManagerV3] Khởi tạo | target={target_prefix} "
            f"model_repo={self.model_repo} dataset_repo={self.dataset_repo}"
        )

    def _download_file(self, repo_id, remote_path: str) -> str:
        # Tự động lấy file ở dưới local trước (nếu chạy local & file có sẵn)
        if os.path.exists(remote_path):
            self.log_callback(f"[CloudManagerV3] ⚡ Tìm thấy cache trên máy Local: {remote_path}")
            return os.path.abspath(remote_path)
            
        self.log_callback(f"[CloudManagerV3] ⬇ Đang tải: {remote_path} từ {repo_id}")
        local_path = hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            token=self.hf_token,
            filename=remote_path,
        )
        self.log_callback(f"[CloudManagerV3] ✅ Tải xong → {local_path}")
        return local_path

    def _save_to_data_dir(self, src_path: str, filename: str) -> str:
        dest = os.path.join(self.data_dir, filename)
        shutil.copy(src_path, dest)
        self.log_callback(f"[CloudManagerV3] 💾 Đã lưu cache: {dest}")
        return dest

    def sync_explicit_model(self, run_id: str, config_id: str) -> tuple:
        """
        Đồng bộ model, trả về (model_path, local_scaler_path, scaler_feats, num_features)
        """
        cfg_id_pure = config_id.replace('_INDICATOR', '')

        self.log_callback(f"[CloudManagerV3] ▶ Bắt đầu sync_explicit_model | run={run_id} | cfg={cfg_id_pure}")

        model_path = ""
        local_scaler_path = ""

        try:
            # Attempt to download config.json
            self._download_file(self.model_repo, f"workspaces/{config_id}/runs/{run_id}/config.json")
        except Exception:
            try:
                self._download_file(self.dataset_repo, f"workspaces/{config_id}/runs/{run_id}/config.json")
            except Exception:
                pass

        scaler_feats = []

        try:
            # 1. Thử path chuẩn: runs/{run_id}/brains/aamt_v3_{cfg_id_pure}_final.pth
            model_path = self._download_file(self.model_repo, f"workspaces/{config_id}/runs/{run_id}/brains/aamt_v3_{cfg_id_pure}_final.pth")
        except Exception:
            try:
                # 2. Thử path không có workspaces/ (Legacy hoặc repo chuyên dụng)
                model_path = self._download_file(self.model_repo, f"runs/{run_id}/brains/aamt_v3_{cfg_id_pure}_final.pth")
            except Exception:
                try:
                    # 3. Thử path không có brains/ (V2)
                    model_path = self._download_file(self.model_repo, f"runs/{run_id}/aamt_v3_{cfg_id_pure}_final.pth")
                except Exception as e:
                    self.log_callback(f"[CloudManagerV3] ❌ Lỗi tải Model Weights: {e}")
                    # Thử tìm best_val_loss nếu các cái trên xịt
                    try:
                        model_path = self._download_file(self.model_repo, f"workspaces/{config_id}/runs/{run_id}/brains/aamt_v3_{cfg_id_pure}_best_val_loss.pth")
                    except Exception as e2:
                        self.log_callback(f"[CloudManagerV3] ❌ Lỗi tải Model Weights (kể cả best_val_loss): {e2}")
                        raise

        try:
            try:
                scaler_cloud_path = self._download_file(self.dataset_repo, f"workspaces/{config_id}/runs/{run_id}/brains/scaler_{cfg_id_pure}.pkl")
            except Exception:
                try:
                    scaler_cloud_path = self._download_file(self.dataset_repo, f"workspaces/{config_id}/runs/{run_id}/data/tensors/scaler_{cfg_id_pure}.pkl")
                except Exception:
                    try:
                        scaler_cloud_path = self._download_file(self.dataset_repo, f"workspaces/{config_id}/data/tensors/scaler_{cfg_id_pure}.pkl")
                    except Exception:
                        try:
                            scaler_cloud_path = self._download_file(self.dataset_repo, f"data/{cfg_id_pure}/scaler_{cfg_id_pure}.pkl")
                        except Exception:
                            scaler_cloud_path = self._download_file(self.dataset_repo, f"workspaces/data/{config_id}/scaler_{cfg_id_pure}.pkl")
            local_scaler_path = self._save_to_data_dir(scaler_cloud_path, f"scaler_{cfg_id_pure}.pkl")
            
            # Auto-convert numpy 2.x pickled scaler to JSON using global Python
            import subprocess
            import json
            py39_path = r"C:\Users\GiggaMan\AppData\Local\Programs\Python\Python39\python.exe"
            script_path = os.path.join(self.safe_script_dir, "fix_scalers.py")
            if os.path.exists(py39_path) and os.path.exists(script_path):
                subprocess.run([py39_path, script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            json_path = local_scaler_path.replace(".pkl", ".json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    scaler_data = json.load(f)
                scaler_obj = scaler_data.get("scaler", {})
                if "feature_names_in_" in scaler_obj:
                    scaler_feats = list(scaler_obj["feature_names_in_"])
                elif "column_order" in scaler_data and scaler_data["column_order"]:
                    scaler_feats = list(scaler_data["column_order"])
            else:
                scaler_obj = joblib.load(local_scaler_path)
                if hasattr(scaler_obj, "feature_names_in_"):
                    scaler_feats = list(scaler_obj.feature_names_in_)
                elif isinstance(scaler_obj, dict):
                    if "feature_names" in scaler_obj:
                        scaler_feats = list(scaler_obj["feature_names"])
                    elif "column_order" in scaler_obj:
                        scaler_feats = list(scaler_obj["column_order"])
                
        except Exception as e:
            self.log_callback(f"[CloudManagerV3] ❌ Lỗi tải Scaler: {e}")
            raise

        self.log_callback(f"[CloudManagerV3] ✅ Đồng bộ V3 Cloud thành công!")
        return model_path, local_scaler_path, scaler_feats, len(scaler_feats)

    def sync_session_model(self, config_id: str) -> tuple:
        """
        Mô_phỏng cho logic đổi phiên. Trong V3 hiện tại, ta sẽ lấy run_id từ config luôn.
        """
        run_id = self.config.get("HF_RUN_ID")
        if not run_id:
            raise ValueError("[CloudManagerV3] Cấu hình không có HF_RUN_ID. Vui lòng cập nhật.")
        return self.sync_explicit_model(run_id, config_id)
