import os
import re

filepath = r'd:\DungLA\client1\src\bot_v6\data_processor_v6.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

process_new = '''    def process(self, df_raw: pd.DataFrame):
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
            return None, None'''

content = re.sub(r'    def process\(self, df_raw: pd\.DataFrame\):.*', process_new, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
