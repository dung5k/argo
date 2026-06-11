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
            
        m_path = os.path.join(_ROOT, "v8_configs", "hall_of_fame", self.model_name)
        if not os.path.exists(m_path):
            raise FileNotFoundError(f"Model path not found: {m_path}")
            
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

    def prepare_full_dataset(self) -> DataLoader:
        data_path = os.path.join(_ROOT, "data", "XAUUSDm_M1_2021_2026.parquet")
        print(f"Loading full M1 dataset from {data_path}...")
        df_m1 = pd.read_parquet(data_path)
        
        # Clean columns
        if 'tick_volume' in df_m1.columns and 'volume' not in df_m1.columns:
            df_m1 = df_m1.rename(columns={'tick_volume': 'volume'})
            
        # Filter session (London & NY only, skip Asian)
        print("Filtering out Asian session (keeping 08:00 - 22:59 server time)...")
        df_m1 = df_m1[(df_m1.index.hour >= 8) & (df_m1.index.hour <= 22)].copy()
        
        # CHỐNG DATA LEAKAGE: Cắt bỏ toàn bộ dữ liệu từ 01/01/2026 trở đi
        print("Truncating data strictly before 2026-01-01 to prevent leakage into the test set...")
        df_m1 = df_m1[df_m1.index < '2026-01-01'].copy()
        
        # Resample base, mid, high
        print(f"Resampling datasets (Base: {self.base_freq}, Mid: {self.mid_freq}, High: {self.high_freq})...")
        def resample_df(df, freq):
            return df.resample(freq).agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
        df_base = resample_df(df_m1, self.base_freq)
        df_mid = resample_df(df_m1, self.mid_freq)
        df_high = resample_df(df_m1, self.high_freq)
        
        print(f"Dataset summary | Base: {len(df_base)} | Mid: {len(df_mid)} | High: {len(df_high)}")
        
        print("Building full V8DatasetBuilder (this may take a few minutes)...")
        dataset = V8DatasetBuilder(self.config, df_base, df_mid, df_high)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True, drop_last=True)
        return loader

    def train(self):
        model = self.load_model()
        loader = self.prepare_full_dataset()
        
        # Weighted CrossEntropyLoss to balance HOLD vs trading classes
        class_weights = torch.tensor([1.0/0.15, 1.0/0.10, 1.0/0.50, 1.0/0.10, 1.0/0.15]).to(self.device)
        class_weights = class_weights / class_weights.sum() * 5.0
        criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1, reduction='none')
        
        optimizer = optim.AdamW(model.parameters(), lr=self.lr, weight_decay=1e-4)
        
        log_msg = f"\nStarting training for {self.epochs} epochs with LR={self.lr} on device={self.device}..."
        print(log_msg)
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as lf:
                lf.write(log_msg + '\n')
        for epoch in range(self.epochs):
            model.train()
            total_loss = 0.0
            
            for step, (x_m15, x_h1, x_h4, cont_x, y) in enumerate(loader):
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
                    step_msg = f"Epoch {epoch+1}/{self.epochs} | Step {step+1}/{len(loader)} | Loss: {loss.item():.4f}"
                    print(step_msg)
                    
            avg_loss = total_loss / len(loader)
            epoch_msg = f"==> Epoch {epoch+1}/{self.epochs} Completed | Average Loss: {avg_loss:.4f}"
            print(epoch_msg)
            if self.log_file:
                with open(self.log_file, 'a', encoding='utf-8') as lf:
                    lf.write(epoch_msg + '\n')
            
        # Save final model
        base_name = os.path.splitext(self.model_name)[0]
        out_name = f"{base_name}_FULL.pt"
        out_path = os.path.join(_ROOT, "v8_configs", "hall_of_fame", out_name)
        
        torch.save(model.state_dict(), out_path)
        done_msg = f"\nFULL_TRAIN_DONE: Model saved to {out_path}"
        print(done_msg)
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as lf:
                lf.write(done_msg + '\n')

def main():
    parser = argparse.ArgumentParser(description="Full Dataset Training for V8 Brains")
    parser.add_argument("--model", type=str, required=True, help="Filename of the brain model to train")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
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
