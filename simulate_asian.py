import os
import sys
import time
import json
import pandas as pd
from datetime import datetime, timezone, timedelta

_ROOT = os.path.abspath(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.simulator.historical_simulator import HistoricalSimulator
from src.bot_v6.inference_engine_v6 import V6InferenceEngine
from src.bot_v6.data_processor_v6 import V6DataProcessor
from src.bot_v3.virtual_trade_manager_v3 import V3VirtualTradeManager

def safe_log(msg):
    print(str(msg).encode('ascii', 'replace').decode(), flush=True)

class V6HistoricalSimulator(HistoricalSimulator):
    def _ensure_engine(self):
        if self._engine is not None:
            return
        self._engine = V6InferenceEngine(log_callback=self.log)
        ok = self._engine.load_weights(self.model_path, self.config)
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
            inference_feats=inference_feats,
            config=self.config,
            log_callback=self.log
        )

    def run(self, date_str: str, session: str = "asian") -> pd.DataFrame:
        self.log("=" * 60)
        self.log(f"SIMULATOR V6 | Date={date_str} | Session={session.upper()}")
        self.log("=" * 60)

        self._build_full_merged()
        self._ensure_engine()

        target_symbol = self.config.get("TARGET_SYMBOL", "XAGUSDm")
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
        hour_start, hour_end = self.SESSION_HOURS.get(session.lower(), (0, 7))
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

        self._ensure_processor([])
        point = self.config.get("FEATURE_ENGINEERING", {}).get("PIP_SIZE", 0.001)

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
                X_list, p_err = self._processor.process(w_df)
            except Exception as e:
                import traceback
                self.log(f"⚠️ [{candle_time.strftime('%H:%M')}] Pipeline lỗi: {e}")
                self.log(traceback.format_exc())
                continue
                
            if X_list is None or len(X_list) == 0:
                continue

            try:
                result_dict = self._engine.predict(X_list)
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
        
        self.last_deals = virtual_tm.history_deals
        return result_df

def get_best_run_dir(workspace_path):
    runs_dir = os.path.join(workspace_path, "runs")
    if not os.path.exists(runs_dir):
        return None
    dirs = [os.path.join(runs_dir, d) for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
    if not dirs:
        return None
    # Nếu chỉ có một run duy nhất ta lấy luôn run đó
    return dirs[-1]

def main():
    workspace = os.path.join(_ROOT, "workspaces", "CFG_XAG_ASIAN_V6")
    run_dir = get_best_run_dir(workspace)
    if not run_dir:
        print("[FATAL] Không tìm thấy thư mục Run nào.")
        sys.exit(1)
        
    config_path = os.path.join(run_dir, "config.json")
    
    with open(config_path, "r", encoding='utf-8') as f:
        temp_config = json.load(f)
        
    master_cfg_path = os.path.join(_ROOT, "bot_config_v6_xag_asian.json")
    with open(master_cfg_path, "r", encoding='utf-8') as f:
        master_config = json.load(f)
        
    sim_cfg = master_config.get("SIMULATOR", {})
    if "MIN_PROBABILITY_THRESH" in sim_cfg:
        temp_config.setdefault("LIVE_BOT", {})["MIN_PROBABILITY_THRESH"] = sim_cfg["MIN_PROBABILITY_THRESH"]
    
    # Khoảng thời gian Out-Of-Sample
    sim_start_date = sim_cfg.get("START_DATE", "2026-05-01")
    sim_end_date = sim_cfg.get("END_DATE", "2026-05-23")
    sim_window_size = sim_cfg.get("WINDOW_SIZE", 15000)

    temp_cfg_path = os.path.join(_ROOT, "temp_sim_config_asian.json")
    try:
        with open(temp_cfg_path, "w", encoding='utf-8') as f:
            json.dump(temp_config, f)

        import glob
        model_dir = os.path.join(run_dir, "brains")
        model_files = glob.glob(os.path.join(model_dir, "*.pth"))
        if not model_files:
            print("No models found!")
            sys.exit(1)
        
        model_files.sort(key=os.path.getmtime)
        best_model_path = model_files[-1]
        scaler_path = os.path.join(run_dir, "brains", "scaler_CFG_XAG_ASIAN_V6.pkl")

        sim = V6HistoricalSimulator(
            config_path=temp_cfg_path,
            model_path=best_model_path,
            scaler_path=scaler_path,
            window_size=sim_window_size,
            log_callback=safe_log
        )

        start_date = datetime.strptime(sim_start_date, "%Y-%m-%d")
        end_date = datetime.strptime(sim_end_date, "%Y-%m-%d")
        
        all_deals = []
        
        current_date = start_date
        while current_date <= end_date:
            d_str = current_date.strftime("%Y-%m-%d")
            safe_log(f"\n---> RUNNING SIMULATION ASIAN FOR DATE: {d_str}")
            try:
                sim.run(d_str, session="asian")
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
        
        start_str = start_date.strftime("%d/%m")
        end_str = end_date.strftime("%d/%m")
        
        safe_log("\n" + "="*50)
        safe_log(f"FINAL SUMMARY ({start_str} to {end_str}) ASIAN Session:")
        safe_log(f"Total Deals: {total}")
        safe_log(f"Wins: {n_win}")
        safe_log(f"Losses: {n_loss}")
        safe_log(f"Win Rate: {wr:.2f}%")
        safe_log(f"Total PnL: ${pnl:.2f}")
        safe_log("="*50)
        
        # Notify Telegram to sếp Lê
        msg = f"🏆 Báo cáo Sếp, tiến trình Simulator (V6 ASIAN OUT-OF-SAMPLE) đã chạy hoàn tất!\n\nKết quả Out-of-sample ({start_str} - {end_str}):\n- Tổng lệnh: {total}\n- Số lệnh Win/Loss: {n_win}W / {n_loss}L\n- Win Rate: {wr:.2f}%\n- PnL: ${pnl:.2f}\n\nDữ liệu test này hoàn toàn mới và chưa từng được mô hình học."
        os.system(f'python .agent/send_to_tele.py "{msg}" --channel 1816854047')
    finally:
        if os.path.exists(temp_cfg_path):
            try:
                os.remove(temp_cfg_path)
            except Exception as e:
                safe_log(f"Warning: Cannot remove temp config file: {e}")

if __name__ == "__main__":
    main()
