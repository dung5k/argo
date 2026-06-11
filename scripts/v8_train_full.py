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
    def __init__(self, model_name: str, config_path: str, epochs: int, lr: float, batch_size: int):
        self.model_name = model_name
        self.config_path = config_path
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
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
        criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
        
        optimizer = optim.AdamW(model.parameters(), lr=self.lr, weight_decay=1e-4)
        
        print(f"\nStarting training for {self.epochs} epochs with LR={self.lr} on device={self.device}...")
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
                loss = criterion(out, y)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                if (step + 1) % 50 == 0:
                    print(f"Epoch {epoch+1}/{self.epochs} | Step {step+1}/{len(loader)} | Loss: {loss.item():.4f}")
                    
            avg_loss = total_loss / len(loader)
            print(f"==> Epoch {epoch+1} Completed | Average Loss: {avg_loss:.4f}")
            
        # Save final model
        base_name = os.path.splitext(self.model_name)[0]
        out_name = f"{base_name}_FULL.pt"
        out_path = os.path.join(_ROOT, "v8_configs", "hall_of_fame", out_name)
        
        torch.save(model.state_dict(), out_path)
        print(f"\n✅ SUCCESS: Full training complete! Model saved to: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Full Dataset Training for V8 Brains")
    parser.add_argument("--model", type=str, required=True, help="Filename of the brain model to train")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-5, help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=128, help="Batch size")
    
    args = parser.parse_args()
    
    config_path = os.path.join(_ROOT, "v8_configs", "v8_training_config.json")
    
    trainer = V8FullTrainer(
        model_name=args.model,
        config_path=config_path,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size
    )
    
    trainer.train()

if __name__ == "__main__":
    main()
