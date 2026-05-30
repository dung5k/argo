import os
import sys
import time
import json
import subprocess
import pandas as pd
from datetime import datetime, timezone, timedelta

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.simulator.historical_simulator import HistoricalSimulator
from src.bot_v6.inference_engine_v6 import V6InferenceEngine
from src.bot_v6.data_processor_v6 import V6DataProcessor
from src.bot_v3.virtual_trade_manager_v3 import V3VirtualTradeManager

def safe_log(msg):
    print(str(msg).encode('ascii', 'replace').decode(), flush=True)

def process_one_candle_standalone(candle_time, close_price, window_df, config, scaler_path):
    from src.bot_v6.data_processor_v6 import V6DataProcessor
    global _local_processor
    if '_local_processor' not in globals():
        _local_processor = V6DataProcessor(scaler_path, [], config, log_callback=lambda x: None)
    
    try:
        X_list, _ = _local_processor.process(window_df)
        return candle_time, close_price, X_list
    except Exception as e:
        import traceback
        safe_log(f"Process Exception at {candle_time}: {e}")
        safe_log(traceback.format_exc())
        return candle_time, close_price, None

class V6HistoricalSimulator(HistoricalSimulator):
    def _ensure_engine(self):
        if self._engine is not None:
            return
        self._engine = V6InferenceEngine(log_callback=self.log)
        mtf_configs = self.config.get("FEATURE_ENGINEERING", {}).get("MTF_INPUTS", [])
        import joblib
        input_dims = []
        if os.path.exists(self.scaler_path):
            try:
                bundle = joblib.load(self.scaler_path)
                if isinstance(bundle, dict) and 'column_orders' in bundle:
                    input_dims = [len(order) for order in bundle['column_orders']]
            except Exception as e:
                self.log(f"⚠️ Error loading scaler for input_dims: {e}")
        
        if not input_dims:
            input_dims = [len(tf.get("FEATURES", [])) for tf in mtf_configs]
            
        seq_lens = [tf.get("WINDOW_SIZE", 60) for tf in mtf_configs]
        train_cfg = self.config.get("TRAINING", {})
        d_model = train_cfg.get("D_MODEL", 128)
        nhead = train_cfg.get("N_HEAD", 8)
        num_attn_layers = train_cfg.get("NUM_LAYERS", 4)
        ok = self._engine.load_weights(self.model_path, input_dims=input_dims, seq_lens=seq_lens, d_model=d_model, nhead=nhead, num_attn_layers=num_attn_layers)
        if not ok:
            raise RuntimeError("Cannot load V6 weights!")
        bot_cfg = self.config.get("LIVE_BOT", {})
        raw_mse_thr = bot_cfg.get("MAX_ABSOLUTE_MSE", None)
        if raw_mse_thr is None or raw_mse_thr <= 1.0:
            self._engine.mse_threshold = 99999.0
        else:
            self._engine.mse_threshold = raw_mse_thr
        self._engine.prob_threshold = bot_cfg.get("MIN_PROBABILITY_THRESH", 0.53)

    def _ensure_processor(self, inference_feats):
        if self._processor is not None:
            return
        self._processor = V6DataProcessor(
            scaler_path=self.scaler_path,
            config=self.config,
            log_callback=self.log
        )

    def run(self, date_str: str, session: str = "asian") -> pd.DataFrame:
        self.log("=" * 60)
        self.log(f"SIMULATOR V6 | Date={date_str} | Session={session.upper()}")
        self.log("=" * 60)

        self._build_full_merged()
        self._ensure_engine()

        target_symbol = self.config.get("TARGET_SYMBOL", "LTCUSDm")
        sim_symbol = f"SIM_{target_symbol}"
        virtual_tm = V3VirtualTradeManager(
            target_symbol=sim_symbol,
            config=self.config,
            log_callback=self.log,
            tg_notify_callback=lambda x: None,
        )
        virtual_tm.active_trade_loggers = {}
        virtual_tm.history_deals = []
        virtual_tm.virtual_balance = 10000.0
        virtual_tm.last_close_time = 0

        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        hour_start, hour_end = self.SESSION_HOURS.get(session.lower(), (0, 24))
        session_start = target_date + timedelta(hours=hour_start)
        session_end = target_date + timedelta(hours=hour_end)

        target_col = f"{self.target_prefix}_close"
        if target_col not in self._merged_full.columns:
            candidates = [c for c in self._merged_full.columns if "close" in c.lower()]
            target_col = candidates[0] if candidates else None

        session_df = self._merged_full[
            (self._merged_full.index >= session_start) &
            (self._merged_full.index <  session_end) &
            (self._merged_full[target_col].notna())
        ]
        
        self.log(f"DEBUG: session={session.lower()} start={session_start} end={session_end} target_col={target_col} len={len(session_df)}")

        if len(session_df) == 0:
            return pd.DataFrame()

        # V6 uses num_features from dict if needed, or we just pass empty list to inference_feats
        self._ensure_processor([])
        point = self.config.get("FEATURE_ENGINEERING", {}).get("PIP_SIZE", 0.01)

        results = []
        candle_times = session_df.index.tolist()
        
        self.log(f"Extracting features and Replaying {len(candle_times)} candles sequentially...")
        
        for candle_time in candle_times:
            close_price = session_df.loc[candle_time, target_col]
            
            virtual_tm.sim_clock = candle_time.timestamp()
            virtual_tm.update_virtual_positions(current_bid=close_price, current_ask=close_price, point=point)

            w_df = self.fetch_history_for_candle(candle_time)
            if w_df is None:
                continue
                
            try:
                ok, X_list = self._processor.process_online([w_df] * len(self._processor.tf_configs))
                if not ok:
                    X_list = None
            except Exception as e:
                import traceback
                self.log(f"⚠️ [{candle_time.strftime('%H:%M')}] Pipeline lỗi: {e}")
                self.log(traceback.format_exc())
                continue
                
            if X_list is None or len(X_list) == 0:
                continue

            try:
                probs = self._engine.predict_probs(X_list)
                if probs is None:
                    continue
                p_sell, p_hold, p_buy = probs
                action_code = 1
                if p_buy >= getattr(self._engine, "prob_threshold", 0.55):
                    action_code = 2
                elif p_sell >= getattr(self._engine, "prob_threshold", 0.55):
                    action_code = 0
                result_dict = {"action": action_code, "mse": 0.0, "raw": [p_sell, p_hold, p_buy]}
            except Exception as e:
                import traceback
                self.log(f"⚠️ [{candle_time.strftime('%H:%M')}] Inference lỗi: {e}")
                self.log(traceback.format_exc())
                continue
                
            action_code = result_dict.get("action", 1)
            mse = result_dict.get("mse", 0.0)
            raw = result_dict.get("raw", [0.0, 0.0, 0.0])
            
            action_str = "HOLD"
            if action_code == 2:
                action_str = "BUY"
            elif action_code == 0:
                action_str = "SELL"
                
            probs_dict = {"buy": raw[2] if action_code == 2 else 0.0, 
                          "sell": raw[0] if action_code == 0 else 0.0}

            virtual_tm.execute_trade(
                action=action_str,
                probs_dict=probs_dict,
                mse_loss=mse,
                current_bid=close_price,
                current_ask=close_price,
                point=point,
                actual_target_sym=target_symbol,
            )

            results.append({
                "time": candle_time, "close": close_price, "action": action_str, 
                "gui_action": virtual_tm.gui_action, "buy_prob": probs_dict.get("buy", 0), 
                "sell_prob": probs_dict.get("sell", 0), "mse": mse,
            })

            if action_str in ("BUY", "SELL"):
                self.log(f"[{candle_time.strftime('%H:%M')}] {action_str} -> {virtual_tm.gui_action}")

        result_df = pd.DataFrame(results)
        self._print_summary(virtual_tm, result_df, date_str, session)
        
        # Injected code to return deals for global tracking
        self.last_deals = virtual_tm.history_deals
        return result_df


