# -*- coding: utf-8 -*-
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
    from model_v6 import AAMT_MTF_Model
    from loss_v3 import AAMT_JointLoss
    from evaluator_v3 import WinRateEvaluatorV3
    from plotter_v3 import plot_and_notify_v3
except ImportError:
    from src.training_v6.model_v6 import AAMT_MTF_Model
    from src.training_v3.loss_v3 import AAMT_JointLoss
    from src.training_v3.evaluator_v3 import WinRateEvaluatorV3
    from src.training_v3.plotter_v3 import plot_and_notify_v3

try:
    from src.training_v2.phoenix_v2 import PhoenixRestartV2
except ImportError:
    pass # Phoenix is optional

def train_warmup_phase(model, train_loader, criterion, optimizer, device, epochs=5):
    """
    Giai đoạn 1: Dạy AI cách nhìn biểu đồ (Tách nhiễu) bằng cách chỉ bật Reconstruction Loss
    """
    model.train()
    model.to(device)
    
    # Ép trọng số Joint Loss: TẮT hoàn toàn nhánh Dự đoán, DỒN 100% lực cho nhánh Giải nén
    criterion.set_lambdas(lambda_recon=1.0, lambda_class=0.0)
    
    print(f"--- \U0001f680 BẮT ĐẦU WARM-UP AUTOENCODER ({epochs} Epochs) ---", flush=True)
    for epoch in range(epochs):
        total_recon_loss = 0.0
        for batch_idx, batch in enumerate(train_loader):
            inputs = [x.to(device) for x in batch[:-1]]
            targets = batch[-1].to(device)
            optimizer.zero_grad()
            reconstructed, logits, _ = model(inputs)
            loss, l_recon, l_class = criterion(reconstructed[0], inputs[0], logits, targets)
            loss.backward()
            # ⚡ CHỐT CHẶN SÓNG THẦN: Cắt gradient khổng lồ để bảo vệ trọng số mạng
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_recon_loss += l_recon.item()
            
        avg_loss = total_recon_loss / len(train_loader)
        print(f"[Warm-up] Epoch {epoch+1}/{epochs} | Recon_MSE_Loss: {avg_loss:.6f}", flush=True)
        
    return model

def train_finetuning_phase(model, train_loader, criterion, optimizer, device):
    """
    Chạy Fine-Tuning 1 Epoch để cắm vào luồng while True.

    PHÁC ĐỒ ĐIỀU TRỊ Task Domination:
    - lambda_recon = 0.05: Bóp nghẹt autoencoder xuống 5% để CE Loss chiếm
      95% gradient bandwidth → mạng dồn sức vào phân loại thay vì vẽ nến.
    """
    model.train()
    model.to(device)
    # [PHÁC ĐỒ 1] Cán cân Loss: Autoencoder chỉ giữ vai trò Regularizer (5%)
    # Giảm mạnh từ 0.2 → 0.05 để triệt tiêu hiện tượng Task Domination
    criterion.set_lambdas(lambda_recon=0.05, lambda_class=1.0)

    total_loss_val = 0.0
    total_recon = 0.0
    total_class = 0.0

    for batch in train_loader:
        inputs = [x.to(device) for x in batch[:-1]]
        targets = batch[-1].to(device)
        optimizer.zero_grad()
        reconstructed, logits, _ = model(inputs)
        loss, l_recon, l_class = criterion(reconstructed[0], inputs[0], logits, targets)
        loss.backward()
        # ⚡ CHỐT CHẶN SÓNG THẦN: Cắt gradient khổng lồ để bảo vệ trọng số mạng
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss_val += loss.item()
        total_recon    += l_recon.item()
        total_class    += l_class.item()

    l = len(train_loader)
    return total_loss_val/l, total_recon/l, total_class/l

