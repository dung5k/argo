import json, html
from src.orchestration.tg_helper import TelegramBot

def test_send():
    with open("tg_config.json", "r") as f:
        cfg = json.load(f)
    bot = TelegramBot(cfg["bot_token"])
    chat_id = cfg["allowed_chat_ids"][0]
    
    # Fake chart
    with open("test_chart.png", "wb") as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

    last_line = "Epoch 0001 | VLoss: 0.6932 | LR: 1.00e-04 | WR: 51.1% | MaxTh: 0.59 | Time: 530.2s"
    current_peak = "🏆 ĐỈNH MỚI CHO TIÊU CHÍ: [L3_1.4_L4_1.0] MaxTh=0.55 | >50%: 51.1%(11397L) | >53%: 50.5%(3488L) | >56%: 53.5%(417L) | >59%: 57.9%(38L)"
    
    pfx = "<b>client1</b> [Ver: v2.0 | Mã: XAUUSD]"
    send_msg = f"🏆 {pfx} TÌM THẤY MẪU MỚI!\n"
    send_msg += f"<pre>{html.escape(last_line.strip())}</pre>\n"
    send_msg += f"<pre>{html.escape(current_peak.strip())}</pre>\n"
    
    ok = bot.send_photo(chat_id, "test_chart.png", caption=send_msg)
    print("Send result:", ok)

if __name__ == "__main__":
    test_send()
