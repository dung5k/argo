import re

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. Thêm gui_target_text = ""
    if 'gui_target_text = ""' not in text:
        text = text.replace('gui_thr_text = ""', 'gui_thr_text = ""\ngui_target_text = "🎯 Sàn: Chờ kết nối..."')

    # 2. Sửa update_ui 
    if 'lbl_target=None' not in text:
        text = re.sub(
            r'def update_ui\(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr\):',
            'def update_ui(root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target=None):\n    if lbl_target: lbl_target.config(text=gui_target_text)',
            text
        )

    # 3. Sửa hàm gán update_ui. V1 và V2 có cú pháp có thể hơi khác.
    if 'root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target)' not in text:
        text = text.replace(
            'root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr)',
            'root.after(500, update_ui, root, lbl_time, lbl_session, lbl_pred, lbl_action, lbl_status, tree, lbl_thr, lbl_target)'
        )
    
    # 4. Thêm label vào GUI loop (V1 và V2 đều có lbl_session = tk.Label(root, text="🌍 Phiên:)
    if 'lbl_target = tk.Label(root, text="🎯 Sàn: Chờ kết nối..."' not in text:
        text = text.replace(
            'lbl_session = tk.Label(root, text="🌍 Phiên:',
            'lbl_target = tk.Label(root, text="🎯 Sàn: Chờ kết nối...", fg="#00ccff", bg="#121212", font=("Helvetica", 9, "bold"))\n    lbl_target.pack(pady=1)\n    lbl_session = tk.Label(root, text="🌍 Phiên:'
        )

    # 5. Extract actual target path in bot_background_loop
    if 'global gui_target_text' not in text:
        pattern = r"actual_target_sym = ([^\n]+)\n\s*target_path = ([^\n]+)"
        rep = r"actual_target_sym = \1\n        target_path = \2\n        global gui_target_text\n        gui_target_text = f'🎯 Cặp: {actual_target_sym} | Sàn: {str(target_path).split(chr(92))[-2] if target_path else \"Local\"}'"
        text = re.sub(pattern, rep, text)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'Patched {filepath}')

import os
if os.path.exists('src/core/trade_mt5.py'): patch_file('src/core/trade_mt5.py')
if os.path.exists('src/bot_v2/bot_v2.py'): patch_file('src/bot_v2/bot_v2.py')
