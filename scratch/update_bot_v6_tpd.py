with open(r'd:\DungLA\client1\src\bot_v6\bot_v6.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_metrics = '''
            for tm in sorted(best.get('threshold_metrics', []), key=lambda x: x.get('threshold', 0)):
                thr = tm.get('threshold', 0)
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                if sigs >= 5:
                    prefix = "🌟" if thr == best_thr else "  "
                    lines.append(f"{prefix} {thr:.2f}: WR {wr:.1%} ({sigs} lệnh)")
'''

new_metrics = '''
            val_days = 8.0 if "weekend" in sess_name.lower() else 20.0
            for tm in sorted(best.get('threshold_metrics', []), key=lambda x: x.get('threshold', 0)):
                thr = tm.get('threshold', 0)
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                if sigs >= 5:
                    tpd = sigs / val_days
                    prefix = "🌟" if thr == best_thr else "  "
                    lines.append(f"{prefix} {thr:.2f}: WR {wr:.1%} ({sigs} lệnh | ~{tpd:.1f} l/ngày)")
'''

if old_metrics.lstrip() in content:
    content = content.replace(old_metrics.lstrip(), new_metrics.lstrip())
    with open(r'd:\DungLA\client1\src\bot_v6\bot_v6.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated bot_v6.py successfully!")
else:
    print("Could not find old metrics string exactly!")
