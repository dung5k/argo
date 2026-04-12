import json
import os
import matplotlib.pyplot as plt

from src.orchestration.tg_helper import TelegramBot

def compute_winrates(thresholds, all_probs, all_labels):
    wrs, totals = [], []
    for pt in thresholds:
        plo = 1.0 - pt
        n = 0
        correct = 0
        for p, l in zip(all_probs, all_labels):
            if p > pt:
                n += 1
                if l == 1: correct += 1
            elif p < plo:
                n += 1
                if l == 0: correct += 1
        wrs.append(correct / n if n > 0 else 0)
        totals.append(n)
    return wrs, totals

def main():
    import random
    with open("tg_config.json", "r") as f:
        cfg = json.load(f)
    bot = TelegramBot(cfg["bot_token"])
    chat_id = cfg["allowed_chat_ids"][0]
    
    # Fake some probabilities
    all_probs = [random.uniform(0.4, 0.6) for _ in range(5000)]
    all_labels = [1 if p + random.uniform(-0.1, 0.1) > 0.50 else 0 for p in all_probs]

    max_thresh = 0.55
    plot_thresholds = [0.50 + (max_thresh - 0.50) * i / 9 for i in range(10)]
    plot_wrs, plot_totals = compute_winrates(plot_thresholds, all_probs, all_labels)
    
    chart_path = "demo_peak_chart_10.png"
    plt.figure(figsize=(10, 5))
    x_vals = [t*100 for t in plot_thresholds]
    y_vals = [w*100 for w in plot_wrs]
    plt.plot(x_vals, y_vals, marker='o', linestyle='-', color='indigo', linewidth=2)
    for xv, yv, tot in zip(x_vals, y_vals, plot_totals):
        plt.text(xv, yv + 0.5, f"{yv:.1f}%\n({tot}L)", fontsize=8, ha='center', va='bottom')
    plt.title(f"Peak Performance [Demo 10 Pts] | MaxTh={max_thresh:.2f}")
    plt.xlabel("Threshold (%)")
    plt.ylabel("Win Rate (%)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.ylim(min(45, min(y_vals)-5), max(85, max(y_vals)+5))
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    
    text = "🚀 [CẬP NHẬT] Yêu cầu VẼ CHI TIẾT ĐỒ THỊ đã hoàn tất! Đây là ảnh phác thảo form phân giải cao (10 points) sẽ được gửi cho anh từ Epoch thực tế tiếp theo."
    bot.send_photo(chat_id, chart_path, caption=text)
    print("Sent demo 10-point chart!")

if __name__ == "__main__":
    main()
