import json
import os
import matplotlib.pyplot as plt

from src.orchestration.tg_helper import TelegramBot

def main():
    with open("tg_config.json", "r") as f:
        cfg = json.load(f)
    bot = TelegramBot(cfg["bot_token"])
    chat_id = cfg["allowed_chat_ids"][0]
    
    thresholds = [0.50, 0.51, 0.51, 0.52]
    wrs = [0.489, 0.524, 0.536, 0.615]
    totals_t = [814, 515, 263, 91]
    max_thresh = 0.52
    
    chart_path = "demo_peak_chart.png"
    plt.figure(figsize=(8, 4))
    x_vals = [t*100 for t in thresholds]
    y_vals = [w*100 for w in wrs]
    plt.plot(x_vals, y_vals, marker='o', linestyle='-', color='indigo', linewidth=2)
    for xv, yv, tot in zip(x_vals, y_vals, totals_t):
        plt.text(xv, yv + 0.5, f"{yv:.1f}%\n({tot}L)", fontsize=8, ha='center', va='bottom')
    plt.title(f"Peak Performance [Demo] | MaxTh={max_thresh:.2f}")
    plt.xlabel("Threshold (%)")
    plt.ylabel("Win Rate (%)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.ylim(min(45, min(y_vals)-5), max(85, max(y_vals)+5))
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    
    text = "🏆 [Demo] KHÔI PHỤC BẢN VẼ: Lỗi cài đặt Plot trên các máy trạm vừa được phát hiện. Đây là Ảnh minh họa do Antigravity phác thảo nhanh."
    bot.send_photo(chat_id, chart_path, caption=text)
    print("Sent demo chart!")

if __name__ == "__main__":
    main()
