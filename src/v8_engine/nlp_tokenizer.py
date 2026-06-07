import pandas as pd
import numpy as np

class NLPTokenizer:
    """
    Dịch các đỉnh/đáy Fractal tĩnh thành chuỗi văn bản (NLP Tokens).
    Cấm truy xuất giá trị tương lai. Xác nhận Breakout bằng Close Price và Volume.
    """
    def __init__(self, config: dict):
        params = config.get('nlp_tokenizer_params', {})
        self.vocab = params.get('vocabulary', ["HH", "HL", "LH", "LL", "BOS_UP", "BOS_DN", "CHOCH_UP", "CHOCH_DN", "FAKE_BOS"])
        
        frac_params = config.get('fractal_params', {})
        self.vol_threshold = frac_params.get('volume_multiplier_threshold', 1.2)
        self.ma_vol_period = frac_params.get('ma_volume_period', 20)

    def tokenize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Input: DataFrame đã chạy qua FractalDetector
        Output: Thêm cột 'market_structure_token'
        """
        df_out = df.copy()
        
        # Check required columns
        for col in ['is_fh_confirmed', 'is_fl_confirmed', 'close']:
            if col not in df_out.columns:
                raise ValueError(f"Missing required column: {col}")
                
        # Calculate Volume MA
        if 'volume' in df_out.columns:
            # Shift 1 để tính MA từ nến trước, tránh MA bị ảnh hưởng bởi nến hiện tại (nguyên tắc Engineer)
            df_out['vol_ma'] = df_out['volume'].shift(1).rolling(window=self.ma_vol_period).mean()
            df_out['is_vol_spike'] = df_out['volume'] > (df_out['vol_ma'] * self.vol_threshold)
        else:
            df_out['is_vol_spike'] = True

        tokens = []
        
        last_fh = -np.inf
        last_fl = np.inf
        prev_fh = -np.inf
        prev_fl = np.inf

        for idx, row in df_out.iterrows():
            token = None
            
            # Xử lý Fractal High
            if row.get('is_fh_confirmed', False) and not pd.isna(row.get('fractal_high_val')):
                current_fh = row['fractal_high_val']
                if current_fh > last_fh:
                    token = "HH"
                else:
                    token = "LH"
                prev_fh = last_fh
                last_fh = current_fh
                
            # Xử lý Fractal Low
            elif row.get('is_fl_confirmed', False) and not pd.isna(row.get('fractal_low_val')):
                current_fl = row['fractal_low_val']
                if current_fl > last_fl:
                    token = "HL"
                else:
                    token = "LL"
                prev_fl = last_fl
                last_fl = current_fl
            
            # Xử lý Breakout Up
            elif last_fh != -np.inf and row['close'] > last_fh:
                if row['is_vol_spike']:
                    if last_fl < prev_fl: # Trước đó tạo LL -> Giờ phá đỉnh -> CHOCH_UP
                        token = "CHOCH_UP"
                    else:
                        token = "BOS_UP"
                else:
                    token = "FAKE_BOS"
                last_fh = np.inf # Xóa cản
                
            # Xử lý Breakout Down
            elif last_fl != np.inf and row['close'] < last_fl:
                if row['is_vol_spike']:
                    if last_fh > prev_fh: # Trước đó tạo HH -> Giờ phá đáy -> CHOCH_DN
                        token = "CHOCH_DN"
                    else:
                        token = "BOS_DN"
                else:
                    token = "FAKE_BOS"
                last_fl = -np.inf # Xóa cản
            
            tokens.append(token)
            
        df_out['market_structure_token'] = tokens
        return df_out
