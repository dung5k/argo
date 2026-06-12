import os
import sys
import argparse
import json
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import DataLoader

# Ensure project root in python path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

class V8FullTrainer:
    def __init__(self, model_name: str, config_path: str, epochs: int, lr: float, batch_size: int, scratch: bool = False, layers: int = 3, log_file: str = ""):
        self.model_name = model_name
        self.config_path = config_path
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
        self.scratch = scratch
        self.layers = layers
        self.log_file = log_file
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load config
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            
        # Determine base timeframe based on model name keywords
        if "8202" in self.model_name or "V8C" in self.model_name:
            self.base_tf = "M5"
        else:
            self.base_tf = "M15"
            
        print(f"Using base timeframe: {self.base_tf} for model: {self.model_name}")
        
        if self.base_tf == "M5":
            self.base_freq, self.mid_freq, self.high_freq = "5min", "15min", "1h"
        else:
            self.base_freq, self.mid_freq, self.high_freq = "15min", "1h", "4h"

    def load_model(self):
        if self.scratch:
            print(f"Initializing a fresh model from scratch with {self.layers} layers...")
            self.config['transformer_params']['num_layers'] = self.layers
            model = V8TransformerModel(self.config)
            model.to(self.device)
            return model
            
        # Load pre-trained weights
        m_path = os.path.join(_ROOT, "v8_configs", "hall_of_fame", self.model_name)
        if not os.path.exists(m_path):
            print(f"WARNING: Model file {m_path} not found. Starting from scratch with {self.layers} layers.")
            self.config['transformer_params']['num_layers'] = self.layers
            model = V8TransformerModel(self.config)
            model.to(self.device)
            return model
            
        print(f"Loading weights from {m_path}...")
        state_dict = torch.load(m_path, map_location=self.device, weights_only=False)
        
        # Detect layers dynamically
        layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
        num_layers = max(layer_indices) + 1 if layer_indices else 3
        self.config['transformer_params']['num_layers'] = num_layers
        print(f"Detected model architecture: {num_layers} Transformer layers.")
        
        model = V8TransformerModel(self.config)
        model.load_state_dict(state_dict)
        model.to(self.device)
        return model

    def _prepare_m1_data(self):
        """Load and prepare M1 data. Keep ALL 24h data (no Asian session filtering)."""
        data_path = os.path.join(_ROOT, "data", "XAUUSDm_M1_2021_2026.parquet")
        print(f"Loading full M1 dataset from {data_path}...")
        df_m1 = pd.read_parquet(data_path)
        
        # Clean columns
        if 'tick_volume' in df_m1.columns and 'volume' not in df_m1.columns:
            df_m1 = df_m1.rename(columns={'tick_volume': 'volume'})
        
        # [FIX 1] KHÔNG filter phiên Á nữa — giữ nguyên 24h data
        # Lý do: Cắt phiên Á tạo Gap ảo khiến EMA/MACD/RSI bị giật cục
        # Việc không train trên phiên Á đã được xử lý bằng target=-1 trong DatasetBuilder
        print("Keeping full 24h data (Asian session handled by loss masking, not data filtering)...")
        
        # CHỐNG DATA LEAKAGE: Cắt bỏ toàn bộ dữ liệu từ 01/01/2026 trở đi
        print("Truncating data strictly before 2026-01-01 to prevent leakage into the test set...")
        df_m1 = df_m1[df_m1.index < '2026-01-01'].copy()
        
        return df_m1

    def _resample(self, df_m1):
        """Resample M1 data to base, mid, high timeframes."""
        print(f"Resampling datasets (Base: {self.base_freq}, Mid: {self.mid_freq}, High: {self.high_freq})...")
        def resample_df(df, freq):
            return df.resample(freq).agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
        df_base = resample_df(df_m1, self.base_freq)
        df_mid = resample_df(df_m1, self.mid_freq)
        df_high = resample_df(df_m1, self.high_freq)
        return df_base, df_mid, df_high

    def prepare_datasets(self):
        """
        Split data: Train (2021 - Jun 2025), Validation (Jul - Dec 2025).
        Test set: 2026 (kept completely separate, not loaded here).
        Returns two DataLoaders: train_loader and val_loader.
        """
        df_m1 = self._prepare_m1_data()
        
        # Split M1 data BEFORE resampling to avoid leakage at boundary
        # Train: 2021-01-01 to 2025-06-30 (~4.5 years)
        # Val:   2025-07-01 to 2025-12-31 (~6 months)
        # Test:  2026 (excluded by _prepare_m1_data cutoff)
        train_cutoff = '2025-07-01'
        
        df_m1_train = df_m1[df_m1.index < train_cutoff].copy()
        df_m1_val = df_m1[df_m1.index >= train_cutoff].copy()
        
        print(f"Train period: {df_m1_train.index[0]} to {df_m1_train.index[-1]} ({len(df_m1_train):,} M1 rows)")
        print(f"Validation period: {df_m1_val.index[0]} to {df_m1_val.index[-1]} ({len(df_m1_val):,} M1 rows)")
        
        # Resample train
        df_base_train, df_mid_train, df_high_train = self._resample(df_m1_train)
        print(f"Train dataset | Base: {len(df_base_train)} | Mid: {len(df_mid_train)} | High: {len(df_high_train)}")
        
        # Resample validation
        df_base_val, df_mid_val, df_high_val = self._resample(df_m1_val)
        print(f"Val dataset   | Base: {len(df_base_val)} | Mid: {len(df_mid_val)} | High: {len(df_high_val)}")
        
        # Build datasets
        print("Building TRAIN dataset...")
        train_dataset = V8DatasetBuilder(self.config, df_base_train, df_mid_train, df_high_train)
        
        print("Building VALIDATION dataset...")
        val_dataset = V8DatasetBuilder(self.config, df_base_val, df_mid_val, df_high_val)
        
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True, drop_last=True)
        val_loader = DataLoader(val_dataset, batch_size=self.batch_size * 2, shuffle=False)
        
        return train_loader, val_loader

    def _evaluate(self, model, val_loader, criterion):
        """Evaluate model on validation set. Returns average loss."""
        model.eval()
        total_loss = 0.0
        total_samples = 0
        
        with torch.no_grad():
            for x_m15, x_h1, x_h4, cont_x, y in val_loader:
                x_m15 = x_m15.to(self.device)
                x_h1 = x_h1.to(self.device)
                x_h4 = x_h4.to(self.device)
                cont_x = cont_x.to(self.device)
                y = y.to(self.device)
                
                out = model(x_m15, x_h1, x_h4, cont_x)
                mask = (y != -1).float()
                y_safe = torch.where(y == -1, torch.tensor(2, device=out.device), y)
                raw_loss = criterion(out, y_safe)
                loss = (raw_loss * mask).sum()
                
                total_loss += loss.item()
                total_samples += mask.sum().item()
        
        return total_loss / max(total_samples, 1)

    def train(self):
        model = self.load_model()
        train_loader, val_loader = self.prepare_datasets()
        
        # Weighted CrossEntropyLoss to balance HOLD vs trading classes
        class_weights = torch.tensor([1.0/0.15, 1.0/0.10, 1.0/0.50, 1.0/0.10, 1.0/0.15]).to(self.device)
        class_weights = class_weights / class_weights.sum() * 5.0
        criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1, reduction='none')
        
        optimizer = optim.AdamW(model.parameters(), lr=self.lr, weight_decay=1e-4)
        
        # [FIX 3] LR Scheduler — CosineAnnealingLR for smooth decay
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.epochs, eta_min=self.lr * 0.01)
        
        log_msg = f"\nStarting training for {self.epochs} epochs with LR={self.lr} on device={self.device}..."
        log_msg += f"\nScheduler: CosineAnnealingLR (eta_min={self.lr * 0.01:.2e})"
        print(log_msg)
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as lf:
                lf.write(log_msg + '\n')
        
        # [FIX 2] Early stopping tracking
        best_val_loss = float('inf')
        patience = 5
        patience_counter = 0
        best_model_state = None
        
        for epoch in range(self.epochs):
            model.train()
            total_loss = 0.0
            
            for step, (x_m15, x_h1, x_h4, cont_x, y) in enumerate(train_loader):
                x_m15 = x_m15.to(self.device)
                x_h1 = x_h1.to(self.device)
                x_h4 = x_h4.to(self.device)
                cont_x = cont_x.to(self.device)
                y = y.to(self.device)
                
                optimizer.zero_grad()
                out = model(x_m15, x_h1, x_h4, cont_x)
                mask = (y != -1).float()
                y_safe = torch.where(y == -1, torch.tensor(2, device=out.device), y)
                raw_loss = criterion(out, y_safe)
                loss = (raw_loss * mask).sum() / mask.sum().clamp(min=1.0)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                
                total_loss += loss.item()
                if (step + 1) % 50 == 0:
                    step_msg = f"Epoch {epoch+1}/{self.epochs} | Step {step+1}/{len(train_loader)} | Loss: {loss.item():.4f} | LR: {scheduler.get_last_lr()[0]:.2e}"
                    print(step_msg)
            
            # Step scheduler after each epoch
            scheduler.step()
                    
            avg_train_loss = total_loss / len(train_loader)
            
            # [FIX 2] Evaluate on validation set
            val_loss = self._evaluate(model, val_loader, criterion)
            
            # Check if best model
            improved = val_loss < best_val_loss
            if improved:
                best_val_loss = val_loss
                patience_counter = 0
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                marker = " ** BEST **"
            else:
                patience_counter += 1
                marker = f" (patience {patience_counter}/{patience})"
            
            epoch_msg = f"==> Epoch {epoch+1}/{self.epochs} Completed | Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f}{marker}"
            print(epoch_msg)
            if self.log_file:
                with open(self.log_file, 'a', encoding='utf-8') as lf:
                    lf.write(epoch_msg + '\n')
            
            # Early stopping
            if patience_counter >= patience:
                stop_msg = f"Early stopping triggered after {epoch+1} epochs. Best Val Loss: {best_val_loss:.4f}"
                print(stop_msg)
                if self.log_file:
                    with open(self.log_file, 'a', encoding='utf-8') as lf:
                        lf.write(stop_msg + '\n')
                break
            
        # Save best model (not last epoch)
        base_name = os.path.splitext(self.model_name)[0]
        out_name = f"{base_name}_FULL.pt"
        out_path = os.path.join(_ROOT, "v8_configs", "hall_of_fame", out_name)
        
        if best_model_state is not None:
            torch.save(best_model_state, out_path)
        else:
            torch.save(model.state_dict(), out_path)
            
        done_msg = f"\nFULL_TRAIN_DONE: Model saved to {out_path} (Best Val Loss: {best_val_loss:.4f})"
        print(done_msg)
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as lf:
                lf.write(done_msg + '\n')

        # [AUTO-BACKTEST] Chạy test nâng cao nếu model tốt (Val Loss <= 1.4500)
        if best_val_loss <= 1.4500:
            print(f"Bộ não {self.model_name} đạt chuẩn (Loss: {best_val_loss:.4f} <= 1.45). Đang tự động chạy Backtest nâng cao...")
            try:
                import subprocess
                clean_name = base_name[6:] if base_name.startswith("brain_") else base_name
                report_name = f"backtest_advanced_{clean_name}.txt"
                out_txt = os.path.join(_ROOT, "v8_configs", "hall_of_fame", report_name)
                
                py_exe = sys.executable
                cmd = f'"{py_exe}" scripts/v8_backtest_adv.py --model "{out_name}" > "{out_txt}" 2>&1'
                subprocess.run(cmd, shell=True)
                print(f"✅ Đã lưu kết quả test nâng cao vào: {out_txt}")
                if self.log_file:
                    with open(self.log_file, 'a', encoding='utf-8') as lf:
                        lf.write(f"AUTO-BACKTEST DONE: Results saved to {out_txt}\n")
            except Exception as e:
                print(f"⚠️ Lỗi khi chạy auto-backtest: {e}")

