import os
import time
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime, timezone
import joblib

from src.core.data_adapters import MT5Adapter, LocalAdapter, BinanceAdapter
import os


class MT5DataManager:
    def __init__(self, log_callback=print, target_sym="XAUUSD", config_path=None):
        self.log_message = log_callback
        self.target_sym = target_sym
        
        import json
        if config_path is None:
            config_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\bot_config_xau.json"
        
        # Absolute path validation
        if not os.path.isabs(config_path):
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), config_path)

        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
                
        # 1. Tự động load MT5 Brokers từ Unified Config
        self.MT5_PATHS = self.config.get("DATA_SOURCE", {}).get("BROKERS", {
            "DEFAULT": r"C:\Program Files\MetaTrader 5\terminal64.exe"
        })
        self.MT5_PATHS["LOCAL"] = "LOCAL" # Giữ nguyên nhãn cho data lấy từ LOCAL
        
        # 2. Xây dựng DATA_SOURCES tự động từ phần ROUTING của Unified Config
        # ROUTING map "Mã" -> "Tên Broker" (VD: "XAUUSDm" -> "EXNESS")
        routing_map = self.config.get("DATA_SOURCE", {}).get("ROUTING", {})
        
        self.DATA_SOURCES = {}
        for sym, broker_key in routing_map.items():
            if broker_key not in self.DATA_SOURCES:
                self.DATA_SOURCES[broker_key] = {}
            
            # Khử tên đuôi .PARQUET của Local nếu có
            sym_clean = sym.replace("m", "").upper()
            if ".PARQUET" in sym_clean:
                sym_clean = sym_clean.replace(".PARQUET", "")
                
            sym_uscore = sym_clean.replace("USD", "_USD")
            self.DATA_SOURCES[broker_key][sym] = [sym_clean, sym_uscore, sym]
        
        self.MT5_FALLBACK_NAMES = {
            "XAUUSDm": ["XAUUSDm", "XAUUSD", "GOLD", "GOLDm", "XAUUSD.a", "XAUUSD_m", "XAUUSD+"],
            "XAGUSDm": ["XAGUSDm", "XAGUSD", "SILVER", "SILVERm", "XAGUSD.a", "XAGUSD+"],
            "XPTUSDm": ["XPTUSDm", "XPTUSD", "PLATINUM", "PLATINUMm", "XPTUSD.a"],
            "XCUUSDm": ["XCUUSDm", "XCUUSD", "COPPER", "COPPERm", "XCUUSD.a"],
            "XALUSDm": ["XALUSDm", "XALUSD", "ALUMINIUM", "ALUMINIUMm"],
            "XNIUSDm": ["XNIUSDm", "XNIUSD", "NICKEL", "NICKELm"],
            "XPDUSDm": ["XPDUSDm", "XPDUSD", "PALLADIUM", "PALLADIUMm"],
            "XPBUSDm": ["XPBUSDm", "XPBUSD", "LEAD", "LEADm"],
            "USDJPYm": ["USDJPYm", "USDJPY", "USDJPY.a"],
            "USDCHFm": ["USDCHFm", "USDCHF", "USDCHF.a"],
            "USDCADm": ["USDCADm", "USDCAD", "USDCAD.a"],
            "EURUSDm": ["EURUSDm", "EURUSD", "EURUSD.a"],
            "GBPUSDm": ["GBPUSDm", "GBPUSD", "GBPUSD.a"],
            "AUDUSDm": ["AUDUSDm", "AUDUSD", "AUDUSD.a"],
            "DXYm":    ["DXYm", "DXY", "USDIDX", "USDX"],
            "USOILm":  ["USOILm", "USOIL", "WTI", "WTIm", "WTICRUDEm", "OIL", "USOIL.a"],
            "UKOILm":  ["UKOILm", "UKOIL", "BRENT", "BRENTm"],
            "XNGUSDm": ["XNGUSDm", "XNGUSD", "NATGAS", "NATGASm", "NG"],
            "US30m":   ["US30m", "US30", "DJ30", "WS30"],
            "US500m":  ["US500m", "US500", "SP500", "SPX500"],
            "USTECm":  ["USTECm", "USTEC", "NAS100", "US100", "NDX100"],
            "JP225m":  ["JP225m", "JP225", "JPN225", "NIY"],
            "VIXYm":   ["VIXYm", "VIXY", "VIX"],
            "BTCUSDm": ["BTCUSDm", "BTCUSD", "BTCUSD.a"],
            "ETHUSDm": ["ETHUSDm", "ETHUSD", "ETHUSD.a"],
        }
        
        self.GLOBAL_MT5_ROUTER_MAP = {}
        self.IN_MEMORY_SYMBOL_HINT = {}
        self.active_mappings = []
        self.features = []
        self.gui_symbols = {}
        self.current_connected_path = None
        
        # --- KHỞI TẠO ADAPTER REGISTRY ---
        self.adapters = {}
        for path_alias, path in self.MT5_PATHS.items():
            if "terminal64.exe" in path:
                self.adapters[path] = MT5Adapter(executable_path=path, log_callback=self.log_message)
            elif path_alias == "LOCAL" or path == "LOCAL":
                script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                self.adapters[path] = LocalAdapter(data_dir=os.path.join(script_dir, "data"), log_callback=self.log_message)
            elif path_alias == "BINANCE" or path == "BINANCE":
                self.adapters[path] = BinanceAdapter(log_callback=self.log_message)
                
        self._load_features()
        self._build_active_mappings()

    def get_front_month_contract(self, continuous_config, target_time=None):
        """Tính toán tên hợp đồng Tương lai đang Active dựa trên thời gian."""
        if continuous_config.get("IS_CFD", False):
            return continuous_config.get("PREFIX") # CFD ghép luôn liên tục không có tháng đáo hạn
            
        months_allowed = continuous_config.get("CONTRACT_MONTHS", ["H", "M", "U", "Z"])
        prefix = continuous_config.get("PREFIX")
        
        now = target_time if target_time else datetime.now()
        year = now.year % 100
        month = now.month
        
        # Chuẩn CME Futures: F=1, G=2, H=3, J=4, K=5, M=6, N=7, Q=8, U=9, V=10, X=11, Z=12
        CME_MONTH_CODES = {
            1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
            7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"
        }
        
        # Tìm hợp đồng front-month trong danh sách cho phép
        # Duyệt từ tháng hiện tại trở đi, chọn tháng đầu tiên có trong CONTRACT_MONTHS
        for offset in range(12):
            check_month = ((month - 1 + offset) % 12) + 1
            check_year = year + ((month - 1 + offset) // 12)
            check_code = CME_MONTH_CODES.get(check_month, "M")
            if check_code in months_allowed:
                return f"{prefix}{check_code}{check_year:02d}"
        
        # Fallback
        return f"{prefix}{CME_MONTH_CODES.get(month, 'M')}{year:02d}"


    def _load_features(self):
        # LUÔN LUÔN ưu tiên load EXACT_FEATURES từ file cấu hình! Vì Scaler có thể bị chèn ép của Model khác!
        self.features = self.config.get("FEATURE_ENGINEERING", {}).get("EXACT_FEATURES", [])
        if not self.features:
            try:
                script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                scaler_path = os.path.join(script_dir, "data", "scaler.pkl")
                scaler = joblib.load(scaler_path)
                self.features = list(scaler.feature_names_in_)
            except Exception as e:
                self.log_message(f"⚠️ Không tìm thấy biến từ Scaler.")

    def _build_active_mappings(self):
        self.active_mappings = []
        for source_name, symbol_dict in self.DATA_SOURCES.items():
            for sym_m, mapped_list in symbol_dict.items():
                for mapped_name in mapped_list:
                    if any(f.startswith(f"{mapped_name}_") for f in self.features):
                        self.active_mappings.append((source_name, sym_m, mapped_name))
        
        self.gui_symbols = {}
        for _src, _s, _m in self.active_mappings:
            self.gui_symbols[_s] = (_m, _src)

    def reload_features(self):
        self.log_message("[DATA MANAGER] Đang tải lại File Trọng số (Scaler) và Xây dựng lại lưới dữ liệu...")
        self._load_features()
        self._build_active_mappings()
        self.GLOBAL_MT5_ROUTER_MAP.clear() # Bắt buộc quét lại vì mã mới có thể xuất hiện
        self.log_message(f"[DATA MANAGER] Đã ánh xạ {len(self.active_mappings)} đường dẫn nội bộ.")

    def force_reload_dynamic_features(self, explicit_features: list):
        """Buộc trình quản lý chỉ quét MT5 để cào các mã được Model yêu cầu (Dynamic Load)."""
        self.features = explicit_features
        self._build_active_mappings()
        self.GLOBAL_MT5_ROUTER_MAP.clear()
        self.log_message(f"🌐 [DYNAMIC MANAGER] Đã đồng bộ lưới cào MT5 khớp hoàn toàn với {len(explicit_features)} giác quan của NÃO AI.")

    def scan_terminals_and_map(self):
        if len(self.GLOBAL_MT5_ROUTER_MAP) > 0:
            return # Already scanned

        self.log_message(f" 🌐 [ROUTER-MANAGER] Bắt đầu Định tuyến Đa-Sàn MT5 cho các Sensor Mạng Nơ-ron...")
        
        # Chỉ quét list duy nhất
        needed_syms = set((src, sym) for src, sym, _ in self.active_mappings)
        
        for path_alias, path in self.MT5_PATHS.items():
            # Gom các mã yêu cầu quét trên Path này
            syms_for_this_path = []
            for src, sym in needed_syms:
                if src == path_alias or src == "AUTO":
                    syms_for_this_path.append(sym)
                    
            if not syms_for_this_path:
                continue

            if path_alias == "LOCAL" or path_alias == "BINANCE" or path == "LOCAL" or path == "BINANCE":
                for req_m in syms_for_this_path:
                    self.GLOBAL_MT5_ROUTER_MAP[req_m] = path
                    self.IN_MEMORY_SYMBOL_HINT[req_m] = req_m
                    self.log_message(f"   => Khớp Sensor [{req_m}] vào [{path_alias}] (Không cần check MT5)")
                continue

            mt5.shutdown()
            if mt5.initialize(path=path):
                syms = mt5.symbols_get()
                if syms:
                    avail = {s.name for s in syms}
                    for req_m in syms_for_this_path:
                        if req_m not in self.GLOBAL_MT5_ROUTER_MAP:
                            continuous_config = self.config.get("DATA_SOURCE", {}).get("CONTINUOUS_CONTRACTS", {}).get(req_m)
                            
                            expanded_candidates = {} # Dùng dict để bảo toàn thứ tự add vào (thay cho set)
                            if continuous_config:
                                active_contract = self.get_front_month_contract(continuous_config)
                                active_contract_1digit = active_contract[:-2] + active_contract[-1]
                                expanded_candidates[active_contract] = True
                                expanded_candidates[active_contract + "m"] = True
                                expanded_candidates[active_contract + ".a"] = True
                                expanded_candidates[active_contract_1digit] = True
                                expanded_candidates[active_contract_1digit + "m"] = True
                            else:
                                s_clean = req_m.replace("m", "")
                                candidates = self.MT5_FALLBACK_NAMES.get(req_m, [req_m, s_clean])
                                for c in candidates:
                                    expanded_candidates[c] = True
                                    expanded_candidates[c + "m"] = True
                                    expanded_candidates[c + ".a"] = True
                                    expanded_candidates[c + "+"] = True
                            
                            found_sym = None
                            for c in expanded_candidates.keys():
                                if c in avail:
                                    found_sym = c
                                    break
                                    
                            if found_sym:
                                self.GLOBAL_MT5_ROUTER_MAP[req_m] = path
                                self.IN_MEMORY_SYMBOL_HINT[req_m] = found_sym
                                self.log_message(f"   => Khớp Sensor [{req_m}] vào lưới [{path_alias}] qua mã [{found_sym}]")
        mt5.shutdown()
        self.current_connected_path = None
        self.log_message(f" 🌐 [ROUTER-MANAGER] Quy hoạch xong {len(self.GLOBAL_MT5_ROUTER_MAP)} luồng tín hiệu!")

    def get_live_merged_data_in_memory(self, window=120):
        # Scan if not scanned yet
        self.scan_terminals_and_map()
        
        df_list = []
        path_groups = {}
        
        # Gom nhóm MT5 Paths
        for source_name, sym_m, mapped_name in self.active_mappings:
            path = self.GLOBAL_MT5_ROUTER_MAP.get(sym_m, source_name)
            if path not in path_groups: path_groups[path] = []
            path_groups[path].append((source_name, sym_m, mapped_name))
            
        for p, group in path_groups.items():
            adapter = self.adapters.get(p)
            if not adapter:
                # Tạo fallback adapter tại runtime nếu chưa có
                if p == "LOCAL" or "LOCAL" in group[0][0]:
                    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    adapter = LocalAdapter(data_dir=os.path.join(script_dir, "data"), log_callback=self.log_message)
                    self.adapters[p] = adapter
                elif p == "BINANCE" or "BINANCE" in group[0][0]:
                    adapter = BinanceAdapter(log_callback=self.log_message)
                    self.adapters[p] = adapter
                elif "terminal64.exe" in p:
                    adapter = MT5Adapter(executable_path=p, log_callback=self.log_message)
                    self.adapters[p] = adapter

            for source_name, sym_m, mapped_name in group:
                df = pd.DataFrame()
                if adapter:
                    # Truyền đúng symbol
                    actual_sym = sym_m
                    if isinstance(adapter, MT5Adapter):
                        sym_clean = sym_m.replace("m", "")
                        actual_sym = self.IN_MEMORY_SYMBOL_HINT.get(sym_m, sym_clean)
                        
                    try:
                        df = adapter.fetch_live_data(actual_sym, 'M1', window)
                    except Exception as e:
                        self.log_message(f"⚠️ Lỗi đọc Adapter {p} cho {sym_m}: {e}")

                if df.empty: continue
                
                df['datetime'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('datetime', inplace=True)
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC')
                else:
                    df.index = df.index.tz_convert('UTC')
                    
                df = df[~df.index.duplicated(keep='last')]
                df.drop(columns=['spread', 'time'], inplace=True, errors='ignore')
                df.rename(columns={'tick_volume': 'volume'}, inplace=True)
                
                renamed_df = df.copy()
                rename_map = {}
                for col in renamed_df.columns:
                    if col in ['open', 'high', 'low', 'close', 'volume', 'real_volume', 'spread']:
                        expected = None
                        if f"{mapped_name}_{col}" in self.features or f"{mapped_name}_{col}_log_ret" in self.features:
                            expected = f"{mapped_name}_{col}"
                        elif f"{mapped_name}_{col.capitalize()}" in self.features or f"{mapped_name}_{col.capitalize()}_log_ret" in self.features:
                            expected = f"{mapped_name}_{col.capitalize()}"
                        elif f"{mapped_name}_{col.upper()}" in self.features or f"{mapped_name}_{col.upper()}_log_ret" in self.features:
                            expected = f"{mapped_name}_{col.upper()}"
                        
                        rename_map[col] = expected if expected else f"{mapped_name}_{col}"
                
                renamed_df = renamed_df.rename(columns=rename_map)
                df_list.append(renamed_df)
                        
        merged_df = None
        error_msg = None
        
        if df_list:
            merged_df = pd.concat(df_list, axis=1)
            merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()].copy()
            merged_df.sort_index(inplace=True)
            
            merged_df.ffill(limit=120, inplace=True)
            vol_cols = [c for c in merged_df.columns if 'volume' in c.lower()]
            merged_df[vol_cols] = merged_df[vol_cols].fillna(0)
            
            target_mapped = "XAU_USD"
            for _src, _s, _m in self.active_mappings:
                if self.target_sym in _s or _s.startswith(self.target_sym):
                    target_mapped = _m
                    break
                    
            target_close = f"{target_mapped}_close"
            if target_close not in merged_df.columns:
                target_close = f"{target_mapped}_Close"
                
            if target_close in merged_df.columns:
                merged_df = merged_df.dropna(subset=[target_close])
            else:
                error_msg = f"❌ LỖI: KHÔNG TÌM THẤY MÃ PHÙ HỢP CHO BOT {self.target_sym} (MT5 MẤT KẾT NỐI)!"
                self.log_message(f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
                return None, [], error_msg
                
            if len(merged_df) > 0:
                merged_df.index = merged_df.index.tz_convert('America/New_York')
                from src.core.feature_engineering import add_time_embeddings
                merged_df = add_time_embeddings(merged_df)
                # ĐỂ LẠI NaNs cho FeatureEngineering tự lo (Zero-pad hoặc Drop)), không dropna() tránh mất trắng dữ liệu

        sym_data = self._build_sym_data(merged_df)
        
        return merged_df, sym_data, error_msg

    def _build_sym_data(self, merged_df):
        sym_data = []
        dt_utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        for sym_m, (mapped_name, source_name) in self.gui_symbols.items():
            sym_clean = mapped_name.replace(".PARQUET", "").replace("1H_2025_2026", "").replace("_", "")
            close_col = f"{mapped_name}_close"
            
            if close_col not in (merged_df.columns if merged_df is not None else []):
                close_col = f"{mapped_name}_Close"
                
            if merged_df is not None and len(merged_df) >= 2 and close_col in merged_df.columns:
                last_row = merged_df.iloc[-1]
                prev_row = merged_df.iloc[-2]
                
                p_curr = last_row[close_col]
                p_prev = prev_row[close_col]
                if pd.isna(p_curr) or pd.isna(p_prev):
                    p_curr, p_prev = 0.0, 0.0
            else:
                p_curr, p_prev = 0.0, 0.0
                
            change = p_curr - p_prev
            try:
                dt = merged_df.index[-1]
                diff_mins = (dt_utc_now - dt.tz_convert('UTC')).total_seconds() / 60.0
                dt_vn = dt.tz_convert('Asia/Ho_Chi_Minh')
                time_str = dt_vn.strftime("%H:%M")
            except:
                diff_mins = 0
                time_str = "N/A"
                
            is_delayed = diff_mins > 5
            if p_curr == 0.0 and p_prev == 0.0:
                is_delayed = True
            
            if not any(s[0] == sym_clean for s in sym_data):
                sym_data.append((sym_clean, p_curr, change, time_str, source_name, is_delayed))
                    
                    
        return sym_data
