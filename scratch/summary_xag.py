import os, json, glob

def get_best_run(workspace):
    runs_dir = os.path.join("workspaces", workspace, "runs")
    if not os.path.exists(runs_dir):
        return None
        
    best_score = -1.0
    best_run = None
    best_metrics = None
    
    for run_dir in glob.glob(os.path.join(runs_dir, "run_*")):
        metrics_file = os.path.join(run_dir, "results", "training_metrics_v3.json")
        if not os.path.exists(metrics_file):
            continue
            
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Find the session name (usually 'asian', 'ldn', or 'ny')
            sessions = data.get("sessions", {})
            for session_name, session_data in sessions.items():
                if "BEST_VLOSS" in session_data:
                    score = session_data["BEST_VLOSS"].get("composite_score", 0.0)
                    if score > best_score:
                        best_score = score
                        best_run = os.path.basename(run_dir)
                        best_metrics = session_data["BEST_VLOSS"]
        except Exception as e:
            pass
            
    return {"run": best_run, "score": best_score, "metrics": best_metrics}

asian = get_best_run("CFG_XAG_ASIAN_V3_5")
ldn = get_best_run("CFG_XAG_LDN_V3_5")
ny = get_best_run("CFG_XAG_NY_V3_5")

def format_metrics(session_name, data):
    if not data or not data['run']:
        return f"### {session_name}\n- Chưa có dữ liệu training hoàn chỉnh.\n"
        
    metrics = data['metrics']
    comp_score = metrics.get('composite_score', 0)
    
    # Tìm Max Win Rate và Win Rate tại mốc có N >= 30
    best_wr_n30 = 0
    best_n30 = 0
    max_wr = 0
    max_wr_n = 0
    
    for m in metrics.get('threshold_metrics', []):
        wr = m.get('win_rate', 0)
        n = m.get('total_signals', 0)
        
        if wr > max_wr:
            max_wr = wr
            max_wr_n = n
            
        if n >= 30 and wr > best_wr_n30:
            best_wr_n30 = wr
            best_n30 = n
            
    res = f"### {session_name} (Run: {data['run']})\n"
    res += f"- **Composite Score**: {comp_score:.3f}\n"
    if best_n30 > 0:
        res += f"- **Win Rate Tối Ưu (N>=30)**: {best_wr_n30*100:.1f}% (Số lệnh: {best_n30})\n"
    res += f"- **Max Win Rate**: {max_wr*100:.1f}% (Số lệnh: {max_wr_n})\n"
    return res

print(format_metrics("🔴 PHIÊN ASIAN (XAG)", asian))
print(format_metrics("🟢 PHIÊN LONDON (XAG)", ldn))
print(format_metrics("🔵 PHIÊN NEW YORK (XAG)", ny))

