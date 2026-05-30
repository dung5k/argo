import os
import sys
import time
import json
import argparse
import pandas as pd
from datetime import datetime, timezone, timedelta

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
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
        mtf_configs = self.config.get("FEATURE_ENGINEERING", {}).get("MTF_INPUTS", [])
        input_dims = [len(tf.get("FEATURES", [])) for tf in mtf_configs]
        seq_lens = [tf.get("WINDOW_SIZE", 60) for tf in mtf_configs]
        train_cfg = self.config.get("TRAIN", {})
        d_model = train_cfg.get("D_MODEL", 128)
        nhead = train_cfg.get("NHEAD", 8)
        num_attn_layers = train_cfg.get("NUM_ATTN_LAYERS", 3)
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

    def _load_parquets(self):
        super()._load_parquets()
        # Lọc dữ liệu từ ngày 2026-04-15 trở đi để tiết kiệm RAM tối đa
        cutoff_date = pd.Timestamp("2026-04-15", tz="UTC")
        self.log(f"Filtering parquet dataframes to keep only data after {cutoff_date}...")
        for sym_key in list(self._symbol_dfs.keys()):
            df = self._symbol_dfs[sym_key]
            filtered_df = df[df.index >= cutoff_date]
            self._symbol_dfs[sym_key] = filtered_df
            self.log(f"  {sym_key} filtered: {len(filtered_df):,} rows")

    def run(self, date_str: str, session: str = "asian") -> pd.DataFrame:
        self.log("=" * 60)
        self.log(f"SIMULATOR V6 | Date={date_str} | Session={session.upper()}")
        self.log("=" * 60)

        self._build_full_merged()

        # Duplicate columns to match target_prefix with 'm' (e.g. LTCUSDT -> LTCUSDm)
        target_prefix = self.config.get("TARGET_PREFIX", "LTCUSDT")
        exec_sym = self.config.get("EXECUTION_SYMBOL", "LTCUSDm")
        for col in self._merged_full.columns:
            if target_prefix.lower() in col.lower():
                new_col = col.replace(target_prefix, exec_sym).replace(target_prefix.lower(), exec_sym.lower())
                self._merged_full[new_col] = self._merged_full[col]

        self._ensure_engine()

        target_symbol = exec_sym
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
            candidates = [c for c in self._merged_full.columns if "close" in c.lower() and target_prefix.lower() in c.lower()]
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
                if p_buy >= getattr(self._engine, 'prob_threshold', 0.55):
                    action_code = 2
                elif p_sell >= getattr(self._engine, 'prob_threshold', 0.55):
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
        
        self.last_deals = virtual_tm.history_deals
        return result_df

