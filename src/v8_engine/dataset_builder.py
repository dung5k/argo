import pandas as pd
from torch.utils.data import Dataset, DataLoader
import torch
import numpy as np
import json
import os

class V8DatasetBuilder(Dataset):
    """
    Gộp Pipeline: Đọc dữ liệu, Detect Fractal, Map Tokens, OB, và tạo Dataset cho PyTorch.
    Xử lý độc lập cho M15, H1, H4, sau đó merge lại để không bị leak data.
    """
    def __init__(self, config: dict, data_m15: pd.DataFrame, data_h1: pd.DataFrame, data_h4: pd.DataFrame):
        self.config = config
        self.vocab = config.get('nlp_tokenizer_params', {}).get('vocabulary', ["HH", "HL", "LH", "LL", "BOS_UP", "BOS_DN", "CHOCH_UP", "CHOCH_DN", "FAKE_BOS"])
        
        # Map token to ID. <PAD> is 0
        self.token2id = {token: i+1 for i, token in enumerate(self.vocab)}
        self.token2id['<PAD>'] = 0
        
        self.seq_len = config.get('nlp_tokenizer_params', {}).get('max_sequence_length', 50)
        
        from src.v8_engine.fractal_detector import FractalDetector
        from src.v8_engine.nlp_tokenizer import NLPTokenizer
        from src.v8_engine.mtf_processor import MTFProcessor
        from src.v8_engine.order_block_detector import OrderBlockDetector
        
        fd = FractalDetector(
            window_size=config.get('fractal_params', {}).get('window_size', 5),
            latency_candles=config.get('fractal_params', {}).get('latency_candles', 2)
        )
        tk = NLPTokenizer(config)
        ob = OrderBlockDetector(config)
        
        # Process từng khung thời gian độc lập
        def process_tf(df, suffix=""):
            # 1. Fractal
            df_proc = fd.detect(df)
            # 2. Tokenize
            df_proc = tk.tokenize(df_proc)
            # 3. Order Blocks
            df_proc = ob.detect(df_proc)
            # 4. Map ID
            df_proc['token_id'] = df_proc['market_structure_token'].map(self.token2id)
            
            # Đổi tên cột để chuẩn bị merge (ngoại trừ open, high, low, close, volume)
            rename_dict = {}
            for col in df_proc.columns:
                if col not in ['open', 'high', 'low', 'close', 'volume'] and suffix != "":
                    rename_dict[col] = f"{col}{suffix}"
            if rename_dict:
                df_proc = df_proc.rename(columns=rename_dict)
            return df_proc
            
        print("Processing M15 Features...")
        self.df_m15 = process_tf(data_m15)
        print("Processing H1 Features...")
        self.df_h1 = process_tf(data_h1, "_h1")
        print("Processing H4 Features...")
        self.df_h4 = process_tf(data_h4, "_h4")
        
        # Merge MTF
        mtf = MTFProcessor(config)
        self.df = mtf.merge_mtf(self.df_m15, self.df_h1, self.df_h4)
        
        # Đọc cấu hình Auto-ML
        strategy_config_path = "v8_configs/strategy_config.json"
        target_shift = -2
        if os.path.exists(strategy_config_path):
            try:
                with open(strategy_config_path, "r", encoding="utf-8-sig") as f:
                    strat_cfg = json.load(f)
                    target_shift = strat_cfg.get("target_shift", -2)
            except Exception as e:
                print(f"Lỗi đọc strategy_config.json: {e}")

        # Target: 5 classes (Balanced 20% each)
        # 0: Strong Sell (Sell 2), 1: Weak Sell (Sell 1), 2: Hold, 3: Weak Buy (Buy 1), 4: Strong Buy (Buy 2)
        diff = self.df['close'].shift(target_shift) - self.df['close']
        
        valid_diff = diff.dropna()
        if len(valid_diff) > 0:
            p20 = np.percentile(valid_diff, 20.0)
            p40 = np.percentile(valid_diff, 40.0)
            p60 = np.percentile(valid_diff, 60.0)
            p80 = np.percentile(valid_diff, 80.0)
        else:
            p20, p40, p60, p80 = 0, 0, 0, 0
            
        conditions = [
            diff < p20,
            (diff >= p20) & (diff < p40),
            (diff >= p40) & (diff < p60),
            (diff >= p60) & (diff < p80),
            diff >= p80
        ]
        choices = [0, 1, 2, 3, 4]
        
        self.df['target'] = np.select(conditions, choices, default=2)
        
        self.valid_df = self.df.dropna(subset=['target']).copy()
        
        # --- Pre-build sequences cho O(1) __getitem__ ---
        def build_history_index(df_source, token_col_name):
            valid_tokens = df_source[token_col_name].dropna()
            history_list = valid_tokens.tolist()
            history_indices = valid_tokens.index
            idx_to_pos = {idx: i for i, idx in enumerate(history_indices)}
            return history_list, history_indices, idx_to_pos
            
        self.m15_hist, self.m15_idx, self.m15_pos = build_history_index(self.df_m15, 'token_id')
        self.h1_hist, self.h1_idx, self.h1_pos = build_history_index(self.df_h1, 'token_id_h1')
        self.h4_hist, self.h4_idx, self.h4_pos = build_history_index(self.df_h4, 'token_id_h4')

    def __len__(self):
        return len(self.valid_df)
        
    def _get_seq(self, row_time, hist_list, hist_idx, idx_to_pos):
        # Lấy những token có index <= row_time
        # Optimization: Dùng searchsorted
        import bisect
        # idx array is sorted
        # tìm vị trí insert của row_time
        pos_in_idx = bisect.bisect_right(hist_idx, row_time) - 1
        
        if pos_in_idx >= 0:
            last_token_time = hist_idx[pos_in_idx]
            last_pos = idx_to_pos[last_token_time]
            start_pos = max(0, last_pos - self.seq_len + 1)
            history = hist_list[start_pos : last_pos + 1]
        else:
            history = []
            
        if len(history) < self.seq_len:
            history = [0] * (self.seq_len - len(history)) + [int(x) for x in history]
            
        return torch.tensor(history, dtype=torch.long)
        
    def __getitem__(self, idx):
        row_time = self.valid_df.index[idx]
        row = self.valid_df.iloc[idx]
        
        x_m15 = self._get_seq(row_time, self.m15_hist, self.m15_idx, self.m15_pos)
        x_h1 = self._get_seq(row_time, self.h1_hist, self.h1_idx, self.h1_pos)
        x_h4 = self._get_seq(row_time, self.h4_hist, self.h4_idx, self.h4_pos)
        
        # Lấy continuous features (Order Blocks)
        # Điểm mạnh: Ta có thể lấy OB của cả M15, H1, H4!
        # Tạm thời lấy các features từ row (đã được merge_mtf backward fill)
        ob_features = [
            row.get('in_ob_up', 0.0), row.get('in_ob_dn', 0.0), row.get('ob_strength', 0.0),
            row.get('in_ob_up_h1', 0.0), row.get('in_ob_dn_h1', 0.0), row.get('ob_strength_h1', 0.0),
            row.get('in_ob_up_h4', 0.0), row.get('in_ob_dn_h4', 0.0), row.get('ob_strength_h4', 0.0)
        ]
        # Xử lý NaN
        ob_features = [0.0 if np.isnan(v) else float(v) for v in ob_features]
        cont_x = torch.tensor(ob_features, dtype=torch.float)
        
        y = torch.tensor(row['target'], dtype=torch.long)
        
        return x_m15, x_h1, x_h4, cont_x, y
