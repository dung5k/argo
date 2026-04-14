import os
import shutil
import json
import joblib
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download


class V2CloudManager:
    """Quản lý đồng bộ Model AI và Scaler từ HuggingFace về máy cục bộ.

    Trách nhiệm duy nhất: download artifacts từ cloud, không chứa logic inference hay trading.
    """

    HF_REPO_ID = "dung5k/argo_data"
    HF_REPO_TYPE = "dataset"

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
        self.log_callback(
            f"[CloudManager] Khởi tạo | symbol={target_symbol} prefix={target_prefix} "
            f"data_dir={self.data_dir}"
        )

    # -------------------------------------------------------------------------
    # PRIVATE – Download helpers (mỗi hàm chỉ 1 việc)
    # -------------------------------------------------------------------------

    def _download_file(self, remote_path: str) -> str:
        """Download 1 file từ HF, trả về local path. Raise nếu thất bại."""
        self.log_callback(f"[CloudManager] ⬇ Đang tải: {remote_path}")
        local_path = hf_hub_download(
            repo_id=self.HF_REPO_ID,
            repo_type=self.HF_REPO_TYPE,
            token=self.hf_token,
            filename=remote_path,
        )
        self.log_callback(f"[CloudManager] ✅ Tải xong → {local_path}")
        return local_path

    def _save_to_data_dir(self, src_path: str, filename: str) -> str:
        """Copy file từ HF cache về data_dir. Trả về đường dẫn đích."""
        dest = os.path.join(self.data_dir, filename)
        shutil.copy(src_path, dest)
        self.log_callback(f"[CloudManager] 💾 Đã lưu: {dest}")
        return dest

    def _extract_features_from_scaler(self, scaler_path: str) -> tuple:
        """Trích xuất (inference_feats, num_features, num_xau_features) từ scaler pkl.
        Returns: (list, int, int) – trả ([], 86, 8) nếu scaler không có feature_names_in_.
        """
        try:
            scaler_obj = joblib.load(scaler_path)
            feats = []
            if hasattr(scaler_obj, "feature_names_in_"):
                feats = list(scaler_obj.feature_names_in_)
            elif isinstance(scaler_obj, dict) and "feature_names" in scaler_obj:
                feats = list(scaler_obj["feature_names"])
            
            if feats:
                # Add back is_imputed_flag because scaler doesn't contain it but train_v2.py used it
                if 'is_imputed_flag' not in feats:
                    feats.append('is_imputed_flag')
                n_feat = len(feats)
                # WORKAROUND: train_v2.py did not pass num_xau_features to TransformerModel,
                # therefore TransformerModel defaulted to max(1, num_features // 3).
                # We MUST match this exactly so the model weights align.
                n_xau = max(1, n_feat // 3)
                
                self.log_callback(
                    f"[CloudManager] 🧬 Trích xuất từ Scaler: {n_feat} features "
                    f"(đã vá lỗi is_imputed_flag), {n_xau} XAU features (ẩn theo lỗi train_v2.py để load được weight)."
                )
                return feats, n_feat, n_xau
            else:
                self.log_callback("[CloudManager] ⚠️ Scaler không có danh sách biến → dùng fallback defaults.")
        except Exception as e:
            self.log_callback(f"[CloudManager] ❌ Lỗi đọc Scaler: {e}")
        return [], 86, 8

    def _get_latest_run_id(self, api: HfApi, weight_file: str) -> str:
        """Tìm run_id mới nhất trên HF repo phù hợp target_prefix và weight_file."""
        self.log_callback(f"[CloudManager] 🔍 Tìm run_id mới nhất cho weight_file='{weight_file}'...")
        files = api.list_repo_files(self.HF_REPO_ID, repo_type=self.HF_REPO_TYPE)
        run_dirs = [
            f.split('/')[1]
            for f in files
            if f.startswith('runs/')
            and f'_{self.target_prefix.lower()}_' in f
            and weight_file in f
        ]
        valid_runs = [r for r in run_dirs if r != 'old']
        if not valid_runs:
            raise FileNotFoundError(
                f"[CloudManager] Không tìm thấy run_ phù hợp với '{weight_file}' trên HF repo!"
            )
        latest = max(valid_runs)
        self.log_callback(f"[CloudManager] 🏆 Run mới nhất: {latest} (trong {len(valid_runs)} run tìm thấy)")
        return latest

    def _load_local_fallback_num_xau(self, num_xau_default: int) -> int:
        """Đọc num_xau_features từ metadata cục bộ nếu cloud không cung cấp."""
        meta_path = os.path.join(self.data_dir, f"feature_meta_{self.target_prefix}.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding='utf-8') as mf:
                    local_xau = json.load(mf).get("num_xau_features", num_xau_default)
                self.log_callback(f"[CloudManager] 📁 Local metadata num_xau={local_xau}")
                return local_xau
            except Exception as e:
                self.log_callback(f"[CloudManager] ⚠️ Lỗi đọc local metadata: {e}")
        return num_xau_default

    # -------------------------------------------------------------------------
    # PRIVATE – Core sync logic (dùng chung cho cả session và explicit mode)
    # -------------------------------------------------------------------------

    def _sync_model(self, run_id: str, weight_filename: str, remote_scaler_filename: str, local_scaler_filename: str,
                    metrix_filename: str) -> tuple:
        """Core: download model + scaler + metrix từ run_id chỉ định.
        Returns: (model_path, brain_name, num_xau_features, num_features, inference_feats)
        """
        self.log_callback(
            f"[CloudManager] ▶ Bắt đầu sync | run={run_id} | weight={weight_filename} | scaler={remote_scaler_filename} -> {local_scaler_filename}"
        )

        # 1. Download model weights
        model_path = self._download_file(f"runs/{run_id}/{weight_filename}")

        # 2. Download + save scaler
        inference_feats, num_features, num_xau = [], 86, 8
        try:
            scaler_cloud = self._download_file(f"runs/{run_id}/{remote_scaler_filename}")
            scaler_local = self._save_to_data_dir(scaler_cloud, local_scaler_filename)
            inference_feats, num_features, num_xau = self._extract_features_from_scaler(scaler_local)
        except Exception as e:
            self.log_callback(f"[CloudManager] ⚠️ Không tải được Scaler: {e}")

        # Fallback num_xau nếu vẫn còn default
        if num_xau == 8:
            num_xau = self._load_local_fallback_num_xau(num_xau)

        # 3. Download + save training metrix
        try:
            metrix_cloud = self._download_file(f"runs/{run_id}/{metrix_filename}")
            self._save_to_data_dir(metrix_cloud, "training_metrix_v2.json")
        except Exception as e:
            self.log_callback(f"[CloudManager] ⚠️ Không tải được Metrix: {e}")

        self.log_callback(
            f"[CloudManager] ✅ Sync hoàn tất | run={run_id} | "
            f"n_feats={num_features} | n_xau={num_xau} | model={model_path}"
        )
        return model_path, run_id, num_xau, num_features, inference_feats

    def _find_local_fallback(self, weight_filename: str) -> str:
        """Tìm model trong cache local. Raise nếu không có."""
        self.log_callback(f"[CloudManager] 🔎 Tìm local fallback cho '{weight_filename}'...")
        found = list(self.runs_dir.rglob(weight_filename))
        if found:
            path = str(max(found, key=os.path.getctime))
            self.log_callback(f"[CloudManager] 📁 Dùng local cache: {path}")
            return path
        old_path = os.path.join(self.models_dir, f"{self.target_symbol}_weights.pth")
        if os.path.exists(old_path):
            self.log_callback(f"[CloudManager] 📁 Dùng fallback cũ: {old_path}")
            return old_path
        raise FileNotFoundError(
            f"[CloudManager] Không tìm thấy '{weight_filename}' ở cloud lẫn đĩa cục bộ!"
        )

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def sync_explicit_model(self, run_id: str, weight_filename: str, config_id: str) -> tuple:
        """Đồng bộ model theo Run ID và Config ID chỉ định (từ brain schedule).

        Returns: (model_path, brain_name, num_xau_features, num_features, inference_feats)
        """
        local_scaler_filename = f"scaler_{config_id}.pkl"
        remote_scaler_filename = "scaler_v2.pkl"
        try:
            return self._sync_model(run_id, weight_filename, remote_scaler_filename, local_scaler_filename, "training_metrix_v2.json")
        except Exception as e:
            self.log_callback(f"[CloudManager] ❌ sync_explicit_model thất bại ({e}). Raise lại lỗi.")
            raise

    def sync_session_model(self, base_weight_name: str, session_id: str) -> tuple:
        """Đồng bộ model theo phiên (tự tìm run_id mới nhất trên HF).

        Returns: (model_path, brain_name, num_xau_features, num_features, inference_feats)
        """
        s_map = {"asian": "asia", "european": "london", "us": "ny", 0: "asia", 1: "london", 2: "ny"}
        session_str = s_map.get(session_id, "unified")
        if "unified_weights" in base_weight_name:
            weight_file = base_weight_name.replace("unified_weights.pth", f"{session_str}_weights_BEST_VLOSS.pth")
        elif "v2_weights_" in base_weight_name:
            weight_file = base_weight_name.replace("v2_weights_", f"{session_str}_weights_")
        else:
            weight_file = base_weight_name

        self.log_callback(f"[CloudManager] 🌐 sync_session_model | session={session_id} | weight={weight_file}")

        try:
            api = HfApi(token=self.hf_token)
            run_id = self._get_latest_run_id(api, weight_file)
            return self._sync_model(run_id, weight_file, "scaler_v2.pkl", "scaler_v2.pkl", "training_metrix_v2.json")
        except Exception as e:
            self.log_callback(f"[CloudManager] ⚠️ Cloud sync thất bại ({e}). Chuyển sang local cache...")
            try:
                model_path = self._find_local_fallback(weight_file)
                return model_path, "local_cache", 8, 86, []
            except Exception as e2:
                self.log_callback(f"[CloudManager] ❌ Không tìm được fallback: {e2}")
                raise