def get_best_run_dir(workspace_path, run_id):
    runs_dir = os.path.join(workspace_path, "runs")
    if not os.path.exists(runs_dir):
        return None
    target_dir = os.path.join(runs_dir, run_id)
    if os.path.exists(target_dir):
        return target_dir
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", choices=["asian", "london", "ny"], required=True)
    parser.add_argument("--start", default="2026-05-01")
    parser.add_argument("--end", default="2026-05-26")
    parser.add_argument("--notify", action="store_true", help="Send report to Telegram")
    args = parser.parse_args()

    master_cfg_path = os.path.join(_ROOT, f"bot_config_v6_ltc_{args.session}.json")
    if not os.path.exists(master_cfg_path):
        print(f"[FATAL] Cannot find {master_cfg_path}")
        sys.exit(1)

    with open(master_cfg_path, "r", encoding='utf-8') as f:
        master_config = json.load(f)
        
    run_id = master_config.get("RUN_ID", "")
    workspace = os.path.join(_ROOT, "workspaces", f"CFG_LTC_{args.session.upper()}_V6")
    
    run_dir = get_best_run_dir(workspace, run_id)
    if not run_dir:
        print(f"[FATAL] Không tìm thấy thư mục Run: {run_id}")
        sys.exit(1)
        
    config_path = os.path.join(run_dir, "config.json")
    with open(config_path, "r", encoding='utf-8') as f:
        temp_config = json.load(f)
        
    # Ghi đè cấu hình thresh
    if "LIVE_BOT" in master_config and "MIN_PROBABILITY_THRESH" in master_config["LIVE_BOT"]:
        temp_config.setdefault("LIVE_BOT", {})["MIN_PROBABILITY_THRESH"] = master_config["LIVE_BOT"]["MIN_PROBABILITY_THRESH"]
    
    sim_window_size = 2000

    temp_cfg_path = os.path.join(_ROOT, f"temp_sim_config_ltc_{args.session}.json")
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
        scaler_path = os.path.join(run_dir, "brains", f"scaler_CFG_LTC_{args.session.upper()}_V6.pkl")

        sim = V6HistoricalSimulator(
            config_path=temp_cfg_path,
            model_path=best_model_path,
            scaler_path=scaler_path,
            window_size=sim_window_size,
            log_callback=safe_log
        )

        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
        
        all_deals = []
        
        current_date = start_date
        while current_date <= end_date:
            d_str = current_date.strftime("%Y-%m-%d")
            safe_log(f"\n---> RUNNING SIMULATION LTC V6 {args.session.upper()} FOR DATE: {d_str}")
            try:
                sim.run(d_str, session=args.session)
                if hasattr(sim, 'last_deals'):
                    day_deals = sim.last_deals
                    all_deals.extend(day_deals)
                    if args.notify:
                        day_n_win = sum(1 for d in day_deals if d.get("profit", 0) > 0)
                        day_n_loss = sum(1 for d in day_deals if d.get("profit", 0) <= 0)
                        day_total = day_n_win + day_n_loss
                        day_wr = day_n_win / day_total * 100 if day_total > 0 else 0
                        day_pnl = sum(d.get("profit", 0) for d in day_deals)
                        
                        msg = f"⏳ TIẾN ĐỘ GIẢ LẬP LTC V6 {args.session.upper()} | NGÀY: {d_str}\n\n"
                        msg += f"📊 Kết quả ngày:\n"
                        msg += f"- Lệnh trong ngày: {day_total} ({day_n_win}W / {day_n_loss}L)\n"
                        if day_total == 0:
                            msg += "- Không có lệnh nào thoả mãn điều kiện vào lệnh.\n"
                        else:
                            msg += f"- Tỷ lệ thắng ngày: {day_wr:.2f}%\n"
                            msg += f"- PnL ngày: ${day_pnl:.2f}\n"
                        
                        import subprocess
                        subprocess.run(['python', '.agent/send_to_tele.py', msg, '--channel', '1816854047'])
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
        safe_log(f"FINAL SUMMARY ({start_str} to {end_str}) LTC V6 {args.session.upper()}:")
        safe_log(f"Total Deals: {total}")
        safe_log(f"Wins: {n_win}")
        safe_log(f"Losses: {n_loss}")
        safe_log(f"Win Rate: {wr:.2f}%")
        safe_log(f"Total PnL: ${pnl:.2f}")
        safe_log("="*50)
        
        if args.notify:
            msg = f"🔍 KIỂM ĐỊNH MÙ (OUT-OF-SAMPLE) LTC V6 | PHIÊN: {args.session.upper()}\n\n"
            msg += f"🗓 Giai đoạn test: {start_str} - {end_str}\n"
            msg += f"🧠 Run ID: {run_id}\n\n"
            msg += f"📊 KẾT QUẢ THỰC CHIẾN MÔ PHỎNG:\n"
            msg += f"- Tổng số lệnh đánh: {total}\n"
            msg += f"- Số lệnh Thắng/Thua: {n_win}W / {n_loss}L\n"
            msg += f"- Tỷ lệ thắng (Win Rate): {wr:.2f}%\n"
            msg += f"- Lợi nhuận (PnL): ${pnl:.2f}\n\n"
            if wr < 60:
                msg += f"⚠️ BÁO ĐỘNG ĐỎ (DEGRADATION): Win Rate ở tập Out-of-sample quá thấp. Mô hình có dấu hiệu Overfitting nặng!"
            elif wr >= 75:
                msg += f"✅ ĐẠT CHUẨN: Mô hình chịu tải tốt ở dữ liệu tương lai, có thể tự tin đưa vào Paper Trading!"
            else:
                msg += f"⚠️ CHẤP NHẬN ĐƯỢC: Phong độ giảm nhẹ, cần theo dõi thêm khi Paper Trading."

            import subprocess
            subprocess.run(['python', '.agent/send_to_tele.py', msg, '--channel', '1816854047'])
            
    finally:
        if os.path.exists(temp_cfg_path):
            try:
                os.remove(temp_cfg_path)
            except Exception as e:
                safe_log(f"Warning: Cannot remove temp config file: {e}")

if __name__ == "__main__":
    main()
