import os
import sys
import json
import argparse
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import numpy as np
import torch

# Add project root to path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
from huggingface_hub import hf_hub_download, HfApi

# Import components
try:
    from model_v3 import AAMT_Model
    from loss_v3 import AAMT_JointLoss
    from evaluator_v3 import WinRateEvaluatorV3
    from plotter_v3 import plot_and_notify_v3
except ImportError:
    from src.training_v3.model_v3 import AAMT_Model
    from src.training_v3.loss_v3 import AAMT_JointLoss
    from src.training_v3.evaluator_v3 import WinRateEvaluatorV3
    from src.training_v3.plotter_v3 import plot_and_notify_v3

try:
    from src.training_v2.phoenix_v2 import PhoenixRestartV2
except ImportError:
    pass # Phoenix is optional

def train_warmup_phase(model, train_loader, criterion, optimizer, device, epochs=5):
    """
    Giai Ä‘oáº¡n 1: Dáº¡y AI cÃ¡ch nhÃ¬n biá»ƒu Ä‘á»“ (TÃ¡ch nhiá»…u) báº±ng cÃ¡ch chá»‰ báº­t Reconstruction Loss
    """
    model.train()
    model.to(device)
    
    # Ã‰p trá»ng sá»‘ Joint Loss: Táº®T hoÃ n toÃ n nhÃ¡nh Dá»± Ä‘oÃ¡n, Dá»’N 100% lá»±c cho nhÃ¡nh Giáº£i nÃ©n
    criterion.set_lambdas(lambda_recon=1.0, lambda_class=0.0)
    
    print(f"--- ðŸš€ Báº®T Äáº¦U WARM-UP AUTOENCODER ({epochs} Epochs) ---", flush=True)
    for epoch in range(epochs):
        total_recon_loss = 0.0
        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            reconstructed, logits, _ = model(inputs)
            loss, l_recon, l_class = criterion(reconstructed, inputs, logits, targets)
            loss.backward()
            optimizer.step()
            total_recon_loss += l_recon.item()
            
        avg_loss = total_recon_loss / len(train_loader)
        print(f"[Warm-up] Epoch {epoch+1}/{epochs} | Recon_MSE_Loss: {avg_loss:.6f}", flush=True)
        
    return model

def train_finetuning_phase(model, train_loader, criterion, optimizer, device):
    """
    Cháº¡y Fine-Tuning 1 Epoch Ä‘á»ƒ cáº¯m vÃ o luá»“ng while True.
    """
    model.train()
    model.to(device)
    # Báº¬T Láº I nhÃ¡nh phÃ¢n loáº¡i (lambda_class = 1.0) Ä‘á»ƒ Ä‘Ã o táº¡o hÃ m tá»•ng (Joint)
    criterion.set_lambdas(lambda_recon=1.0, lambda_class=1.0)
    
    total_loss_val = 0.0
    total_recon = 0.0
    total_class = 0.0
    
    for inputs, targets in train_loader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        reconstructed, logits, _ = model(inputs)
        loss, l_recon, l_class = criterion(reconstructed, inputs, logits, targets)
        loss.backward()
        optimizer.step()
        
        total_loss_val += loss.item()
        total_recon += l_recon.item()
        total_class += l_class.item()
        
    l = len(train_loader)
    return total_loss_val/l, total_recon/l, total_class/l

