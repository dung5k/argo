import sys

filepath = r'd:\DungLA\client1\src\training_v6\train_v6.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We know the last part of the file is the Cleanup block. Let's find # QUáº¢N LÃ  DUNG LÆ¯á»¢NG & Ä á»’NG Bá»˜ SAU TRAINING
import re
new_tail = '''    # ==========================================
    # QUẢN LÝ DUNG LƯỢNG & ĐỒNG BỘ SAU TRAINING
    # ==========================================
    sys.stdout = sys.__stdout__
    print(f"\\n[CLEANUP] Đã kết thúc Training. Kỷ lục Score: {best_score:.4f} | Kỷ lục Win Rate: {best_win_rate*100:.2f}%", flush=True)
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
            tbot.send_message(chat_id, f"☁️ <b>[{client_id}] Đã đồng bộ lên HF</b>\\nRun: {run_id}\\nScore: {best_score:.4f}")
    except Exception as e:
        print(f"❌ Lỗi khi Push: {e}", flush=True)

if __name__ == "__main__":
    main()
'''

# Find the start of the cleanup section
parts = content.split('    # ==========================================')
if len(parts) >= 3:
    content = '    # =========================================='.join(parts[:-1]) + new_tail

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
