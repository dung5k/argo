import os
import re

filepath = r'd:\DungLA\client1\src\bot_v6\bot_v6.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: _load_brain_metrics logic
old_logic = '''            best_wr, best_thr, best_sigs = 0, 0, 0
            for tm in best.get('threshold_metrics', []):
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                if wr > best_wr and sigs >= 10:
                    best_wr = wr
                    best_thr = tm.get('threshold', 0)
                    best_sigs = sigs'''

new_logic = '''            best_wr, best_thr, best_sigs = 0, 0, 0
            for tm in best.get('threshold_metrics', []):
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                if wr >= best_wr and sigs >= 1:
                    best_wr = wr
                    best_thr = tm.get('threshold', 0)
                    best_sigs = sigs'''

content = content.replace(old_logic, new_logic)

# Fix 2: Return tuple
old_ret = '''        return '\n'.join(lines)
    except Exception as e:
        return f"🧠 Não: {run_id}\n❌ Lỗi đọc metrics: {e}"'''
new_ret = '''        return '\n'.join(lines), best_thr
    except Exception as e:
        return f"🧠 Não: {run_id}\n❌ Lỗi đọc metrics: {e}", 0.7'''

content = content.replace(old_ret, new_ret)
content = content.replace('''return f"🧠 Não: {run_id}\n📊 Không tìm thấy metrics"''', '''return f"🧠 Não: {run_id}\n📊 Không tìm thấy metrics", 0.7''')

# Fix 3: Call site of _load_brain_metrics
old_call = '''                # Tải training metrics cho tooltip
                gui_brain_tooltip = _load_brain_metrics(target_run_id, cfg_id)'''
new_call = '''                # Tải training metrics cho tooltip
                gui_brain_tooltip, best_thr = _load_brain_metrics(target_run_id, cfg_id)
                if best_thr > 0:
                    engine.prob_threshold = best_thr
                print(f"[BOT V6] Đã cài đặt prob_threshold = {engine.prob_threshold}")'''

content = content.replace(old_call, new_call)

# Fix 4: V3 -> V6 and Action mapping
old_msg = '''        display_action = str(action)
        # Nếu bot V3 có hỗ trợ open_positions...
        if hasattr(trade_manager, 'get_open_positions'):
            for pos in trade_manager.get_open_positions():
                ticket = getattr(pos, 'ticket', '?')
                side = 'BUY' if getattr(pos, 'type', None) == mt5.ORDER_TYPE_BUY else 'SELL'
                if (side == 'SELL' and action == 'SELL') or (side == 'BUY' and action == 'BUY'):
                    display_action = f"GIỮ LỆNH {side} (#{ticket})"
                    break

        msg_pred = (
            f"🎯 KẾT QUẢ PIPELINE V3:\\n"'''

new_msg = '''        if action == 2:
            display_action = "BUY"
        elif action == 0:
            display_action = "SELL"
        else:
            display_action = "HOLD"
            
        # Nếu bot V3 có hỗ trợ open_positions...
        if hasattr(trade_manager, 'get_open_positions'):
            for pos in trade_manager.get_open_positions():
                ticket = getattr(pos, 'ticket', '?')
                side = 'BUY' if getattr(pos, 'type', None) == mt5.ORDER_TYPE_BUY else 'SELL'
                if (side == 'SELL' and display_action == 'SELL') or (side == 'BUY' and display_action == 'BUY'):
                    display_action = f"GIỮ LỆNH {side} (#{ticket})"
                    break

        msg_pred = (
            f"🎯 KẾT QUẢ PIPELINE V6:\\n"'''

content = content.replace(old_msg, new_msg)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
