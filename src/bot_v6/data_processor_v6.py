import os
import sys
import numpy as np
import pandas as pd
import joblib
from typing import List, Dict, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3

class V6DataProcessor:
    """
    Xử lý dữ liệu đầu vào online cho mô hình AI V6 (Multi-Timeframe).
    """
    def __init__(self, scaler_path: str, config: dict = None, log_callback=None):
        self.scaler_path = scaler_path
        self.config = config or {}
        self.log = log_callback or print
        
        self.scalers = []
        self.column_orders = []
        self.tf_configs = self.config.get('FEATURE_ENGINEERING', {}).get('MTF_INPUTS', [])
        self.target_prefix = self.config.get('TARGET_PREFIX', 'LTCUSDT')
        
        self.fe_engines = []
        self.log(f'[DataProcessorV6] Khởi tạo V6 MTF Processor với {len(self.tf_configs)} TFs')

    def _init_engines(self) -> bool:
        if self.fe_engines:
            return True
            
        try:
            self.log(f'[DataProcessorV6] Nạp scalers từ {self.scaler_path}...')
            bundle = joblib.load(self.scaler_path)
            if not isinstance(bundle, dict) or 'scalers' not in bundle:
                self.log('[DataProcessorV6] ❌ Scaler bundle không hợp lệ.')
                return False
                
            self.scalers = bundle['scalers']
            self.column_orders = bundle['column_orders']
            
            fe_cfg = self.config.get('FEATURE_ENGINEERING', {})
            self.tf_configs = self.tf_configs[:len(self.scalers)]
            
            for tf_cfg in self.tf_configs:
                sym = tf_cfg['SYMBOL']
                macro_features = {}
                if sym != self.target_prefix:
                    macro_features[sym] = tf_cfg.get('FEATURES', [])
                    
                fe = FeatureEngineeringV3(
                    target_prefix=sym,
                    macro_features=macro_features,
                    mtf_windows=fe_cfg.get('MTF_WINDOWS', None),
                    order_flow=fe_cfg.get('ORDER_FLOW', False),
                    vol_regime=fe_cfg.get('VOL_REGIME', False),
                    crypto_mode=fe_cfg.get('CRYPTO_MODE', False),
                    zero_noise_target=fe_cfg.get('ZERO_NOISE_TARGET', False)
                )
                self.fe_engines.append((fe, tf_cfg))
                
            return True
        except Exception as e:
            self.log(f'[DataProcessorV6] ❌ Lỗi khởi tạo: {e}')
            return False

    def process_online(self, df_raw: List[pd.DataFrame]) -> Tuple[bool, List[np.ndarray]]:
        """
        df_raw: List của các DataFrame (M1, H1, H4...) đã được resample từ bên ngoài hoặc Simulator.
        Mỗi DF phải có ít nhất `window_size` + một số nến dự phòng để tính indicator.
        """
        if not self._init_engines():
            return False, None
            
        X_tensors = []
        try:
            for i, (fe, tf_cfg) in enumerate(self.fe_engines):
                df_tf = df_raw[i].copy()
                sym = tf_cfg['SYMBOL']
                features_req = tf_cfg.get('FEATURES', [])
                win_size = tf_cfg.get('WINDOW_SIZE', 60)
                
                sym_lower = sym.lower()
                mapping = {
                    'open': f'{sym_lower}_open',
                    'high': f'{sym_lower}_high',
                    'low': f'{sym_lower}_low',
                    'close': f'{sym_lower}_close',
                    'volume': f'{sym_lower}_volume',
                    'tick_volume': f'{sym_lower}_tick_volume',
                    'spread': f'{sym_lower}_spread'
                }
                df_tf = df_tf.rename(columns=mapping)
                    
                df_fe = fe.process_features(df_tf)
                df_fe = df_fe.replace([np.inf, -np.inf], np.nan).fillna(method='ffill').fillna(0)
                
                final_cols = []
                for f_req in features_req:
                    if f_req in df_fe.columns:
                        final_cols.append(f_req)
                    elif f'{sym}_{f_req}' in df_fe.columns:
                        final_cols.append(f'{sym}_{f_req}')
                    else:
                        final_cols.append(f_req)
                        
                df_selected = df_fe[final_cols]
                
                fe.scaler = self.scalers[i]
                fe.is_fitted = True
                col_order = self.column_orders[i]
                for c in col_order:
                    if c not in df_selected.columns:
                        df_selected[c] = 0.0
                
                # Apply FeatureEngineeringV3's transform_scaler to correctly filter out non-scaled columns
                df_scaled = fe.transform_scaler(df_selected)
                df_scaled = df_scaled[col_order]
                
                scaled = df_scaled.values
                
                if len(scaled) < win_size:
                    self.log(f'[DataProcessorV6] ❌ Không đủ data cho TF{i} ({len(scaled)} < {win_size})')
                    return False, None
                    
                window = scaled[-win_size:]
                X_tensors.append(np.expand_dims(window, axis=0))
                
            return True, X_tensors
        except Exception as e:
            self.log(f'[DataProcessorV6] ❌ Lỗi xử lý online: {e}')
            return False, None
