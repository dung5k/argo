import os

def patch_file(filepath, is_v6=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    start_str = 'def _load_brain_metrics'
    end_str = 'return "\\n".join(lines)\n    except Exception as e:' if is_v6 else 'return \'\\n\'.join(lines)\n    except Exception as e:'
    
    idx_start = content.find(start_str)
    idx_end = content.find('except Exception as e:', idx_start)
    
    if idx_start == -1 or idx_end == -1:
        print(f'Cannot find function in {filepath}')
        return
        
    new_func = f'''def _load_brain_metrics(run_id: str, config_id: str, is_active: bool = False){' -> tuple' if is_v6 else ' -> str'}:
    """Đọc training metrics từ local cache hoặc HF để tạo tooltip."""
    import glob as _glob
    import os, json
    base = os.path.join(safe_script_dir, 'workspaces', config_id, 'runs', run_id, 'results')
    metric_file = os.path.join(base, 'training_metrics_v3.json')
    
    status_icon = "🟢 ACTIVE" if is_active else "⚪ QUEUE"
    header = f"{{status_icon}} | 🧠 {{run_id}}"
    
    if not os.path.isfile(metric_file):
        cache_base = os.path.expanduser('~/.cache/huggingface/hub/datasets--dung5k--argo_workspaces')
        pattern = os.path.join(cache_base, '**', 'workspaces', config_id, 'runs', run_id, 'results', 'training_metrics_v3.json')
        found = _glob.glob(pattern, recursive=True)
        if found:
            metric_file = found[0]
        else:
            return f"{{header}}\\n📊 Không tìm thấy metrics"{', 0.7' if is_v6 else ''}
            
    try:
        with open(metric_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sessions = data.get('sessions', {{}})
        lines = [header]
        
        platform = CONFIG.get("LIVE_BOT", {{}}).get("TRADE_PLATFORM", "?")
        exec_sym = CONFIG.get("EXECUTION_SYMBOL", CONFIG.get("TARGET_SYMBOL", "?"))
        lines.append(f"💹 {{platform}} | {{exec_sym}}")
        lines.append("─" * 32)
        
        best_thr_overall = 0.7
        for sess_name, sess_data in sessions.items():
            best = sess_data.get('BEST_VLOSS', {{}})
            score = best.get('composite_score', 0)
            epoch = best.get('epoch', 0)
            lines.append(f"📅 PHIÊN: {{sess_name.upper()}}")
            lines.append(f"⭐ Score: {{score:.4f}} | Epoch: {{epoch}}")
            lines.append("─" * 15)
            
            best_wr, best_sigs = 0, 0
            for tm in best.get('threshold_metrics', []):
                thr = tm.get('threshold', 0)
                wr = tm.get('win_rate', 0)
                sigs = tm.get('total_signals', 0)
                tus = tm.get('tus_score', 0)
                b = tm.get('total_buy', sigs // 2)
                s = tm.get('total_sell', sigs - b)
                avg = sigs / 30.0 if sigs > 0 else 0
                lines.append(f"🎯 Thr: {{thr:.3f}} | WR: {{wr*100:.1f}}% ({{b}}B/{{s}}S)")
                lines.append(f"   Avg: {{avg:.1f}}/ngày | TUS: {{tus:.2f}}")
                
                if wr >= best_wr and sigs >= 1:
                    best_wr = wr
                    best_thr_overall = thr
            lines.append("─" * 15)
        
        report = "\\n".join(lines)
        return report{', best_thr_overall' if is_v6 else ''}
    '''
    
    new_content = content[:idx_start] + new_func + content[idx_end:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Patched {filepath}')

patch_file('src/bot_v3/bot_v3.py', is_v6=False)
patch_file('src/bot_v6/bot_v6.py', is_v6=True)