def evaluate_val_set(model, val_loader, criterion, device, freq_min_N=80, freq_max_N=1000):
    model.eval()
    total_loss_val = 0.0
    total_recon = 0.0
    total_class = 0.0
    
    all_logits = []
    all_labels = []
    
    with torch.no_grad():
        for batch in val_loader:
            inputs = [x.to(device) for x in batch[:-1]]
            targets = batch[-1].to(device)
            reconstructed, logits, _ = model(inputs)
            
            # Tính MSE Loss trung bình trên các khung thời gian
            # Trong criterion V3, l_recon mong đợi 1 tensor. V6 model trả về list các reconstructed.
            # Ta cần sửa hàm loss một chút hoặc truyền tensor đầu tiên (Base TF) vào hàm loss.
            # Base TF (khung thấp nhất) là inputs[0].
            loss, l_recon, l_class = criterion(reconstructed[0], inputs[0], logits, targets)
            
            total_loss_val += loss.item()
            total_recon += l_recon.item()
            total_class += l_class.item()
            
            all_logits.append(logits.cpu())
            all_labels.append(targets.cpu())
            
    l = len(val_loader)
    avg_loss = total_loss_val / max(1, l)
    avg_recon = total_recon / max(1, l)
    avg_class = total_class / max(1, l)
    
    cat_logits = torch.cat(all_logits, dim=0)
    cat_labels = torch.cat(all_labels, dim=0)
    
    evaluator = WinRateEvaluatorV3(freq_min_N=freq_min_N, freq_max_N=freq_max_N)
    res = evaluator.evaluate(cat_logits, cat_labels, val_loss=avg_loss, val_mse=avg_recon, val_ce=avg_class)
    return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", help="Path to config file")
    parser.add_argument("--scratch", action="store_true", help="Bỏ qua kế thừa, train lại từ đầu")
    parser.add_argument("--session", default="ny", help="Session target (bo qua, doc tu config file)")
    parser.add_argument("--run-id", default="", help="ID của lượt chạy (vd: legacy_run)")
    args = parser.parse_args()
    
    config_path = args.config if args.config else "workspaces/CFG_XAU_NY_V3_5/base_config.json"
    print(f"Loading config from: {config_path}", flush=True)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    cfg_id = config.get('CONFIG_ID', 'V3_UNKNOWN')
    run_dir = None
    if getattr(args, 'run_id', ""):
        run_id = args.run_id
    elif config.get("RUN_ID", ""):
        run_id = config.get("RUN_ID")
    else:
        run_timestamp = time.strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{run_timestamp}_v3"

    run_dir = os.path.join(_ROOT, "workspaces", cfg_id, "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    run_config_path = os.path.join(run_dir, "config.json")
    
    if os.path.exists(run_config_path):
        with open(run_config_path, 'r', encoding='utf-8') as f:
            run_cfg = json.load(f)
            config.update(run_cfg)
        print(f"Loaded run-specific overrides from: {run_config_path}", flush=True)
        config_path = run_config_path
    else:
        # Mới tạo, copy từ base config
        with open(run_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"Created new run directory: {run_dir}", flush=True)
        config_path = run_config_path
        
    dataset_repo = config.get("HF_CLOUD", {}).get("DATASET_REPO")
    train_cfg = config.get("TRAINING", {})
    
    epochs_warmup = train_cfg.get("EPOCHS_PHASE_1", 10)
    batch_size = train_cfg.get("BATCH_SIZE", 64)
    lr = train_cfg.get("LEARNING_RATE", 1e-4)
    
    hf_token = os.environ.get("HF_TOKEN", "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")
    
    # 1. Kéo Dataset (Features V3, 37 Cột) từ mây về
    print("\u2601\ufe0f Đang tải Dataset Tensor từ HuggingFace HUB...", flush=True)
    tensor_local_dir = os.path.join(run_dir, "data", "tensors")
    os.makedirs(tensor_local_dir, exist_ok=True)
    
    x_path = os.path.join(tensor_local_dir, f"X_tensor_{cfg_id}_tf0.npy")
    y_path = os.path.join(tensor_local_dir, f"Y_tensor_{cfg_id}.npy")
    scaler_src = os.path.join(tensor_local_dir, f"scaler_{cfg_id}.pkl")

    import shutil
    import subprocess
    legacy_tensor_dir = os.path.join(_ROOT, "workspaces", cfg_id, "runs", "legacy_run", "data", "tensors")

    if not os.path.exists(x_path):
        # THỬ ĐỒNG BỘ TỪ HUGGINGFACE TRƯỚC!
        print(f"Không tìm thấy tensor cục bộ. Đang đồng bộ từ HuggingFace cho {cfg_id}...", flush=True)
        try:
            subprocess.run([sys.executable, "scripts/sync_workspaces.py", "pull", cfg_id], cwd=_ROOT, check=True)
            print("Đồng bộ HuggingFace hoàn tất!", flush=True)
        except Exception as e:
            print(f"Lỗi khi đồng bộ HuggingFace: {e}", flush=True)
            
        # DOWNLOAD TENSOR TỪ DATASET REPO (NẾU CÓ)
        if not os.path.exists(x_path):
            # Cố gắng tải từ repo chung argo_workspaces (nơi upload_v3_dataset.py đẩy lên)
            target_repo = "dung5k/argo_workspaces"
            print(f"☁️ Đang tải trực tiếp Tensor từ Dataset Repo: {target_repo}...", flush=True)
            try:
                from huggingface_hub import hf_hub_download
                for filename in [f"X_tensor_{cfg_id}.npy", f"Y_tensor_{cfg_id}.npy", f"scaler_{cfg_id}.pkl"]:
                    remote_path = f"workspaces/{cfg_id}/runs/{run_id}/data/tensors/{filename}"
                    local_dl_path = hf_hub_download(
                        repo_id=target_repo,
                        repo_type="dataset",
                        filename=remote_path,
                        token=hf_token
                    )
                    shutil.copy(local_dl_path, os.path.join(tensor_local_dir, filename))
                print("✅ Tải Tensor thành công từ HF Dataset!", flush=True)
            except Exception as e:
                print(f"❌ Lỗi tải Tensor từ HF Dataset: {e}", flush=True)
            
        # NẾU CÓ TENSOR LOCAL ROOT, COPY SANG
        local_root_tensor_dir = os.path.join(_ROOT, "workspaces", cfg_id, "data", "tensors")
        if not os.path.exists(x_path) and os.path.exists(local_root_tensor_dir):
            import glob
            x_files = glob.glob(os.path.join(local_root_tensor_dir, "X_tensor_*.npy"))
            if x_files:
                print(f"Tìm thấy tensor tại root local, đang copy sang {run_id}...", flush=True)
                for f in os.listdir(local_root_tensor_dir):
                    shutil.copy(os.path.join(local_root_tensor_dir, f), os.path.join(tensor_local_dir, f))
                
        # Nếu vẫn không có, thử copy từ legacy_run
        if not os.path.exists(x_path):
            if os.path.exists(os.path.join(legacy_tensor_dir, f"X_tensor_{cfg_id}.npy")):
                print(f"Bản sao Tensor từ legacy_run sang {run_id}...", flush=True)
                shutil.copy(os.path.join(legacy_tensor_dir, f"X_tensor_{cfg_id}.npy"), x_path)
                shutil.copy(os.path.join(legacy_tensor_dir, f"Y_tensor_{cfg_id}.npy"), y_path)
                shutil.copy(os.path.join(legacy_tensor_dir, f"scaler_{cfg_id}.pkl"), scaler_src)
            else:
                raise FileNotFoundError(
                    f"Không tìm thấy tensor tại {x_path}.\n"
                    f"Hãy chạy trước: python scripts/upload_v3_dataset.py --config {config_path}"
                )

    print("✅ Tensor đã sẵn sàng!", flush=True)

    import glob
    x_files = sorted(glob.glob(os.path.join(tensor_local_dir, f"X_tensor_{cfg_id}_tf*.npy")))
    if not x_files:
        raise FileNotFoundError(f"Không tìm thấy các tensor MTF cho {cfg_id}")
    
    Xs = [np.load(f) for f in x_files]
    Y = np.load(y_path)
    print(f"✅ Tải thành công! Y: {Y.shape}", flush=True)
    for i, X in enumerate(Xs):
        print(f"   X_tf{i}: {X.shape}", flush=True)
    
    # ============================================================
    # KIỂM TRA SỨC KHỎE DỮ LIỆU: Phát hiện sớm data chưa scale
    # ============================================================
    x_abs_max = float(np.max([np.abs(X).max() for X in Xs]))
    x_mean    = float(np.mean([np.abs(X).mean() for X in Xs]))
    print(f"[DATA CHECK] X abs_max={x_abs_max:.4f} | abs_mean={x_mean:.4f}", flush=True)
    if x_abs_max > 100:
        error_msg = f"FATAL ERROR: abs_max={x_abs_max:.1f} khổng lồ. Dữ liệu CHƯA ĐƯỢC SCALE hoặc bị Nổ Variance!\n   → TỪ CHỐI HUẤN LUYỆN. Hãy chạy lại scripts/upload_v3_dataset.py để re-scale chuẩn."
        print(f" ⛔ {error_msg}", flush=True)
        raise ValueError(error_msg)
    else:
        print(f"✅ Dữ liệu đã được scale chuẩn (abs_max < 100).", flush=True)
    
    # Phân bố nhãn Y
    unique, counts = np.unique(Y, return_counts=True)
    label_dist = dict(zip(unique.tolist(), counts.tolist()))
    print(f"[DATA CHECK] Phân bố nhãn Y: {label_dist}", flush=True)

    if False: # Tạm tắt Monthly Split tự động trong đoạn này để đơn giản hóa
        pass
    else:
        # [BẢO MẬT DỮ LIỆU] Chia Validation set chronological với Embargo Gap (khoảng 2 ngày ~ 2880 nến)
        # Sếp chỉ đạo: "Cắt bỏ đi dữ liệu cuối tuần để dữ liệu học và test cách nhau 2 ngày cho chắc"
        print("[DATA SPLIT] Dùng Chronological 80/20 split với Embargo Gap = 2880 nến.", flush=True)
        split_idx = int(len(Y) * 0.8)
        gap = 2880
        
        Xs_tr = [X[:split_idx] for X in Xs]
        Y_tr = Y[:split_idx]
        
        # Kiểm tra để tránh lỗi out-of-bounds nếu data quá ít
        val_start = min(split_idx + gap, len(Y) - 1)
        Xs_va = [X[val_start:] for X in Xs]
        Y_va = Y[val_start:]

    # PHỤC HỒI CLASS WEIGHTS từ tập Train
    unique_tr, counts_tr = np.unique(Y_tr, return_counts=True)
    n_samples = sum(counts_tr)
    n_classes = len(unique_tr)
    # Trọng số = Tổng số mẫu / (Số class * Số mẫu của class đó)
    cw_dict = {u: n_samples / (n_classes * c) for u, c in zip(unique_tr, counts_tr)}
    # Khởi tạo mảng weights đảm bảo độ dài 3 (cho 3 class: 0, 1, 2)
    cw_array = [cw_dict.get(i, 1.0) for i in range(3)]
    
    print(f"[CLASS WEIGHTS] Trọng số cân bằng lớp: {cw_array}", flush=True)

    # Wrap into TensorDataset. PyTorch TensorDataset có thể nhận nhiều tham số (*tensors)
    tensor_args_tr = [torch.tensor(X_tr, dtype=torch.float32) for X_tr in Xs_tr] + [torch.tensor(Y_tr, dtype=torch.long)]
    tensor_args_va = [torch.tensor(X_va, dtype=torch.float32) for X_va in Xs_va] + [torch.tensor(Y_va, dtype=torch.long)]

    train_loader = DataLoader(TensorDataset(*tensor_args_tr), batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(TensorDataset(*tensor_args_va), batch_size=batch_size, shuffle=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\U0001f4bb Đang Train trên nền tảng: {device}", flush=True)
    
    # 2. Sinh mạng neural AAMTV3
    d_model = train_cfg.get("D_MODEL", 128)
    nheads = train_cfg.get("N_HEADS", train_cfg.get("N_HEAD", 8))
    num_layers = train_cfg.get("NUM_LAYERS", 4)
    dropout = train_cfg.get("DROPOUT", 0.25)
    d_ff = train_cfg.get("D_FF", 512)
    
    print(f"[MODEL] Init with: d_model={d_model}, nhead={nheads}, num_layers={num_layers}, dropout={dropout}, d_ff={d_ff}", flush=True)
    
    # [MỚI V2] Đọc tùy chọn kiến trúc cao cấp từ config
    pooling = train_cfg.get("POOLING", "mean")         # 'mean' hoặc 'attention'
    cls_head = train_cfg.get("CLS_HEAD", "simple")      # 'simple' hoặc 'residual'
    layer_drop = train_cfg.get("LAYER_DROP", 0.0)       # 0.0 = tắt, 0.1 = bật
    if pooling != "mean" or cls_head != "simple" or layer_drop > 0:
        print(f"[MODEL V2] Kiến trúc nâng cao: pooling={pooling}, cls_head={cls_head}, layer_drop={layer_drop}", flush=True)
    
    input_dims = [X.shape[2] for X in Xs]
    seq_lens = [X.shape[1] for X in Xs]
    
    model = AAMT_MTF_Model(
        input_dims=input_dims, 
        seq_lens=seq_lens,
        d_model=d_model,
        nhead=nheads,
        num_layers=num_layers,
        dropout=dropout,
        d_ff=d_ff,
        pooling=pooling,
        cls_head=cls_head,
        layer_drop=layer_drop
    )
    
    msg = ""
    # -------------------------------------
    # Kế thừa trọng số cũ
    # -------------------------------------
    if args.scratch:
        msg = "Bỏ qua kế thừa theo cờ --scratch. Đào tạo mới hoàn toàn!"
        print(f"\n[INHERIT] {msg}", flush=True)
    else:
        print("\n[INHERIT] Đang tìm trọng số cũ để kế thừa từ Workspaces...", flush=True)
        import glob
        inherit_cfg_id = config.get("INHERIT_CONFIG_ID", cfg_id)
        if run_dir:
            pattern = os.path.join(_ROOT, "workspaces", inherit_cfg_id, "runs", "**", "brains", "**", f"aamt_v3_{inherit_cfg_id}_final.pth")
        else:
            pattern = os.path.join(_ROOT, "workspaces", inherit_cfg_id, "brains", "**", f"aamt_v3_{inherit_cfg_id}_final.pth")
        all_files = glob.glob(pattern, recursive=True)
        if all_files:
            latest_file = max(all_files, key=os.path.getmtime)
            try:
                state_dict = torch.load(latest_file, map_location=device)
                model_state = model.state_dict()
                for name, param in state_dict.items():
                    if name in model_state:
                        if param.shape != model_state[name].shape:
                            print(f"[INHERIT] ✂️ Tự động Padding layer {name}: {param.shape} -> {model_state[name].shape}", flush=True)
                            new_param = model_state[name].clone()
                            slices = tuple(slice(0, min(s1, s2)) for s1, s2 in zip(param.shape, new_param.shape))
                            new_param[slices] = param[slices]
                            state_dict[name] = new_param
                model.load_state_dict(state_dict, strict=False)
                run_dir = os.path.basename(os.path.dirname(latest_file))
                msg = f"\U0001f449 Kế thừa Model: {run_dir}/{os.path.basename(latest_file)}"
                print(f"  {msg} từ \n  {latest_file}", flush=True)
            except Exception as e:
                msg = f"\u274c Lỗi kế thừa Model: {e}"
                print(f"  {msg}", flush=True)
        else:
            msg = f"❌ Không tìm thấy CSDL trọng số cũ nào cho {inherit_cfg_id} trên HF để kế thừa! Yêu cầu kế thừa đã bị thất bại. Dừng hệ thống!"
            print(f"  {msg}", flush=True)
            raise FileNotFoundError(msg)
            
    tbot = None
    chat_id = None
    import socket
    client_id = os.environ.get("ARGO_CLIENT_ID", "")
    if not client_id or client_id == "UnknownClient":
        client_id = socket.gethostname()[:8]
    try:
        # Cố gắng lấy Telegram credentials
        tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        # 1. Đọc từ cấu hình của Extension VSCode
        settings_path = os.path.join(_ROOT, '.vscode', 'settings.json')
        if os.path.exists(settings_path):
            import re
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not tg_token:
                    m = re.search(r'"antigravityBridge.teleBotToken"\s*:\s*"([^"]+)"', content)
                    if m: tg_token = m.group(1)
                if not tg_chat_id:
                    m = re.search(r'"antigravityBridge.whitelistChatIds"\s*:\s*"([^"]+)"', content)
                    if m: 
                        chat_id_str = m.group(1).split(",")[0].strip()
                        if chat_id_str: tg_chat_id = chat_id_str
            except Exception:
                pass
                
        if tg_chat_id: tg_chat_id = int(tg_chat_id)

        # 2. Danh sách đường dẫn thử theo thứ tự ưu tiên (Fallback)
        tg_config_candidates = [
            os.path.join(_ROOT, ".agent", "telegram_bot_info.json"),
            os.path.join(_ROOT, "tg_config.json"),
        ]
        
        if not tg_token:
            for tg_config_path in tg_config_candidates:
                if os.path.exists(tg_config_path):
                    with open(tg_config_path, "r", encoding="utf-8") as f:
                        tcfg = json.load(f)
                    tg_token   = tcfg.get("bot_token")
                    tg_chat_id = tcfg.get("allowed_chat_ids", [None])[0]
                    if tg_chat_id: tg_chat_id = int(tg_chat_id)
                    break

        if not tg_token or not tg_chat_id:
            raise ValueError("Không tìm thấy Telegram credentials (file JSON hoặc env vars)")

        # Import TelegramBot robust (compatible cả client lẫn host)
        try:
            from tg_helper import TelegramBot
        except ImportError:
            from src.orchestration.tg_helper import TelegramBot

        tbot = TelegramBot(tg_token)
        chat_id = tg_chat_id

        # === THÔNG BÁO KHỞI ĐỘNG TRAINING ĐẦY ĐỦ ===
        fe_cfg     = config.get("FEATURE_ENGINEERING", {})
        macro_keys = list(fe_cfg.get("MACRO_FEATURES", {}).keys())
        label_dist_str = " | ".join([f"C{int(k)}: {v:,}" for k, v in label_dist.items()])
        inherit_icon = "🔁" if not args.scratch else "🆕"
        inherit_text = msg if msg else "Kế thừa trọng số cũ thành công"
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"

        mtf_inputs = fe_cfg.get("MTF_INPUTS", [])
        
        symbols_list = []
        for inp in mtf_inputs:
            sym = inp.get("SYMBOL", "?")
            tf = inp.get("TIMEFRAME", "?")
            w = inp.get("WINDOW_SIZE", "?")
            feats = inp.get("FEATURES", [])
            symbols_list.append(f"  • 🌐 {sym}: <code>{tf} ({w} nến) - {len(feats)} features</code>")
        symbols_str = "\n".join(symbols_list)

        start_msg = (
            f"🚀 <b>[{client_id}] BẮT ĐẦU TRAINING</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Cấu hình:</b> <code>{cfg_id}</code> (v{config.get('VERSION', '?')})\n"
            f"🎯 <b>Phiên giao dịch:</b> {config.get('SESSION', '?').upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Dữ liệu (MTF: {len(Xs)} frames):</b>\n"
            f"{symbols_str}\n"
            f"  • -----------------------\n"
            f"  • Features mỗi TF: <code>{Xs[0].shape[2]}</code>\n"
            f"  • Tổng Samples: <code>{Xs[0].shape[0]:,}</code>\n"
            f"  • Train/Val: <code>{len(Xs_tr[0]):,} / {len(Xs_va[0]):,}</code>\n"
            f"  • Phân bố Nhãn: <code>{label_dist_str}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ <b>Siêu tham số:</b>\n"
            f"  • TP={fe_cfg.get('TP_PIPS')} | SL={fe_cfg.get('SL_PIPS')} | MaxHold={fe_cfg.get('MAX_HOLD_BARS')}\n"
            f"  • LR=<code>{lr}</code> | Batch=<code>{batch_size}</code> | WarmUp=<code>{epochs_warmup}</code> ep\n"
            f"  • Device: <code>{device}</code> ({gpu_name})\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{inherit_icon} <b>Chế độ:</b> {inherit_text}"
        )
        tbot.send_message(chat_id, start_msg)
        print(f"✅ [TELEGRAM] Đã gửi thông báo khởi động!", flush=True)
    except Exception as e:
        print(f"⚠️ [TELEGRAM] Lỗi gửi thông báo khởi động: {e}", flush=True)
    
    model.to(device)
    
    class_weights_tensor = torch.tensor(cw_array, dtype=torch.float32).to(device)
    focal_gamma = train_cfg.get("FOCAL_GAMMA", 0.0)
    mse_gate = train_cfg.get("MSE_GATE_PERCENTILE", 0.0)
    recon_weight = train_cfg.get("RECON_LOSS_WEIGHT", 1.0)
    label_smoothing = train_cfg.get("LABEL_SMOOTHING", 0.15)
    print(f"[LOSS] Khởi tạo AAMT_JointLoss với focal_gamma = {focal_gamma} | mse_gate = {mse_gate} | lambda_recon = {recon_weight} | label_smoothing = {label_smoothing}", flush=True)
    criterion = AAMT_JointLoss(
        class_weights=class_weights_tensor, 
        focal_gamma=focal_gamma, 
        mse_gate_percentile=mse_gate,
        lambda_recon=recon_weight,
        label_smoothing=label_smoothing
    )
    weight_decay = train_cfg.get("WEIGHT_DECAY", 1e-4)
    # Tách Parameter Groups: log_vars của criterion không được dùng weight_decay để tránh bị ép về 0
    optimizer_grouped_parameters = [
        {"params": model.parameters(), "weight_decay": weight_decay},
        {"params": criterion.parameters(), "weight_decay": 0.0, "lr": lr * 0.1}
    ]
    optimizer = optim.AdamW(optimizer_grouped_parameters, lr=lr)
    phoenix = None  # Đã tắt Auto Healing

    # [V2] Chọn Learning Rate Scheduler theo config
    lr_scheduler_type = train_cfg.get("LR_SCHEDULER", "plateau")  # 'plateau' hoặc 'cosine_warm'
    if lr_scheduler_type == "cosine_warm":
        # Cosine Annealing with Warm Restarts — khám phá tốt hơn cho data khó
        lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=15, T_mult=2, eta_min=1e-6
        )
        print(f"[SCHEDULER] CosineAnnealingWarmRestarts (T_0=15, T_mult=2)", flush=True)
    else:
        # [PHÁC ĐỒ 2] Learning Rate Decay — Giảm LR 50% sau X epoch không cải thiện CE Loss val
        # Ngăn optimizer đạp vỡ vùng tối ưu sau khi đạt đỉnh (như Epoch 19 → 308)
        patience_val = train_cfg.get("PATIENCE", 10)
        lr_scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=patience_val,
            min_lr=1e-6
        )
        print(f"[SCHEDULER] ReduceLROnPlateau (patience={patience_val}, factor=0.5)", flush=True)
    # [PHÁC ĐỒ 3] Early Stopping — Dừng nếu CE Loss val tăng liên tiếp X epoch
    # Ngăn mạng "ngu đi" khi đang tự huỷ hoại phân bố Softmax
    _ES_PATIENCE     = train_cfg.get("ES_PATIENCE", 20)   # Số epoch chịu đựng CE tăng
    _es_streak       = 0    # Biến đếm streak tăng hiện tại
    _es_best_ce_val  = float('inf')  # CE val tốt nhất từ trước đến nay
    
    # 3. PHASE 1 WARM-UP (Chỉ chạy 1 lần)
    model = train_warmup_phase(model, train_loader, criterion, optimizer, device, epochs=epochs_warmup)
    
    # Tự động tối ưu CUDNN nếu dùng GPU
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
    
    # Môi trường log giống V2
    import shutil
    model_dir = os.path.join(run_dir, "brains")
    results_dir = os.path.join(run_dir, "results")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    import shutil
    shutil.copy(config_path, os.path.join(results_dir, os.path.basename(config_path)))

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

    sys.stdout = _TeeLogger(os.path.join(results_dir, "train_v3.log"))
    
    # scaler_src đã được trỏ đến thư mục workspaces ở bước trên
    if os.path.exists(scaler_src):
        shutil.copy(scaler_src, os.path.join(model_dir, f"scaler_{cfg_id}.pkl"))
        print(f"[PACK] Kèm theo scaler file vào: {model_dir}", flush=True)

    # 4. PHASE 2 FINE-TUNING (Vòng lặp vĩnh cửu)
    print("--- \U0001f680 BẮT ĐẦU VÒNG LẶP FINE-TUNING ĐA NHIỆM (Infinite Loop) ---", flush=True)
    epoch = 0
    best_score = 0.0
    best_win_rate = 0.0
    # Bỏ qua logic tạo repo riêng lẻ vì đã dùng chung dung5k/argo_workspaces
    
    report_interval_seconds = train_cfg.get("TELEGRAM_REPORT_INTERVAL_MINUTES", 10) * 60
    last_report_time = time.time()
    
    # Đọc cấu hình giới hạn số lượng lệnh, mặc định 50-500
    freq_min = config.get("TRAINING", {}).get("FREQ_MIN_N", 50)
    freq_max = config.get("TRAINING", {}).get("FREQ_MAX_N", 500)
    
    while True:
        epoch += 1
        current_optimizer = optimizer
        tr_loss, tr_recon, tr_class = train_finetuning_phase(model, train_loader, criterion, current_optimizer, device)
        eval_res = evaluate_val_set(model, val_loader, criterion, device, freq_min_N=freq_min, freq_max_N=freq_max)

        comp_score  = eval_res.composite_score()
        val_ce_loss = eval_res.val_ce   # Sử dụng trực tiếp CrossEntropy Loss từ evaluator
        current_lr  = optimizer.param_groups[0]['lr']
        print(f"[Epoch {epoch}] Loss(MSE:{tr_recon:.4f}/CE:{tr_class:.4f}) | LR={current_lr:.2e} | Val {eval_res.format_summary().replace(chr(10), ' | ')}", flush=True)

        # [V2] Báo scheduler bước — tương thích cả 2 loại
        if lr_scheduler_type == "cosine_warm":
            lr_scheduler.step()  # CosineAnnealing step mỗi epoch
        else:
            lr_scheduler.step(val_ce_loss)  # ReduceLROnPlateau step theo val loss

        # [PHÁC ĐỒ 3] Early Stopping: theo dõi CE Loss val
        if val_ce_loss < _es_best_ce_val:
            _es_best_ce_val = val_ce_loss
            _es_streak      = 0
        else:
            _es_streak += 1
            if _es_streak >= _ES_PATIENCE:
                es_msg = f"\n🛑 EARLY STOPPING kích hoạt tại Epoch {epoch}!\n"
                es_msg += f"   CE Loss val đã tăng liên tiếp {_es_streak} epoch ({_es_best_ce_val:.4f} → {val_ce_loss:.4f})\n"
                es_msg += f"   Best model đã được lưu. Dừng training để bảo toàn trọng số tốt nhất."
                print(es_msg, flush=True)
                if tbot and chat_id:
                    try:
                        tbot.send_message(chat_id, f"🛑 <b>[{client_id}] HỆ THỐNG DỪNG ĐÀO TẠO (EARLY STOPPING)</b>\n" + es_msg)
                    except Exception:
                        pass
                break
        
        improved = comp_score > best_score
        if improved:
            best_score      = comp_score
            best_win_rate   = max([float(m.win_rate) for m in eval_res.threshold_metrics]) if eval_res.threshold_metrics else 0.0
            _es_streak      = 0           # Reset Early Stopping khi có kỷ lục mới
            _es_best_ce_val = val_ce_loss  # Cập nhật ngưỡng CE tốt nhất
            print(f"  🏆 [ARGO2] ĐỈNH MỚI! Composite Score = {best_score:.4f}. Lưu model...", flush=True)
            
            # Save local
            model_export_path = os.path.join(model_dir, f"aamt_v3_{cfg_id}_final.pth")
            torch.save(model.state_dict(), model_export_path)
            
            # Ghi json metrics theo chuẩn V2
            try:
                session_name = config.get("SESSION", "ny").lower()
                target_sym = config.get("TARGET_SYMBOL", "xauusd").lower().replace('m', '')
                nfe = config.get("MODEL_DIMENSIONS", {}).get("num_features", 38)
                t_metrics = []
                for m in eval_res.threshold_metrics:
                    t_metrics.append({
                        "threshold": float(m.threshold),
                        "total_signals": int(m.total_signals),
                        "win_rate": float(m.win_rate),
                        "avg_win_return": 0.001,
                        "avg_loss_return": 0.001,
                        "ev_score": float(m.balanced_score),
                        "sharpe_score": 0.0,
                        "total_buy": int(m.total_signals // 2),  # Giả lập tạm
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
                                "win_rates": [float(m.win_rate) for m in eval_res.threshold_metrics],
                                "thresholds": [float(m.threshold) for m in eval_res.threshold_metrics],
                                "totals": [int(m.total_signals) for m in eval_res.threshold_metrics]
                            }
                        }
                    }
                }
                with open(os.path.join(results_dir, "training_metrics_v3.json"), "w", encoding="utf-8") as fm:
                    json.dump(metrics_data, fm, indent=4)
            except Exception as e:
                print(f"  \u274c Lỗi lưu JSON metrics: {e}", flush=True)

            # Đẩy Chart Telegram
            plot_and_notify_v3(eval_res, cfg_id, epoch, results_dir)
            
            # Chỉ đẩy đúng thư mục run hiện tại lên HuggingFace nếu có bật SYNC_CHUNKS
            try:
                sync_chunks = config.get("HF_CLOUD", {}).get("SYNC_CHUNKS", True)
                if sync_chunks:
                    print(f"  ☁️ Đang PUSH run {run_id} lên HF (Background)...", flush=True)
                    from scripts.sync_workspaces import push_run
                    import threading
                    threading.Thread(target=push_run, args=(cfg_id, run_id), daemon=True).start()
            except Exception as e:
                print(f"  \u274c Lỗi Push HF: {e}", flush=True)
            
            if phoenix:
                pass
            last_report_time = time.time()
        else:
            pass # Continuous wait

        # Báo cáo Telegram định kỳ
        current_time = time.time()
        if (current_time - last_report_time) >= report_interval_seconds:
            last_report_time = current_time
            plot_and_notify_v3(eval_res, cfg_id, epoch, results_dir, is_periodic=True)
            if tbot and chat_id:
                try:
                    report_msg = f"⏳ <b>[{client_id}] [AAMT V3 ({cfg_id})] Báo cáo chặng định kỳ (Epoch {epoch})</b>\n"
                    report_msg += f"🔥 Tr Loss (MSE:{tr_recon:.4f} | CE:{tr_class:.4f})\n\n"
                    report_msg += f"📊 <b>Kết quả Validation:</b>\n{eval_res.format_summary()}"
                    tbot.send_message(chat_id, report_msg)
                    print(f"[TELEGRAM] Đã gửi báo cáo định kỳ cho epoch {epoch} sau mỗi {report_interval_seconds//60} phút", flush=True)
                except Exception as e:
                    print(f"[TELEGRAM] Lỗi gửi báo cáo: {e}", flush=True)

    # ==========================================
    # QUẢN LÝ DUNG LƯỢNG & ĐỒNG BỘ SAU TRAINING
    # ==========================================
    # QUẢN LÝ DUNG LƯỢNG & ĐỒNG BỘ SAU TRAINING
    # ==========================================
    sys.stdout = sys.__stdout__
    print(f"\n[CLEANUP] Đã kết thúc Training. Kỷ lục Score: {best_score:.4f} | Kỷ lục Win Rate: {best_win_rate*100:.2f}%", flush=True)
    metrics_path = os.path.join(results_dir, "training_metrics_v3.json")
    if not os.path.exists(metrics_path):
        with open(metrics_path, "w", encoding="utf-8") as fm:
            json.dump({
                "BEST_VLOSS": {
                    "composite_score": float(best_score),
                    "win_rates": [float(best_win_rate)]
                }
            }, fm)
            
    print(f"🏆 Win Rate {best_win_rate*100:.2f}% >= 60%. Đang PUSH lên HuggingFace...", flush=True)
    try:
        from scripts.sync_workspaces import push_run
        push_run(cfg_id, run_id)
        print("✅ Đã Push thành công!", flush=True)
        if tbot and chat_id:
            tbot.send_message(chat_id, f"☁️ <b>[{client_id}] Đã đồng bộ lên HF</b>\nRun: {run_id}\nScore: {best_score:.4f}")
    except Exception as e:
        print(f"❌ Lỗi khi Push: {e}", flush=True)

if __name__ == "__main__":
    main()
