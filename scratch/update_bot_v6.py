with open(r'd:\DungLA\client1\src\bot_v6\bot_v6.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update TARGET_SYMBOL -> TARGET_DISPLAY_NAME
content = content.replace('💹 Mã: {TARGET_SYMBOL} | Chế độ: {mode_info}', '💹 Mã: {TARGET_DISPLAY_NAME} | Chế độ: {mode_info}')
content = content.replace('f"AAMT TERMINATOR V6 - {TARGET_SYMBOL}"', 'f"AAMT TERMINATOR V6 - {TARGET_DISPLAY_NAME}"')
content = content.replace('f"🌌 {TARGET_SYMBOL} MASTER V6 🌌"', 'f"🌌 {TARGET_DISPLAY_NAME} MASTER V6 🌌"')
content = content.replace('lbl_target.config(text=TARGET_SYMBOL)', 'lbl_target.config(text=TARGET_DISPLAY_NAME)')
content = content.replace('f"🤖 [BOT V3 MASTER KHỞI ĐỘNG]', 'f"🤖 [BOT V6 MASTER KHỞI ĐỘNG]')

# 2. Update _load_brain_metrics
old_metrics = '''
            lines.append(f"📊 Phiên: {sess_name.upper()}")
            lines.append(f"⭐ Score: {score:.4f}")
            lines.append(f"🎯 WR: {best_wr:.1%} @thr={best_thr:.3f}")
            lines.append(f"📈 Signals: {best_sigs} | Epoch: {epoch}")
            lines.append(f"📉 Val Loss: {val_loss:.4f}")
'''
new_metrics = '''
            lines.append(f"📊 Phiên: {sess_name.upper()}")
            lines.append(f"⭐ Score: {score:.4f} | Val Loss: {val_loss:.4f}")
            lines.append(f"📈 Epoch: {epoch}")
            lines.append("🎯 Phân bổ Ngưỡng WinRate:")
            
            for tm in sorted(best.get('threshold_metrics', []), key=lambda x: x.get('threshold', 0)):
                thr = tm.get('threshold', 0)
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                if sigs >= 5:
                    prefix = "🌟" if thr == best_thr else "  "
                    lines.append(f"{prefix} {thr:.2f}: WR {wr:.1%} ({sigs} lệnh)")
'''

if old_metrics.lstrip() in content:
    content = content.replace(old_metrics.lstrip(), new_metrics.lstrip())
else:
    print("Could not find old metrics string exactly!")

with open(r'd:\DungLA\client1\src\bot_v6\bot_v6.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated bot_v6.py successfully!")
