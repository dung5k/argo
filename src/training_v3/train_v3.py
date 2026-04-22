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
    Giai đoạn 1: Dạy AI cách nhìn biểu đồ (Tách nhiễu) bằng cách chỉ bật Reconstruction Loss
    """
    model.train()
    model.to(device)
    
    # Ép trọng số Joint Loss: TẮT hoàn toàn nhánh Dự đoán, DỒN 100% lực cho nhánh Giải nén
    criterion.set_lambdas(lambda_recon=1.0, lambda_class=0.0)
    
    print(f"--- \U0001f680 BẮT ĐẦU WARM-UP AUTOENCODER ({epochs} Epochs) ---", flush=True)
    for epoch in range(epochs):
        total_recon_loss = 0.0
        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            reconstructed, logits, _ = model(inputs)
            loss, l_recon, l_class = criterion(reconstructed, inputs, logits, targets)
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

    for inputs, targets in train_loader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        reconstructed, logits, _ = model(inputs)
        loss, l_recon, l_class = criterion(reconstructed, inputs, logits, targets)
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
    
    evaluator = WinRateEvaluatorV3(freq_min_N=freq_min_N, freq_max_N=freq_max_N)
    res = evaluator.evaluate(cat_logits, cat_labels, avg_loss, avg_recon)
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
    
    x_path = os.path.join(tensor_local_dir, f"X_tensor_{cfg_id}.npy")
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

    print("\u2705 Tensor đã sẵn sàng!", flush=True)

    X = np.load(x_path)
    Y = np.load(y_path)
    print(f"\u2705 Tải thành công! Kích thước X: {X.shape}, Y: {Y.shape}", flush=True)
    
    # ============================================================
    # KIỂM TRA SỨC KHỎE DỮ LIỆU: Phát hiện sớm data chưa scale
    # ============================================================
    x_abs_max = float(np.abs(X).max())
    x_mean    = float(np.abs(X).mean())
    print(f"[DATA CHECK] X abs_max={x_abs_max:.4f} | abs_mean={x_mean:.4f}", flush=True)
    if x_abs_max > 100:
        error_msg = f"FATAL ERROR: abs_max={x_abs_max:.1f} khổng lồ. Dữ liệu CHƯA ĐƯỢC SCALE hoặc bị Nổ Variance!\n   → TỪ CHỐI HUẤN LUYỆN. Hãy chạy lại scripts/upload_v3_dataset.py để re-scale chuẩn."
        print(f" \u26d4 {error_msg}", flush=True)
        raise ValueError(error_msg)
    else:
        print(f"\u2705 Dữ liệu đã được scale chuẩn (abs_max < 100).", flush=True)
    
    # Phân bố nhãn Y
    unique, counts = np.unique(Y, return_counts=True)
    label_dist = dict(zip(unique.tolist(), counts.tolist()))
    print(f"[DATA CHECK] Phân bố nhãn Y: {label_dist}", flush=True)

    # Đã gỡ bỏ tính toán trọng số cân bằng lớp (class weights) để chống conflict với Triple Barrier.
    # Mạng sẽ học thẳng vào phân bố nhãn thật.

    # Chia Validation set - BẮT BUỘC shuffle=False để bảo toàn trục thời gian (Time-Series)
    # shuffle=True gây Data Leakage: mẫu i và i+1 chia sẻ 59/60 nến trùng nhau với Sliding Window
    X_tr, X_va, Y_tr, Y_va = train_test_split(X, Y, test_size=0.2, shuffle=False)
    
    train_loader = DataLoader(TensorDataset(torch.tensor(X_tr, dtype=torch.float32), torch.tensor(Y_tr, dtype=torch.long)), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.tensor(X_va, dtype=torch.float32), torch.tensor(Y_va, dtype=torch.long)), batch_size=batch_size, shuffle=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\U0001f4bb Đang Train trên nền tảng: {device}", flush=True)
    
    # 2. Sinh mạng neural AAMTV3
    model = AAMT_Model(input_dim=X.shape[2], seq_len=X.shape[1])
    
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
        # Cố gắng lấy Telegram credentials từ file JSON rồi fallback sang biến môi trường
        tg_token = None
        tg_chat_id = None

        # Danh sách đường dẫn thử theo thứ tự ưu tiên
        tg_config_candidates = [
            os.path.join(_ROOT, ".agent", "telegram_bot.json"),
            os.path.join(_ROOT, "tg_config.json"),
        ]
        for tg_config_path in tg_config_candidates:
            if os.path.exists(tg_config_path):
                with open(tg_config_path, "r", encoding="utf-8") as f:
                    tcfg = json.load(f)
                tg_token   = tcfg.get("bot_token")
                tg_chat_id = tcfg.get("allowed_chat_ids", [None])[0]
                break

        if not tg_token:
            # Fallback: đọc từ biến môi trường (client không có file config)
            tg_token   = os.environ.get("TELEGRAM_BOT_TOKEN")
            tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            if tg_chat_id:
                tg_chat_id = int(tg_chat_id)

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

        start_msg = (
            f"🚀 <b>[{client_id}] BẮT ĐẦU TRAINING</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Cấu hình:</b> <code>{cfg_id}</code> (v{config.get('VERSION', '?')})\n"
            f"🎯 <b>Target:</b> {config.get('TARGET_SYMBOL', '?')} — Phiên {config.get('SESSION', '?').upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Dữ liệu:</b>\n"
            f"  • Tensor X: <code>{X.shape}</code>\n"
            f"  • Samples: <code>{X.shape[0]:,}</code> | Window: <code>{X.shape[1]}</code> nến | Features: <code>{X.shape[2]}</code>\n"
            f"  • Train/Val: <code>{len(X_tr):,} / {len(X_va):,}</code>\n"
            f"  • Nhãn: <code>{label_dist_str}</code>\n"
            f"  • Macro: <code>{', '.join(macro_keys)}</code>\n"
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

    criterion = AAMT_JointLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    phoenix = None  # Đã tắt Auto Healing

    # [PHÁC ĐỒ 2] Learning Rate Decay — Giảm LR 50% sau 10 epoch không cải thiện CE Loss val
    # Ngăn optimizer đạp vỡ vùng tối ưu sau khi đạt đỉnh (như Epoch 19 → 308)
    lr_scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=10,
        min_lr=1e-6
    )
    # [PHÁC ĐỒ 3] Early Stopping — Dừng nếu CE Loss val tăng liên tiếp 20 epoch
    # Ngăn mạng "ngu đi" khi đang tự huỷ hoại phân bố Softmax
    _ES_PATIENCE     = 20   # Số epoch chịu đựng CE tăng
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
        val_ce_loss = eval_res.val_loss   # CE-dominated val loss
        current_lr  = optimizer.param_groups[0]['lr']
        print(f"[Epoch {epoch}] Loss(MSE:{tr_recon:.4f}/CE:{tr_class:.4f}) | LR={current_lr:.2e} | Val {eval_res.format_summary().replace(chr(10), ' | ')}", flush=True)

        # [PHÁC ĐỒ 2] Báo ReduceLROnPlateau bước CE Loss val
        lr_scheduler.step(val_ce_loss)

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
            _es_streak      = 0           # Reset Early Stopping khi có kỷ lục mới
            _es_best_ce_val = val_ce_loss  # Cập nhật ngưỡng CE tốt nhất
            print(f"  🌟 KỶ LỤC MỚI! Composite Score = {best_score:.4f}. Lưu model...", flush=True)
            
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
            
            # Chỉ đẩy đúng thư mục run hiện tại lên HuggingFace
            try:
                print(f"  ☁️ Đang PUSH run {run_id} lên HF...", flush=True)
                from scripts.sync_workspaces import push_run
                push_run(cfg_id, run_id)
                print(f"  ☁️ PUSH run hoàn tất!", flush=True)
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

if __name__ == "__main__":
    main()