def evaluate_val_set(model, val_loader, criterion, device):
    model.eval()
    total_loss_val = 0.0
    total_recon = 0.0
    
    all_logits = []
    all_labels = []
    
    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            reconstructed, logits, _ = model(inputs)
            loss, l_recon, l_class = criterion(reconstructed, inputs, logits, targets)
            
            total_loss_val += loss.item()
            total_recon += l_recon.item()
            
            all_logits.append(logits.cpu())
            all_labels.append(targets.cpu())
            
    l = len(val_loader)
    avg_loss = total_loss_val / max(1, l)
    avg_recon = total_recon / max(1, l)
    
    cat_logits = torch.cat(all_logits, dim=0)
    cat_labels = torch.cat(all_labels, dim=0)
    
    evaluator = WinRateEvaluatorV3()
    res = evaluator.evaluate(cat_logits, cat_labels, avg_loss, avg_recon)
    return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", help="Path to config file")
    parser.add_argument("--scratch", action="store_true", help="Bá» qua káº¿ thá»«a, train láº¡i tá»« Ä‘áº§u")
    parser.add_argument("--session", default="ny", help="Session target (bo qua, doc tu config file)")
    args = parser.parse_args()
    
    config_path = args.config if args.config else "data/bot_config_xau_ny_v3.json"
    print(f"Loading config from: {config_path}", flush=True)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    cfg_id = config.get('CONFIG_ID', 'V3_UNKNOWN')
    dataset_repo = config.get("HF_CLOUD", {}).get("DATASET_REPO")
    train_cfg = config.get("TRAINING", {})
    
    epochs_warmup = train_cfg.get("EPOCHS_PHASE_1", 10)
    batch_size = train_cfg.get("BATCH_SIZE", 64)
    lr = train_cfg.get("LEARNING_RATE", 1e-4)
    
    hf_token = os.environ.get("HF_TOKEN", "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")
    
    # 1. KÃ©o Dataset (Features V3, 37 Cá»™t) tá»« mÃ¢y vá»
    print("â˜ï¸ Äang táº£i Dataset Tensor tá»« HuggingFace HUB...", flush=True)
    x_filename = f"data/{cfg_id}/X_tensor_{cfg_id}.npy"
    y_filename = f"data/{cfg_id}/Y_tensor_{cfg_id}.npy"
    
    x_path = hf_hub_download(repo_id=dataset_repo, filename=x_filename, repo_type="dataset", token=hf_token)
    y_path = hf_hub_download(repo_id=dataset_repo, filename=y_filename, repo_type="dataset", token=hf_token)
    
    X = np.load(x_path)
    Y = np.load(y_path)
    print(f"âœ… Táº£i thÃ nh cÃ´ng! KÃ­ch thÆ°á»›c X: {X.shape}, Y: {Y.shape}", flush=True)
    
    # Chia Validation set
    X_tr, X_va, Y_tr, Y_va = train_test_split(X, Y, test_size=0.2, random_state=42, shuffle=True)
    
    train_loader = DataLoader(TensorDataset(torch.tensor(X_tr, dtype=torch.float32), torch.tensor(Y_tr, dtype=torch.long)), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.tensor(X_va, dtype=torch.float32), torch.tensor(Y_va, dtype=torch.long)), batch_size=batch_size, shuffle=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"ðŸ’» Äang Train trÃªn ná»n táº£ng: {device}", flush=True)
    
    # 2. Sinh máº¡ng neural AAMTV3
    model = AAMT_Model(input_dim=X.shape[2], seq_len=X.shape[1])
    
    msg = ""
    # -------------------------------------
    # Káº¿ thá»«a trá»ng sá»‘ cÅ©
    # -------------------------------------
    if args.scratch:
        msg = "Bá» qua káº¿ thá»«a theo cá» --scratch. ÄÃ o táº¡o má»›i hoÃ n toÃ n!"
        print(f"\n[INHERIT] {msg}", flush=True)
    else:
        print("\n[INHERIT] Äang tÃ¬m trá»ng sá»‘ cÅ© Ä‘á»ƒ káº¿ thá»«a tá»« HF...", flush=True)
        import sys as _sys
        _hf_script_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "orchestration")
        if _hf_script_dir not in _sys.path:
            _sys.path.insert(0, _hf_script_dir)
        try:
            from hf_sync import pull_runs
            pulled = pull_runs(logger=None, target_prefix="v3", config_id=cfg_id)
        except Exception as e:
            print(f"[HF] Lá»—i pull_runs: {e}", flush=True)
            
        import glob
        pattern = os.path.join(_ROOT, "logs", "runs", "**", f"aamt_v3_{cfg_id}_final.pth")
        all_files = glob.glob(pattern, recursive=True)
        if all_files:
            latest_file = max(all_files, key=os.path.getmtime)
            try:
                model.load_state_dict(torch.load(latest_file, map_location=device, weights_only=True))
                msg = f"ðŸ‘‰ Káº¿ thá»«a Model: {os.path.basename(latest_file)}"
                print(f"  {msg} tá»« \n  {latest_file}", flush=True)
            except Exception as e:
                msg = f"âŒ Lá»—i káº¿ thá»«a Model: {e}"
                print(f"  {msg}", flush=True)
        else:
            msg = f"âŒ KhÃ´ng tÃ¬m tháº¥y trá»ng sá»‘ cÅ© ná»™i bá»™/Ä‘Ã¡m mÃ¢y. Khá»Ÿi táº¡o ngáº«u nhiÃªn tá»« Ä‘áº§u!"
            print(f"  {msg}", flush=True)
            
    try:
        tg_config_path = os.path.join(_ROOT, ".agent", "telegram_bot.json")
        with open(tg_config_path, "r", encoding="utf-8") as f:
            tcfg = json.load(f)
        from src.orchestration.tg_helper import TelegramBot
        tbot = TelegramBot(tcfg["bot_token"])
        chat_id = tcfg["allowed_chat_ids"][0]
        client_id = os.environ.get("ARGO_CLIENT_ID", "Unknown")
        tbot.send_message(chat_id, f"âš™ï¸ <b>[{client_id}] [AAMT V3 ({cfg_id})]</b>\n{msg}")
    except Exception as e:
        pass
    
    model.to(device)
    
    criterion = AAMT_JointLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    if 'PhoenixRestartV2' in globals():
        phoenix = PhoenixRestartV2(model, base_lr=lr, max_phoenix=15, weight_decay=1e-4)
        optimizer = phoenix.optimizer
    else:
        phoenix = None
    
    # 3. PHASE 1 WARM-UP (Chá»‰ chay 1 láº§n)
    model = train_warmup_phase(model, train_loader, criterion, optimizer, device, epochs=epochs_warmup)
    
    # Tá»± Ä‘á»™ng tá»‘i Æ°u CUDNN nÃªÃº dÃ¹ng GPU
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
    
    # MÃ´i trÆ°á»ng log giá»‘ng V2
    import shutil
    run_timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_name = f"run_{run_timestamp}_v3_{cfg_id}"
    log_base = os.environ.get("ARGO_LOGS_DIR", os.path.join(_ROOT, "logs"))
    out_dir = os.path.join(log_base, "runs", run_name)
    os.makedirs(out_dir, exist_ok=True)
    
    import shutil
    shutil.copy(config_path, os.path.join(out_dir, os.path.basename(config_path)))

    class _TeeLogger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "w", encoding="utf-8")
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
        def flush(self):
            self.terminal.flush()
            self.log.flush()

    sys.stdout = _TeeLogger(os.path.join(out_dir, "train_v3.log"))
    
    scaler_src = f"data/{cfg_id}/scaler_{cfg_id}.pkl"
    if os.path.exists(scaler_src):
        shutil.copy(scaler_src, os.path.join(out_dir, f"scaler_{cfg_id}.pkl"))
        print(f"[PACK] KÃ¨m theo scaler file vÃ o: {out_dir}", flush=True)

    # 4. PHASE 2 FINE-TUNING (VÃ²ng láº·p vÄ©nh cá»­u)
    print("--- ðŸš€ Báº®T Äáº¦U VÃ’NG Láº¶P FINE-TUNING ÄA NHIá»†M (Infinite Loop) ---", flush=True)
    epoch = 0
    best_score = 0.0
    api = HfApi(token=hf_token)
    model_repo = config.get("HF_CLOUD", {}).get("MODEL_REPO", "dung5k/aamt_v3_xau_ny_weights")
    api.create_repo(repo_id=model_repo, exist_ok=True, private=True)
    
    while True:
        epoch += 1
        current_optimizer = phoenix.optimizer if phoenix else optimizer
        tr_loss, tr_recon, tr_class = train_finetuning_phase(model, train_loader, criterion, current_optimizer, device)
        eval_res = evaluate_val_set(model, val_loader, criterion, device)
        
        comp_score = eval_res.composite_score()
        print(f"[Epoch {epoch}] Loss(MSE:{tr_recon:.4f}/CE:{tr_class:.4f}) | Val {eval_res.format_summary().replace(chr(10), ' | ')}", flush=True)
        
        improved = comp_score > best_score
        if improved:
            best_score = comp_score
            print(f"  ðŸŒŸ Ká»¶ Lá»¤C Má»šI! Composite Score = {best_score:.4f}. LÆ°u model...", flush=True)
            
            # Save local
            model_export_path = os.path.join(out_dir, f"aamt_v3_{cfg_id}_final.pth")
            torch.save(model.state_dict(), model_export_path)
            
            # Ghi json metrics theo chuáº©n V2
            try:
                session_name = config.get("SESSION", "ny").lower()
                target_sym = config.get("TARGET_SYMBOL", "xauusd").lower().replace('m', '')
                nfe = config.get("MODEL_DIMENSIONS", {}).get("num_features", 38)
                t_metrics = []
                for m in eval_res.threshold_metrics:
                    t_metrics.append({
                        "threshold": float(m.threshold),
                        "total_signals": int(m.total_signals),
                        "win_rate": float(m.win_rate()),
                        "avg_win_return": 0.001,
                        "avg_loss_return": 0.001,
                        "ev_score": float(m.balanced_score),
                        "sharpe_score": 0.0,
                        "total_buy": int(m.total_signals // 2),  # Giáº£ láº­p táº¡m
                        "total_sell": int(m.total_signals - (m.total_signals // 2))
                    })
                    
                metrics_data = {
                    "target": target_sym,
                    "version": "Transformer_V3",
                    "dimensions": {
                        "num_features_target": 0,
                        "num_features_macro": nfe
                    },
                    "sessions": {
                        session_name: {
                            "BEST_VLOSS": {
                                "epoch": int(epoch),
                                "max_threshold": float(max([m.threshold for m in eval_res.threshold_metrics])) if eval_res.threshold_metrics else 0.5,
                                "composite_score": float(eval_res.composite_score()),
                                "val_loss": float(eval_res.val_loss),
                                "threshold_metrics": t_metrics,
                                "win_rates": [float(m.win_rate()) for m in eval_res.threshold_metrics],
                                "thresholds": [float(m.threshold) for m in eval_res.threshold_metrics],
                                "totals": [int(m.total_signals) for m in eval_res.threshold_metrics]
                            }
                        }
                    }
                }
                with open(os.path.join(out_dir, "training_metrix_v3.json"), "w", encoding="utf-8") as fm:
                    json.dump(metrics_data, fm, indent=4)
            except Exception as e:
                print(f"  âŒ Lá»—i lÆ°u JSON metrics: {e}", flush=True)

            # Äáº©y Chart Telegram
            plot_and_notify_v3(eval_res, cfg_id, epoch, out_dir)
            
            # Upload HuggingFace nguyÃªn kiá»‡n (Logs, Charts, Config, Model)
            try:
                import sys as _sys
                _hf_script_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "orchestration")
                if _hf_script_dir not in _sys.path:
                    _sys.path.insert(0, _hf_script_dir)
                from hf_sync import push_runs
                
                push_runs(run_dir=out_dir)
                print(f"  â˜ï¸ Upload dá»¯ liá»‡u nguyÃªn kiá»‡n thÆ° má»¥c {out_dir} lÃªn HF thÃ nh cÃ´ng!", flush=True)
            except Exception as e:
                print(f"  âŒ Lá»—i Push HF: {e}", flush=True)
            
            if phoenix:
                phoenix.notify_improved()
        else:
            if phoenix:
                if phoenix.notify_no_improve():
                    phoenix.apply_perturbation(model.state_dict())
                    print(f"  ðŸ”¥ PHOENIX RESTART! (TÃ¡i sinh do káº¹t {phoenix.max_stagnate} epochs)", flush=True)
            else:
                pass # Continuous wait

if __name__ == "__main__":
    main()