def get_best_run_dir(workspace_path):
    runs_dir = os.path.join(workspace_path, "runs")
    valid_runs = []
    if os.path.exists(runs_dir):
        for run_name in os.listdir(runs_dir):
            run_path = os.path.join(runs_dir, run_name)
            if not os.path.isdir(run_path): continue
            
            # RULE 3: Atomic Auto-Tuning (Check train.log or metrics before picking)
            metrics_path = os.path.join(run_path, "results", "training_metrics_v3.json")
            if not os.path.exists(metrics_path): continue
            
            try:
                with open(metrics_path, "r", encoding="utf-8") as f:
                    metrics = json.load(f)
                
                def extract_score(d):
                    if not isinstance(d, dict): return 0
                    if "composite_score" in d: return d["composite_score"]
                    if "COMPOSITE_SCORE" in d: return d["COMPOSITE_SCORE"]
                    max_s = 0
                    for v in d.values():
                        s = extract_score(v)
                        if s > max_s: max_s = s
                    return max_s
                
                score = extract_score(metrics)
                    
                if score > 0:
                    valid_runs.append((run_path, score))
            except:
                pass
                
    if not valid_runs:
        return None
        
    valid_runs.sort(key=lambda x: x[1])
    return valid_runs[-1][0]


def main():
    workspace = os.path.join(_ROOT, "workspaces", "CFG_XAG_NY_V6")
    run_dir = os.path.join(workspace, "runs", "run_20260530_150747_v6_ny")
    if not os.path.exists(run_dir):
        print("[FATAL] Cannot find Run: ", run_dir)
        sys.exit(1)
        
    config_path = os.path.join(run_dir, "config.json")
    
    with open(config_path, "r", encoding='utf-8') as f:
        temp_config = json.load(f)
    # Set the strict threshold for the simulator matching the Asian session WR
    temp_config.setdefault("LIVE_BOT", {})["MIN_PROBABILITY_THRESH"] = 0.53
    
    # [SIM FIX] Map all 'm' symbols to non-'m' for historical data matching
    target_sym = temp_config.get("TARGET_SYMBOL", "")
    if target_sym.endswith("m") or target_sym.endswith("M"):
        temp_config["TARGET_SYMBOL"] = target_sym[:-1]
        
    target_prefix = temp_config.get("TARGET_PREFIX", "")
    if target_prefix.endswith("m") or target_prefix.endswith("M"):
        temp_config["TARGET_PREFIX"] = target_prefix[:-1]
        
    if "FEATURE_ENGINEERING" in temp_config and "MTF_INPUTS" in temp_config["FEATURE_ENGINEERING"]:
        for tf_cfg in temp_config["FEATURE_ENGINEERING"]["MTF_INPUTS"]:
            sym = tf_cfg.get("SYMBOL", "")
            if sym.endswith("m") or sym.endswith("M"):
                tf_cfg["SYMBOL"] = sym[:-1]
    
    temp_cfg_path = os.path.join(_ROOT, "temp_sim_config_ny.json")

    with open(temp_cfg_path, "w") as f:
        json.dump(temp_config, f)

    import glob
    model_dir = os.path.join(run_dir, "brains")
    model_files = glob.glob(os.path.join(model_dir, "*.pth"))
    if not model_files:
        print("No models found!")
        sys.exit(1)
    
    model_files.sort(key=os.path.getmtime)
    best_model_path = model_files[-1]
    scaler_path = os.path.join(run_dir, "brains", "scaler_CFG_XAG_NY_V6.pkl")

    sim = V6HistoricalSimulator(
        config_path=temp_cfg_path,
        model_path=best_model_path,
        scaler_path=scaler_path,
        window_size=15000,
        log_callback=safe_log
    )

    start_date = datetime(2026, 5, 1)
    end_date = datetime(2026, 5, 30)
    
    all_deals = []
    
    current_date = start_date
    while current_date <= end_date:
        d_str = current_date.strftime("%Y-%m-%d")
        safe_log(f"\n---> RUNNING SIMULATION NY FOR DATE: {d_str}")
        try:
            sim.run(d_str, session="ny")
            if hasattr(sim, 'last_deals'):
                all_deals.extend(sim.last_deals)
        except Exception as e:
            safe_log(f"Error on {d_str}: {e}")
        current_date += timedelta(days=1)
        
    n_win = sum(1 for d in all_deals if d.get("profit", 0) > 0)
    n_loss = sum(1 for d in all_deals if d.get("profit", 0) <= 0)
    total = n_win + n_loss
    wr = n_win / total * 100 if total > 0 else 0
    pnl = sum(d.get("profit", 0) for d in all_deals)
    
    safe_log("\n" + "="*50)
    safe_log("FINAL SUMMARY (2026-05-04 to 2026-05-18) NY Session:")
    safe_log(f"Total Deals: {total}")
    safe_log(f"Wins: {n_win}")
    safe_log(f"Losses: {n_loss}")
    safe_log(f"Win Rate: {wr:.2f}%")
    safe_log(f"Total PnL: ${pnl:.2f}")
    safe_log("="*50)
    
    # Notify Telegram using send_to_tele.py
    msg = f"Báo cáo Sếp Lê, tiến trình Simulator (V6 NY) từ đầu tháng 5 đến nay đã chạy xong hoàn tất!\n\nKết quả (01/05 - 30/05):\n- Tổng lệnh: {total}\n- Số lệnh Win/Loss: {n_win}W / {n_loss}L\n- Win Rate: {wr:.2f}%\n- PnL: ${pnl:.2f}\n\nHệ thống đã sẵn sàng."
    try:
        import subprocess
        subprocess.run([sys.executable, ".agent/send_to_tele.py", msg, "--channel", "1816854047"], check=True)
        safe_log("✅ Đã gửi thông báo kết quả Simulator qua Telegram!")
    except Exception as e:
        safe_log(f"❌ Lỗi khi gửi thông báo Telegram: {e}")

if __name__ == "__main__":
    main()
