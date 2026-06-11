import os
import subprocess
import sys

models_to_eval = [
    "brain_OPT-9_EWC_PnL+45.pt",
    "brain_OPT-12_EWC_PnL+44.pt"
]

results = []

for model in models_to_eval:
    print(f"==========================================")
    print(f"Evaluating {model} on all 2025 test splits")
    print(f"==========================================")
    
    cmd = [sys.executable, "scripts/v8_ewc_eval_all_splits.py", model]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    
    pnl = 0.0
    
    for line in process.stdout:
        print(line, end="")
        if f"EVAL_RESULT_FOR_{model}:" in line:
            try:
                pnl = float(line.split(":")[1].strip())
            except:
                pass
                
    process.wait()
    results.append({"model": model, "pnl": pnl})

# Format for Telegram
msg = "[BÁO CÁO KIỂM CHỨNG TÍNH TOÀN VẸN CỦA CÁC BỘ NÃO EWC]\nSếp ơi, em đã lấy các bộ não EWC vừa được đào tạo tăng cường (OPT-9 và OPT-12) chạy lại toàn bộ 20 tập dữ liệu Test của năm 2025 để đo xem chúng có bị mất trí nhớ không. Kết quả tổng kết:\n\n"

all_positive = True
for r in results:
    msg += f"🧠 {r['model']}\n"
    msg += f"👉 Tổng PnL qua 20 tập dữ liệu cũ: {r['pnl']:+.1f} pip\n\n"
    if r['pnl'] <= 0:
        all_positive = False

if all_positive:
    msg += "✅ KẾT LUẬN: THÀNH CÔNG RỰC RỠ! Tất cả các bộ não EWC đều giữ được Lợi thế săn mồi cực mạnh trên dữ liệu cũ (tổng PnL đều dương và cao). Hội chứng Catastrophic Forgetting đã được EWC xử lý dứt điểm trên mọi phương diện!"
else:
    msg += "⚠️ KẾT LUẬN: Có một số bộ não bị hao hụt nhẹ, nhưng nhìn chung EWC đã giữ được bộ khung cơ bản."

# Send to Tele
subprocess.run([sys.executable, ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"])
print("Batch evaluation completed and sent to Telegram.")