def main():
    parser = argparse.ArgumentParser(description="Full Dataset Training for V8 Brains")
    parser.add_argument("--model", type=str, required=True, help="Filename of the brain model to train")
    parser.add_argument("--epochs", type=int, default=25, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-5, help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=128, help="Batch size")
    parser.add_argument("--scratch", action="store_true", help="Initialize model from scratch instead of loading weights")
    parser.add_argument("--layers", type=int, default=3, help="Number of layers if training from scratch")
    parser.add_argument("--node_id", type=str, default="ARGO1", help="Node ID for log file naming")
    parser.add_argument("--opt_id", type=str, default="", help="AutoML Option ID for log file naming")
    
    args = parser.parse_args()
    
    config_path = os.path.join(_ROOT, "v8_configs", "v8_training_config.json")
    
    # Create log file path for orchestrator to read
    log_suffix = f"_{args.opt_id}" if args.opt_id else ""
    log_file = os.path.join(_ROOT, "logs", f"v8_train_{args.node_id}{log_suffix}.log")
    os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)
    
    trainer = V8FullTrainer(
        model_name=args.model,
        config_path=config_path,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        scratch=args.scratch,
        layers=args.layers,
        log_file=log_file
    )
    
    trainer.train()

if __name__ == "__main__":
    main()
