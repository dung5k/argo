import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:32'
import sys
import json
import argparse
import glob
import pandas as pd
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


def get_args():
    parser = argparse.ArgumentParser(description="V8 Training Loop")
    parser.add_argument("--node_id", type=str, default="ARGO1", help="Node Name")
    parser.add_argument("--layers", type=int, default=3, help="Number of Transformer Layers")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning Rate")
    parser.add_argument("--epochs", type=int, default=10, help="Epochs per split")
    parser.add_argument("--batch_size", type=int, default=0, help="Batch size (0 = use config default)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--opt_id", type=str, default="", help="AutoML Option ID for logging")
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
        
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
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
            
    criterion = nn.CrossEntropyLoss()
    log("Using Standard CrossEntropyLoss (5 Balanced Classes: 20% each)")
        
    optimizer = optim.AdamW(model.parameters(), lr=strat_lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
    
    checkpoint_path = os.path.join("v8_configs", f"checkpoint_{args.node_id}.pt")
    best_model_path = os.path.join("v8_configs", f"best_model_{args.node_id}.pt")
    
    start_split_idx = 0
    start_epoch = 0
    best_loss = float('inf')
    
    if args.resume and os.path.exists(checkpoint_path):
        try:
            log(f"Loading checkpoint from {checkpoint_path}...")
            checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
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
        
    train_files = sorted(glob.glob(os.path.join(splits_dir, "*_train.parquet")))
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
            
        df_train = pd.read_parquet(train_file)
        df_train_h1 = df_train.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        df_train_h4 = df_train.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        
        train_dataset = V8DatasetBuilder(config, df_train, df_train_h1, df_train_h4)
        train_loader = DataLoader(train_dataset, batch_size=bs, shuffle=True)
        
        df_test = pd.read_parquet(test_file)
        df_test_h1 = df_test.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        df_test_h4 = df_test.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        
        test_dataset = V8DatasetBuilder(config, df_test, df_test_h1, df_test_h4)
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

            scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
        
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
            
            # Trade dua tren nhan Manh (Strong Buy = 4, Strong Sell = 0)
            prob_s2 = all_probs[:, 0]
            prob_b2 = all_probs[:, 4]
            max_trade_probs, trade_dirs = torch.max(torch.stack([prob_s2, prob_b2], dim=1), dim=1)
            # trade_dirs: 0 = Sell2, 1 = Buy2
            trade_dirs = torch.where(trade_dirs == 0, torch.tensor(0).to(device), torch.tensor(4).to(device))
            
            train_avg = total_loss/len(train_loader) if len(train_loader) > 0 else 0
            val_avg = val_loss/len(test_loader) if len(test_loader) > 0 else 0
            
            current_lr = optimizer.param_groups[0]['lr']
            log(f"Split {split_id} | Ep {epoch+1} | Loss(T/V): {train_avg:.3f}/{val_avg:.3f} | LR: {current_lr:.1e}")
            log(f"  -> Prob [S2]: {min_probs[0]:.4f}~{max_probs[0]:.4f} | [S1]: {min_probs[1]:.4f}~{max_probs[1]:.4f} | [H]: {min_probs[2]:.4f}~{max_probs[2]:.4f} | [B1]: {min_probs[3]:.4f}~{max_probs[3]:.4f} | [B2]: {min_probs[4]:.4f}~{max_probs[4]:.4f}")
            
            be_wr = 51.5
            edge = -100.0
            
            for threshold in [0.3, 0.35, 0.4]:
                signal_mask = max_trade_probs >= threshold
                predicted_actions = torch.where(signal_mask, trade_dirs, torch.zeros_like(trade_dirs))
                
                total_signal = signal_mask.sum().item()
                correct_signal = ((predicted_actions == all_targets) & signal_mask).sum().item()
                
                signal_acc = correct_signal/total_signal if total_signal > 0 else 0
                trades_per_day = total_signal / total_days if total_days > 0 else 0
                win_rate = signal_acc * 100
                current_edge = win_rate - be_wr
                
                if threshold == 0.35:
                    edge = current_edge
                    
                log(f"  -> [Threshold {threshold}] WR: {win_rate:.1f}% | Edge: {current_edge:+.1f}% | Signals: {total_signal} ({trades_per_day:.1f}/day)")
            
            scheduler.step(val_avg)
            
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
            model.load_state_dict(torch.load(best_model_path, map_location=device))
            
        # Kiểm tra Early Stopping theo Split (Sau khi kết thúc toàn bộ epochs của split)
        if split_best_edge < 0:
            consecutive_bad_splits += 1
            log(f"[BAD] Split {split_id} khong co Edge (Best: {split_best_edge:.1f}%). Lien tiep: {consecutive_bad_splits}/{max_bad_splits}")
        else:
            consecutive_bad_splits = 0
            log(f"[GOOD] Split {split_id} CO Edge (Best: {split_best_edge:.1f}%). Reset count.")
            
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
