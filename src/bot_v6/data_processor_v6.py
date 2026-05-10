import os
import sys
import numpy as np
import pandas as pd
import joblib
import json

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3

def resample_dataframe(df_raw, freq):
    if not freq or freq in ['1m', '1T', 'M1']:
        return df_raw.copy()
    rule_map = {'5m': '5min', '15m': '15min', '30m': '30min', '1h': '1h', '1H': '1h', '4h': '4h', '1d': '1D'}
    pd_rule = rule_map.get(freq, freq)
    
    resampled = pd.DataFrame()
    for col in df_raw.columns:
        if 'open' in col.lower():
            resampled[col] = df_raw[col].resample(pd_rule).first().ffill()
        elif 'high' in col.lower():
            resampled[col] = df_raw[col].resample(pd_rule).max().ffill()
        elif 'low' in col.lower():
            resampled[col] = df_raw[col].resample(pd_rule).min().ffill()
        elif 'close' in col.lower() or 'price' in col.lower():
            resampled[col] = df_raw[col].resample(pd_rule).last().ffill()
        elif 'volume' in col.lower() or 'tick_volume' in col.lower():
            resampled[col] = df_raw[col].resample(pd_rule).sum().fillna(0)
        else:
            resampled[col] = df_raw[col].resample(pd_rule).last().ffill()
            
    return resampled.dropna()

class V6DataProcessor:
    def __init__(self, scaler_path: str, inference_feats: list, config: dict, log_callback=None):
        self.scaler_path = scaler_path
        self.inference_feats = inference_feats
        self.config = config or {}
        self.log_callback = log_callback or print
        
        self.mtf_windows = self.config.get('FEATURE_ENGINEERING', {}).get('MTF_INPUTS', [])
        
        # Base config
        self.base_window = self.config.get('FEATURE_ENGINEERING', {}).get('WINDOW_SIZE', 60)
        self.base_tf = self.config.get('FEATURE_ENGINEERING', {}).get('TIMEFRAME', '1m')
        
        self.fe = None
        self.saved_column_order = None
        
    def _init_fe(self) -> bool:
        if self.fe is not None:
            return True
            
        self.log_callback(f"[DataProcessorV6] ðŸ”§ Khá»Ÿi táº¡o FeatureEngineeringV3 tá»« {os.path.basename(self.scaler_path)}...")
        try:
            target_prefix = self.config.get('TARGET_PREFIX', 'LTCUSDT')
            fe_cfg = self.config.get('FEATURE_ENGINEERING', {})
            macro_features = fe_cfg.get('MACRO_FEATURES', {})
            
            self.fe = FeatureEngineeringV3(
                target_prefix=target_prefix, 
                macro_features=macro_features,
                mtf_windows=[],
                order_flow=fe_cfg.get('ORDER_FLOW', False),
                vol_regime=fe_cfg.get('VOL_REGIME', False),
                crypto_mode=fe_cfg.get('CRYPTO_MODE', False)
            )
            
            import joblib
            raw_pickle = joblib.load(self.scaler_path)
            if isinstance(raw_pickle, dict) and "scalers" in raw_pickle:
                self.scalers = raw_pickle["scalers"]
                self.column_orders = raw_pickle["column_orders"]
            else:
                self.log_callback("[DataProcessorV6] âŒ Lá»—i: Scaler khÃ´ng Ä‘Ãºng Ä‘á»‹nh dáº¡ng Heterogeneous V6.")
                return False
                
            self.fe.is_fitted = True
            self.log_callback("[DataProcessorV6] âœ… Sáºµn sÃ ng xá»­ lÃ½ MTF Data.")
            return True
        except Exception as e:
            self.log_callback(f"[DataProcessorV6] âŒ Lá»—i khá»Ÿi táº¡o: {e}")
            import traceback
            self.log_callback(traceback.format_exc())
            return False

    def process(self, df_raw: pd.DataFrame):
        if not self._init_fe():
            return None, None
            
        try:
            target_prefix = self.config.get('TARGET_PREFIX', 'LTCUSDT')
            fe_cfg = self.config.get('FEATURE_ENGINEERING', {})
            X_list = []
            
            for i, mtf_cfg in enumerate(self.mtf_windows):
                sym = mtf_cfg.get("SYMBOL", target_prefix)
                tf = mtf_cfg.get("TIMEFRAME", "1H")
                w_size = mtf_cfg.get("WINDOW_SIZE", 24)
                
                df_tf = resample_dataframe(df_raw, tf)
                
                macro_feats = {target_prefix: ["log_ret", "corr_60"]} if sym != target_prefix else {}
                from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3
                fe_mtf = FeatureEngineeringV3(
                    target_prefix=sym,
                    macro_features=macro_feats,
                    mtf_windows=[],
                    order_flow=fe_cfg.get('ORDER_FLOW', False),
                    vol_regime=fe_cfg.get('VOL_REGIME', False),
                    crypto_mode=fe_cfg.get('CRYPTO_MODE', False)
                )
                
                df_tf_feat = fe_mtf.process_features(df_tf.copy())
                
                corr_col_name = f"{target_prefix}_target_corr_60"
                if corr_col_name in df_tf_feat.columns:
                    df_tf_feat = df_tf_feat.rename(columns={corr_col_name: f"corr_60_{target_prefix}"})
                
                fe_mtf.is_fitted = True
                fe_mtf.scaler = self.scalers[i]
                df_tf_feat = fe_mtf.transform_scaler(df_tf_feat)
                
                col_order_tf = self.column_orders[i]
                available_cols_tf = [c for c in col_order_tf if c in df_tf_feat.columns]
                scaled_tf_df = df_tf_feat[available_cols_tf]
                
                if len(scaled_tf_df) < w_size:
                    self.log_callback(f"[DataProcessorV6] ⚠️ Không đủ nến {tf}: {len(scaled_tf_df)} < {w_size}")
                    return None, None
                    
                X_tf = scaled_tf_df.iloc[-w_size:].values
                import numpy as np
                X_list.append(np.expand_dims(X_tf, axis=0))
                
            tf0 = self.mtf_windows[0].get("TIMEFRAME", "1m")
            df0 = resample_dataframe(df_raw, tf0)
            return X_list, df0.index[-1]
            
        except Exception as e:
            self.log_callback(f"[DataProcessorV6] ❌ Lỗi process: {e}")
            import traceback
            self.log_callback(traceback.format_exc())
            return None, None