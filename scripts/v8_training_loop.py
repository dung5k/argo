import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:32'
import sys
import json
import argparse
import glob
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader

# Force UTF-8 encoding for stdout/stderr to prevent crash on ARGO2
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder
from datetime import timedelta

# Load M1 Data globally
print("Loading M1 Tick Data for Training Loop Validation...")
df_m1 = pd.read_parquet("data/XAUUSDm_M1_2024_2026.parquet")
print("M1 Data loaded.")

def get_args():
    parser = argparse.ArgumentParser(description="V8 Training Loop")
    parser.add_argument("--node_id", type=str, default="ARGO1", help="Node Name")
    parser.add_argument("--layers", type=int, default=3, help="Number of Transformer Layers")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning Rate")
    parser.add_argument("--epochs", type=int, default=10, help="Epochs per split")
    parser.add_argument("--batch_size", type=int, default=0, help="Batch size (0 = use config default)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--opt_id", type=str, default="", help="AutoML Option ID for logging")
    parser.add_argument("--base_timeframe", type=str, default="", help="Override base timeframe (M5 or M15)")
    return parser.parse_args()

def main():
    args = get_args()
    log_suffix = f"_{args.opt_id}" if args.opt_id else ""
    log_file = os.path.join("logs", f"v8_train_{args.node_id}{log_suffix}.log")
    os.makedirs("logs", exist_ok=True)
    
    def log(msg):
        try:
            print(msg, flush=True)
        except UnicodeEncodeError:
            print(msg.encode('ascii', 'replace').decode('ascii'), flush=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
            
    if not args.resume and os.path.exists(log_file):
        try:
            os.remove(log_file)
        except PermissionError:
            pass # Ignore if file is locked
            
    mode_str = "RESUMING" if args.resume else "STARTING FRESH"
    log(f"=== {mode_str} V8 TRAINING ON {args.node_id} ===")
    log(f"Config: Layers={args.layers}, LR={args.lr}, Epochs={args.epochs}")
    
    config_path = "v8_configs/v8_training_config.json"
    if not os.path.exists(config_path):
        log("Config not found!")
        return
        
    # Doc cau hinh
    with open("v8_configs/v8_training_config.json", "r", encoding="utf-8-sig") as f:
        config = json.load(f)
        
    if args.base_timeframe:
        if 'system' not in config:
            config['system'] = {}
        config['system']['base_timeframe'] = args.base_timeframe
        
    base_freq = config.get('system', {}).get('base_timeframe', 'M5')
        
    config['transformer_params']['num_layers'] = args.layers
    
    model = V8TransformerModel(config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        log("CRITICAL ERROR: CUDA GPU is not available! OS or environment restriction detected. Forcing crash as requested.")
        raise RuntimeError("GPU is required but not available. Check CUDA/WDDM setup.")
        
    model.to(device)
    
    # === DYNAMIC BATCH SIZE: Tu dong dieu chinh theo VRAM con trong ===
    def calculate_batch_size():
        """Tinh batch_size dua tren VRAM con trong. Toi uu hoa toan bo GPU cho training."""
        if args.batch_size > 0:
            return args.batch_size  # CLI override, khong tu dong
        
        try:
            total_mem = torch.cuda.get_device_properties(0).total_mem
            free_mem = total_mem - torch.cuda.memory_allocated(0) - torch.cuda.memory_reserved(0)
            # Dung nvidia-smi de lay VRAM that su con trong (bao gom app khac)
            import subprocess as _sp
            result = _sp.run(
                ['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                free_mb = int(result.stdout.strip().split('\n')[0])
            else:
                free_mb = free_mem / (1024 * 1024)
        except Exception:
            free_mb = 2048  # Fallback: gia dinh 2GB

        # Quy tac: du tru 200MB cho he thong (khong con game/app nang)
        usable_mb = max(free_mb - 200, 256)
        
        if usable_mb >= 5000:
            bs = 64
        elif usable_mb >= 3500:
            bs = 48
        elif usable_mb >= 2500:
            bs = 32
        elif usable_mb >= 1500:
            bs = 16
        elif usable_mb >= 800:
            bs = 8
        elif usable_mb >= 400:
            bs = 4
        else:
            bs = 2
        
        return bs

    bs = calculate_batch_size()
    log(f"Using device: {device} | GPU: {torch.cuda.get_device_name(0)}")
    try:
        total_gb = torch.cuda.get_device_properties(0).total_mem / (1024**3)
        import subprocess as _sp2
        result = _sp2.run(
            ['nvidia-smi', '--query-gpu=memory.free,memory.used', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(',')
            free_mb = int(parts[0].strip())
            used_mb = int(parts[1].strip())
            log(f"GPU VRAM: {total_gb:.1f}GB total | {free_mb}MB free | {used_mb}MB used (by other apps)")
        else:
            log(f"GPU VRAM: {total_gb:.1f}GB total")
    except Exception:
        pass
    log(f"Batch size: {bs} (tu dong dieu chinh theo VRAM con trong)")

    
    # Đọc cấu hình Auto-ML
    strategy_config_path = "v8_configs/strategy_config.json"
    strat_lr = args.lr
    loss_fn_name = "CrossEntropyLoss"
    if os.path.exists(strategy_config_path):
        try:
            with open(strategy_config_path, "r", encoding="utf-8-sig") as f:
                strat_cfg = json.load(f)
                strat_lr = strat_cfg.get("learning_rate_base", strat_lr)
                loss_fn_name = strat_cfg.get("loss_function", loss_fn_name)
        except Exception as e:
            log(f"Lỗi đọc strategy_config.json: {e}")
            
    # Class weights: inverse of class proportions (15%, 10%, 50%, 10%, 15%)
    # Boost learning on rare but important Strong signals
    class_weights = torch.tensor([1.0/0.15, 1.0/0.10, 1.0/0.50, 1.0/0.10, 1.0/0.15]).to(device)
    class_weights = class_weights / class_weights.sum() * 5.0  # normalize to sum=5
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
    log(f"Using Weighted CrossEntropyLoss (label_smoothing=0.1, weights={[f'{w:.2f}' for w in class_weights.tolist()]})")
        
    optimizer = optim.AdamW(model.parameters(), lr=strat_lr, weight_decay=1e-3)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    
    checkpoint_path = os.path.join("v8_configs", f"checkpoint_{args.node_id}.pt")
    best_model_path = os.path.join("v8_configs", f"best_model_{args.node_id}.pt")
    # Luu rieng theo OPT ID de khong bi ghi de
    final_model_path = os.path.join("v8_configs", f"best_model_{args.node_id}_{args.opt_id}.pt")
    
    start_split_idx = 0
    start_epoch = 0
    best_loss = float('inf')
    
    if args.resume and os.path.exists(checkpoint_path):
        try:
            log(f"Loading checkpoint from {checkpoint_path}...")
            try:
                checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
            except TypeError:
                checkpoint = torch.load(checkpoint_path, map_location=device)
            model.load_state_dict(checkpoint['model_state'])
            optimizer.load_state_dict(checkpoint['optimizer_state'])
            if 'scheduler_state' in checkpoint:
                scheduler.load_state_dict(checkpoint['scheduler_state'])
            start_split_idx = checkpoint['split_idx']
            start_epoch = checkpoint['epoch'] + 1 # Start from next epoch
            best_loss = checkpoint['best_loss']
            log(f"Resumed at Split Index {start_split_idx}, Epoch {start_epoch}")
        except Exception as e:
            log(f"[WARNING] Loi khi load checkpoint: {e}. Se bat dau lai tu dau!")
            start_split_idx = 0
            start_epoch = 0
            best_loss = float('inf')
        
    elif not args.resume:
        # Clear old checkpoints if starting fresh
        if os.path.exists(checkpoint_path): os.remove(checkpoint_path)
        if os.path.exists(best_model_path): os.remove(best_model_path)
    
    splits_dir = "data/v8_splits"
    if not os.path.exists(splits_dir):
        log(f"No splits found in {splits_dir}")
        return
        
    train_files = sorted(
        glob.glob(os.path.join(splits_dir, "*_train.parquet")),
        key=lambda x: int(os.path.basename(x).split('_')[1]) if '_' in os.path.basename(x) else 0
    )
    if len(train_files) == 0:
        log("No training data found.")
        return
        
    log(f"Found {len(train_files)} walk-forward splits.")
    
    consecutive_bad_splits = 0
    max_bad_splits = 3  # Dừng sau 3 split liên tiếp không có lợi thế
    
    for split_idx in range(start_split_idx, len(train_files)):
        train_file = train_files[split_idx]
        split_id = train_file.split("split_")[1].split("_train")[0]
        test_file = train_file.replace("_train.parquet", "_test.parquet")
        
        if start_epoch == 0:
            log(f"--- Processing Split {split_id} ---")
            
        df_train_m1 = pd.read_parquet(train_file)
        df_test_m1 = pd.read_parquet(test_file)
        
        base_tf_cfg = config.get("system", {}).get("base_timeframe", "M15")
        if base_tf_cfg == "M5":
            base_freq, mid_freq, high_freq = "5min", "15min", "1h"
        else:
            base_freq, mid_freq, high_freq = "15min", "1h", "4h"
            
        def resample_df(df_m1, freq):
            if 'tick_volume' in df_m1.columns and 'volume' not in df_m1.columns:
                df_m1 = df_m1.rename(columns={'tick_volume': 'volume'})
            return df_m1.resample(freq).agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
        df_train_base = resample_df(df_train_m1, base_freq)
        df_train_mid = resample_df(df_train_m1, mid_freq)
        df_train_high = resample_df(df_train_m1, high_freq)
        
        train_dataset = V8DatasetBuilder(config, df_train_base, df_train_mid, df_train_high)
        train_loader = DataLoader(train_dataset, batch_size=bs, shuffle=True)
        
        df_test_base = resample_df(df_test_m1, base_freq)
        df_test_mid = resample_df(df_test_m1, mid_freq)
        df_test_high = resample_df(df_test_m1, high_freq)
        
        test_dataset = V8DatasetBuilder(config, df_test_base, df_test_mid, df_test_high, label_thresholds=train_dataset.thresholds)
        test_loader = DataLoader(test_dataset, batch_size=bs, shuffle=False)
        
        # Reset best_loss per split? Or keep global? Walk-forward usually optimizes per split or global
        # Let's keep it global or per split. Usually per split is better for dynamic. But let's reset it per split for saving best model of that split
        if start_epoch == 0:
            best_loss = float('inf')
            # Soft Restarts: Không reset LR về mức tối đa để tránh Catastrophic Forgetting
            if split_idx > 0:
                soft_lr = strat_lr / 5.0
                for param_group in optimizer.param_groups:
                    param_group['lr'] = soft_lr
                log(f"--- [Soft Restarts] Phục hồi nhẹ Learning Rate về {soft_lr} cho Split {split_id} ---")
            else:
                for param_group in optimizer.param_groups:
                    param_group['lr'] = strat_lr

            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
        
        split_best_edge = -100.0
        torch.cuda.empty_cache()
        
        for epoch in range(start_epoch, args.epochs):
            model.train()
            total_loss = 0
            
            for x_m15, x_h1, x_h4, cont_x, y in train_loader:
                x_m15, x_h1, x_h4, cont_x, y = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device), y.to(device)
                
                optimizer.zero_grad()
                out = model(x_m15, x_h1, x_h4, cont_x)
                
                loss = criterion(out, y)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                total_loss += loss.item()
                
            model.eval()
            val_loss = 0
            correct_signal = 0
            total_signal = 0
            
            all_probs = []
            all_targets = []
            
            with torch.no_grad():
                for x_m15, x_h1, x_h4, cont_x, y in test_loader:
                    x_m15, x_h1, x_h4, cont_x, y = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device), y.to(device)
                    
                    out = model(x_m15, x_h1, x_h4, cont_x)
                    v_loss = criterion(out, y)
                    val_loss += v_loss.item()
                    
                    probs = torch.softmax(out, dim=1)
                    all_probs.append(probs)
                    all_targets.append(y)
                    
            # Gom toàn bộ Validation Data
            all_probs = torch.cat(all_probs, dim=0)
            all_targets = torch.cat(all_targets, dim=0)
            
            # Lấy min/max để in log
            max_probs = all_probs.max(dim=0)[0]
            min_probs = all_probs.min(dim=0)[0]
            
            total_samples = len(test_dataset)
            total_days = total_samples / 60.0  # 60 candles per session day
            
            # Chi su dung tin hieu Strong Buy (4) va Strong Sell (0) lam tin hieu vao lenh
            prob_s2 = all_probs[:, 0]
            prob_b2 = all_probs[:, 4]
            max_trade_probs, trade_dirs = torch.max(torch.stack([prob_s2, prob_b2], dim=1), dim=1)
            # trade_dirs: 0 = Sell2 (Sell), 1 = Buy2 (Buy)
            
            # Map target ve cung dinh dang huong (0=Sell, 1=Buy, 2=Hold)
            is_target_sell = (all_targets == 0) | (all_targets == 1)
            is_target_buy = (all_targets == 3) | (all_targets == 4)
            target_dir = torch.where(is_target_buy, torch.tensor(1).to(device), 
                            torch.where(is_target_sell, torch.tensor(0).to(device), torch.tensor(2).to(device)))
            
            train_avg = total_loss/len(train_loader) if len(train_loader) > 0 else 0
            val_avg = val_loss/len(test_loader) if len(test_loader) > 0 else 0
            
            current_lr = optimizer.param_groups[0]['lr']
            log(f"Split {split_id} | Ep {epoch+1} | Loss(T/V): {train_avg:.3f}/{val_avg:.3f} | LR: {current_lr:.1e}")
            log(f"  -> Prob [S2]: {min_probs[0]:.4f}~{max_probs[0]:.4f} | [S1]: {min_probs[1]:.4f}~{max_probs[1]:.4f} | [H]: {min_probs[2]:.4f}~{max_probs[2]:.4f} | [B1]: {min_probs[3]:.4f}~{max_probs[3]:.4f} | [B2]: {min_probs[4]:.4f}~{max_probs[4]:.4f}")
            
            # === PnL SIMULATION (Triple-Barrier + ATR) - THUOC DO DUY NHAT ===
            threshold_sim = 0.30   # Tang tu 0.22 -> chi bat lenh xac suat cao
            spread = 0.3           # pip spread XAUUSD (san tot: 0.2-0.5)
            tp_mult = 3.0          # TP = 3.0 x ATR (R:R = 2:1)
            sl_mult = 1.5          # SL = 1.5 x ATR
            max_hold = 12          # Toi da 12 nen M15 = 3 tieng
            cooldown = 4           # Cho 4 nen sau khi dong lenh
            
            signal_mask_sim = max_trade_probs >= threshold_sim
            valid_df = test_dataset.valid_df
            n_samples = len(valid_df)
            
            wins = 0
            losses = 0
            scratches = 0
            total_pnl = 0.0
            trade_results = []
            trade_positions = []
            consecutive_losses = 0
            max_consec_losses = 0
            max_drawdown = 0.0
            equity_peak = 0.0
            equity = 0.0
            
            next_allowed = 0
            
            for idx in range(n_samples):
                if idx < next_allowed:
                    continue
                if not signal_mask_sim[idx]:
                    continue
                if idx + max_hold >= n_samples:
                    continue
                    
                entry_time = valid_df.index[idx]
                # Chỉ cho phép vào lệnh trước khi đóng NY 1 tiếng (8:00 - 21:59)
                if entry_time.hour >= 22 or entry_time.hour < 8:
                    continue
                    
                row = valid_df.iloc[idx]
                entry_price = row['close']
                atr_val = row.get('atr', 1.5)
                if atr_val <= 0 or np.isnan(atr_val):
                    atr_val = 1.5
                
                direction = trade_dirs[idx].item()
                
                tp_dist = atr_val * tp_mult
                sl_dist = atr_val * sl_mult
                
                if direction == 1:  # BUY
                    real_entry = entry_price + spread / 2
                    tp_price = real_entry + tp_dist
                    sl_price = real_entry - sl_dist
                else:  # SELL
                    real_entry = entry_price - spread / 2
                    tp_price = real_entry - tp_dist
                    sl_price = real_entry + sl_dist
                
                result = 'scratch'
                pnl = 0.0
                close_candle = idx + max_hold
                
                # M1 Evaluation Window
                start_m1 = entry_time + timedelta(minutes=15)
                end_m1 = start_m1 + timedelta(minutes=max_hold * 15)
                
                trade_m1 = df_m1.loc[start_m1:end_m1]
                
                if not trade_m1.empty:
                    m1_times = trade_m1.index
                    m1_highs = trade_m1['high'].values
                    m1_lows = trade_m1['low'].values
                    m1_closes = trade_m1['close'].values
                    
                    for i in range(len(m1_times)):
                        m1_time = m1_times[i]
                        fh = m1_highs[i]
                        fl = m1_lows[i]
                        
                        # Đóng lệnh cưỡng bức khi kết thúc phiên NY (23:00)
                        if m1_time.hour >= 23 or m1_time.hour < 8:
                            result = 'scratch'
                            pnl = (m1_closes[i] - real_entry) if direction == 1 else (real_entry - m1_closes[i])
                            minutes_passed = (m1_time - entry_time).total_seconds() / 60
                            close_candle = idx + int(minutes_passed // 15)
                            break
                            
                        if direction == 1:
                            if fl <= sl_price:
                                result = 'loss'
                                pnl = -sl_dist
                                minutes_passed = (m1_time - entry_time).total_seconds() / 60
                                close_candle = idx + int(minutes_passed // 15)
                                break
                            if fh >= tp_price:
                                result = 'win'
                                pnl = tp_dist
                                minutes_passed = (m1_time - entry_time).total_seconds() / 60
                                close_candle = idx + int(minutes_passed // 15)
                                break
                        else:
                            if fh >= sl_price:
                                result = 'loss'
                                pnl = -sl_dist
                                minutes_passed = (m1_time - entry_time).total_seconds() / 60
                                close_candle = idx + int(minutes_passed // 15)
                                break
                            if fl <= tp_price:
                                result = 'win'
                                pnl = tp_dist
                                minutes_passed = (m1_time - entry_time).total_seconds() / 60
                                close_candle = idx + int(minutes_passed // 15)
                                break
                
                if result == 'scratch':
                    # Kiểm tra đóng lệnh cưỡng bức tại cấp nến M15
                    for h_idx in range(idx + 1, close_candle + 1):
                        if h_idx >= n_samples:
                            break
                        check_time = valid_df.index[h_idx]
                        if check_time.hour >= 23 or check_time.hour < 8:
                            close_candle = h_idx
                            break
                    close_candle = min(close_candle, n_samples - 1)
                    close_price = valid_df.iloc[close_candle]['close']
                    if direction == 1:
                        pnl = close_price - real_entry
                    else:
                        pnl = real_entry - close_price
                
                next_allowed = close_candle + cooldown
                
                if result == 'win':
                    wins += 1
                    consecutive_losses = 0
                elif result == 'loss':
                    losses += 1
                    consecutive_losses += 1
                    max_consec_losses = max(max_consec_losses, consecutive_losses)
                else:
                    scratches += 1
                    if pnl < 0:
                        consecutive_losses += 1
                        max_consec_losses = max(max_consec_losses, consecutive_losses)
                    else:
                        consecutive_losses = 0
                
                total_pnl += pnl
                equity += pnl
                equity_peak = max(equity_peak, equity)
                current_dd = equity_peak - equity
                max_drawdown = max(max_drawdown, current_dd)
                
                trade_results.append(pnl)
                trade_positions.append(idx)
            
            total_trades = wins + losses + scratches
            trades_per_day = total_trades / total_days if total_days > 0 else 0
            
            if total_trades > 0:
                gross_win = sum(p for p in trade_results if p > 0)
                gross_loss = abs(sum(p for p in trade_results if p < 0))
                pf = gross_win / gross_loss if gross_loss > 0 else 999.0
                real_wr = wins / total_trades * 100
                
                quarter = n_samples // 4
                q_counts = [0, 0, 0, 0]
                for pos in trade_positions:
                    qi = min(pos // quarter, 3) if quarter > 0 else 0
                    q_counts[qi] += 1
                dist_std = np.std(q_counts)
                dist_str = f"Q1:{q_counts[0]}|Q2:{q_counts[1]}|Q3:{q_counts[2]}|Q4:{q_counts[3]}"
                
                edge = total_pnl
                
                log(f"  >> [PnL] Trades:{total_trades} ({trades_per_day:.1f}/d) | W:{wins} L:{losses} S:{scratches} | WR:{real_wr:.1f}%")
                log(f"  >> [PnL] PnL:{total_pnl:+.1f}pip | PF:{pf:.2f} | MaxDD:{max_drawdown:.1f}pip | MaxLoseStreak:{max_consec_losses}")
                log(f"  >> [PnL] Dist: {dist_str} (StdDev:{dist_std:.1f})")
            else:
                edge = -100.0
                log(f"  >> [PnL] Khong co lenh nao (threshold qua cao)")
            
            scheduler.step()
            
            # Save state
            if val_avg < best_loss:
                best_loss = val_avg
                torch.save(model.state_dict(), best_model_path)
                
            if edge > split_best_edge:
                split_best_edge = edge
                
            torch.save({
                'split_idx': split_idx,
                'epoch': epoch,
                'model_state': model.state_dict(),
                'optimizer_state': optimizer.state_dict(),
                'scheduler_state': scheduler.state_dict(),
                'best_loss': best_loss
            }, checkpoint_path)
            
        # Kết thúc 1 Split, Load lại bộ não tốt nhất của Split này (tránh Overfitting vào epoch cuối)
        if os.path.exists(best_model_path):
            log(f"--- [Walk-Forward] Load lai Model tot nhat (Loss: {best_loss:.4f}) de mang sang Split tiep theo ---")
            try:
                best_model_state = torch.load(best_model_path, map_location=device, weights_only=True)
            except TypeError:
                best_model_state = torch.load(best_model_path, map_location=device)
            model.load_state_dict(best_model_state)
            
        # Kiểm tra Early Stopping theo Split (Sau khi kết thúc toàn bộ epochs của split)
        if split_best_edge < 0:
            consecutive_bad_splits += 1
            log(f"[BAD] Split {split_id} khong co Edge (Best: {split_best_edge:.1f}%). Lien tiep: {consecutive_bad_splits}/{max_bad_splits}")
        else:
            consecutive_bad_splits = 0
            log(f"[GOOD] Split {split_id} CO Edge (Best: {split_best_edge:.1f}%). Reset count.")
            # Luu bo nao co thanh tich + vao Hall of Fame
            import shutil
            import datetime
            ts = datetime.datetime.now().strftime("%y%m%d_%H%M")
            hof_dir = os.path.join("v8_configs", "hall_of_fame")
            os.makedirs(hof_dir, exist_ok=True)
            hof_name = f"brain_{args.opt_id}_S{split_id}_PnL{split_best_edge:+.0f}_{ts}.pt"
            hof_path = os.path.join(hof_dir, hof_name)
            if os.path.exists(best_model_path):
                shutil.copy2(best_model_path, hof_path)
                log(f"[SAVED] {hof_name} -> Hall of Fame")
            
        if consecutive_bad_splits >= max_bad_splits:
            log(f"=== EARLY STOPPING GLOBAL: Dung toan bo qua trinh train vi {max_bad_splits} splits lien tiep Edge < 0 ===")
            break
            
        # Reset start_epoch for next splits
        start_epoch = 0
        
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log(f"")
    log(f"{'='*60}")
    log(f"=== TRAINING HOAN TAT CHU DONG tren {args.node_id} ===")
    log(f"=== Thoi gian: {now} ===")
    log(f"=== Tong so splits da xu ly: {len(train_files)} ===")
    log(f"=== Best Val Loss: {best_loss:.6f} ===")
    log(f"=== Ly do dung: DA HOAN THANH toan bo {len(train_files)} walk-forward splits ===")
    log(f"{'='*60}")
    
    # Luu model rieng theo OPT ID
    import shutil
    if os.path.exists(best_model_path):
        shutil.copy2(best_model_path, final_model_path)
        log(f"=== Da luu model vao {final_model_path} ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        if "CUDA error" in str(e) or "out of memory" in str(e).lower():
            # Neu dang o GPU ma bi crash do GPU bi chiem dung hoan toan (Game/DirectX)
            import time
            print(f"\n[FATAL] GPU Crash detected ({e}).")
            print("=> Hệ thống đang bận (Game/App khác chiếm GPU). Sẽ đợi 5 phút rồi thử lại trên GPU...\n", flush=True)
            time.sleep(300) # Doi 5 phut
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            raise e
