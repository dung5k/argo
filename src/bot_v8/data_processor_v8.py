import os
import sys
import numpy as np
import pandas as pd
import torch

# Ensure src in path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.v8_engine.fractal_detector import FractalDetector
from src.v8_engine.nlp_tokenizer import NLPTokenizer
from src.v8_engine.mtf_processor import MTFProcessor
from src.v8_engine.order_block_detector import OrderBlockDetector
from src.v8_engine.indicators import add_all_indicators

class V8DataProcessor:
    def __init__(self, config: dict, log_callback=None):
        self.config = config
        self.log = log_callback or print
        self.vocab = config.get('nlp_tokenizer_params', {}).get('vocabulary', ["HH", "HL", "LH", "LL", "BOS_UP", "BOS_DN", "CHOCH_UP", "CHOCH_DN", "FAKE_BOS"])
        self.token2id = {token: i+1 for i, token in enumerate(self.vocab)}
        self.token2id['<PAD>'] = 0
        self.seq_len = config.get('nlp_tokenizer_params', {}).get('max_sequence_length', 50)
        
        self.fd = FractalDetector(
            window_size=config.get('fractal_params', {}).get('window_size', 5),
            latency_candles=config.get('fractal_params', {}).get('latency_candles', 2)
        )
        self.tk = NLPTokenizer(config)
        self.ob = OrderBlockDetector(config)
        self.mtf = MTFProcessor(config)
        
    def resample_m1_to_tf(self, df_m1: pd.DataFrame, freq: str) -> pd.DataFrame:
        agg_dict = {'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}
        
        # MT5 data column mapping
        rename_map = {}
        for col in df_m1.columns:
            if 'open' in col.lower() and 'open' not in rename_map: rename_map[col] = 'open'
            elif 'high' in col.lower() and 'high' not in rename_map: rename_map[col] = 'high'
            elif 'low' in col.lower() and 'low' not in rename_map: rename_map[col] = 'low'
            elif 'close' in col.lower() and 'close' not in rename_map: rename_map[col] = 'close'
            elif 'volume' in col.lower() and 'tick' not in col.lower() and 'volume' not in rename_map: rename_map[col] = 'volume'
            
        df_clean = df_m1.rename(columns=rename_map)
        
        if freq in ['1m', '1T', 'M1']:
            return df_clean[list(agg_dict.keys())].dropna()
            
        df_resampled = df_clean.resample(freq).agg(agg_dict).dropna()
        return df_resampled

    def _process_tf(self, df, suffix=""):
        df_proc = self.fd.detect(df)
        df_proc = self.tk.tokenize(df_proc)
        df_proc = self.ob.detect(df_proc)
        df_proc['token_id'] = df_proc['market_structure_token'].map(self.token2id)
        df_proc = add_all_indicators(df_proc)
        
        df_proc['hour_sin'] = np.sin(2 * np.pi * df_proc.index.hour / 24.0)
        df_proc['hour_cos'] = np.cos(2 * np.pi * df_proc.index.hour / 24.0)
        df_proc['day_sin'] = np.sin(2 * np.pi * df_proc.index.dayofweek / 7.0)
        df_proc['day_cos'] = np.cos(2 * np.pi * df_proc.index.dayofweek / 7.0)
        
        rename_dict = {}
        for col in df_proc.columns:
            if col not in ['open', 'high', 'low', 'close', 'volume'] and suffix != "":
                rename_dict[col] = f"{col}{suffix}"
        if rename_dict:
            df_proc = df_proc.rename(columns=rename_dict)
        return df_proc

    def process_live_data(self, df_m1: pd.DataFrame):
        try:
            df_m15 = self.resample_m1_to_tf(df_m1, '15T') # M15
            df_h1 = self.resample_m1_to_tf(df_m1, '1h')
            df_h4 = self.resample_m1_to_tf(df_m1, '4h')
            
            # Need minimum data for indicators (SMA 200 needs 200 candles)
            if len(df_h4) < 200:
                self.log(f"❌ [V8DataProcessor] Lỗi: Cần ít nhất 200 nến H4 (hiện có {len(df_h4)}). Hãy kéo dữ liệu MT5 dài hơn!")
                return False, None
                
            proc_m15 = self._process_tf(df_m15)
            proc_h1 = self._process_tf(df_h1, "_h1")
            proc_h4 = self._process_tf(df_h4, "_h4")
            
            df = self.mtf.merge_mtf(proc_m15, proc_h1, proc_h4)
            
            # Lấy dòng cuối cùng (hiện tại)
            row = df.iloc[-1]
            row_time = df.index[-1]
            
            # Helper to get sequence
            def get_seq(df_source, token_col_name):
                valid_tokens = df_source[token_col_name].dropna()
                history = valid_tokens.tolist()
                history = [int(x) for x in history]
                if len(history) < self.seq_len:
                    history = [0] * (self.seq_len - len(history)) + history
                else:
                    history = history[-self.seq_len:]
                return torch.tensor(history, dtype=torch.long)

            x_m15 = get_seq(proc_m15, 'token_id').unsqueeze(0)
            x_h1 = get_seq(proc_h1, 'token_id_h1').unsqueeze(0)
            x_h4 = get_seq(proc_h4, 'token_id_h4').unsqueeze(0)
            
            ob_features = [
                row.get('in_ob_up', 0.0), row.get('in_ob_dn', 0.0), row.get('ob_strength', 0.0),
                row.get('in_ob_up_h1', 0.0), row.get('in_ob_dn_h1', 0.0), row.get('ob_strength_h1', 0.0),
                row.get('in_ob_up_h4', 0.0), row.get('in_ob_dn_h4', 0.0), row.get('ob_strength_h4', 0.0)
            ]
            time_features = [
                row.get('hour_sin', 0.0), row.get('hour_cos', 0.0),
                row.get('day_sin', 0.0), row.get('day_cos', 0.0)
            ]
            
            def get_inds(r, suffix=""):
                return [
                    r.get(f'rsi{suffix}', 50.0) / 100.0,
                    r.get(f'macd_hist{suffix}', 0.0),
                    r.get(f'dist_ema50{suffix}', 0.0),
                    r.get(f'dist_ema200{suffix}', 0.0),
                    r.get(f'body_size{suffix}', 0.0),
                    r.get(f'upper_wick{suffix}', 0.0),
                    r.get(f'lower_wick{suffix}', 0.0)
                ]
                
            m15_inds = get_inds(row, "")
            h1_inds = get_inds(row, "_h1")
            h4_inds = get_inds(row, "_h4")
            
            all_cont = ob_features + time_features + m15_inds + h1_inds + h4_inds
            all_cont = [0.0 if np.isnan(v) else float(v) for v in all_cont]
            cont_x = torch.tensor(all_cont, dtype=torch.float).unsqueeze(0)
            
            atr_val = row.get('atr', 1.5)
            if pd.isna(atr_val) or atr_val <= 0: atr_val = 1.5
            
            return True, (x_m15, x_h1, x_h4, cont_x, float(row['close']), float(atr_val))
            
        except Exception as e:
            self.log(f"❌ [V8DataProcessor] Lỗi Exception: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False, None
