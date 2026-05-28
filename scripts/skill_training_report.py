# -*- coding: utf-8 -*-
"""
Prompt Skill: Bao cao thanh tich dao tao toan he thong
Quet toan bo workspaces va trich xuat TOP 3 bo nao tot nhat cho moi phien,
sau do gui bao cao qua Telegram.

Su dung: python .agent/skill_training_report.py [--channel <id>]
"""
import os, json, glob, sys, subprocess
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def scan_workspace(workspace_dir):
    """Quet toan bo runs trong workspace, tra ve danh sach ket qua."""
    results = []
    runs_dir = os.path.join(workspace_dir, "runs")
    if not os.path.exists(runs_dir):
        return results
    
    for run_dir in glob.glob(os.path.join(runs_dir, "run_*")):
        metrics_path = os.path.join(run_dir, "results", "training_metrics_v3.json")
        if not os.path.exists(metrics_path):
            continue
        run_name = os.path.basename(run_dir)
        try:
            with open(metrics_path, 'r', encoding='utf-8') as f:
                m = json.load(f)
        except:
            continue
        
        # Tim session key (asian, london, ny, weekend)
        sessions = m.get("sessions", {})
        for session_key, session_data in sessions.items():
            best = session_data.get("BEST_VLOSS", {})
            if not best:
                continue
            epoch = best.get("epoch", 0)
            score = best.get("composite_score", 0)
            win_rates = best.get("win_rates", [])
            thresholds = best.get("thresholds", [])
            totals = best.get("totals", [])
            
            # Lay WR cao nhat
            wr_high = max(win_rates) * 100 if win_rates else 0
            wr_high_idx = win_rates.index(max(win_rates)) if win_rates else 0
            thr_high = thresholds[wr_high_idx] if thresholds and wr_high_idx < len(thresholds) else 0
            signals_high = totals[wr_high_idx] if totals and wr_high_idx < len(totals) else 0
            
            # Extract timestamp
            parts = run_name.split("_")
            try:
                dt = datetime.strptime(f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S")
                time_str = dt.strftime("%d/%m %H:%M")
            except:
                time_str = "N/A"
            
            results.append({
                "run_name": run_name,
                "time": time_str,
                "epoch": epoch,
                "score": score,
                "wr_high": wr_high,
                "thr_high": thr_high,
                "signals": signals_high,
            })
    
    # Sort by WR descending
    results.sort(key=lambda x: x["wr_high"], reverse=True)
    return results

def format_session_report(session_name, session_emoji, results, sniper_threshold=80):
    """Format bao cao cho 1 phien."""
    lines = []
    sep = "━" * 27
    lines.append(f"{sep}")
    lines.append(f"{session_emoji} {session_name}")
    lines.append(f"{sep}")
    
    if not results:
        lines.append("   (Chua co du lieu dao tao)")
        return "\n".join(lines)
    
    # TOP 3
    medals = ["🥇 BEST", "🥈 #2", "🥉 #3"]
    for i, r in enumerate(results[:3]):
        medal = medals[i]
        lines.append(f"{medal}: {r['run_name']}")
        lines.append(f"   ├─ Win Rate : {r['wr_high']:.1f}%{'  ⭐' if r['wr_high'] >= 90 else ''}")
        lines.append(f"   └─ Score    : {r['score']:.4f}{'  ⭐' if r['score'] >= 0.8 else ''}")
    
    # Sniper club (>= threshold)
    snipers = [r for r in results if r["wr_high"] >= sniper_threshold]
    if len(snipers) > 3:
        lines.append(f"")
        lines.append(f"🏅 Cac run >= {sniper_threshold}% WR (Sniper Club): {len(snipers)} runs")
    
    # Status
    if results[0]["wr_high"] >= sniper_threshold:
        lines.append(f"✅ Da dat nguong Sniper >= {sniper_threshold}% WR")
    else:
        lines.append(f"⚠️ Chua dat nguong Sniper >= {sniper_threshold}% WR")
    
    return "\n".join(lines)

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspaces_dir = os.path.join(base_dir, "workspaces")
    
    # Parse symbol from args first to filter workspaces
    target_symbol = None
    if "--symbol" in sys.argv:
        idx = sys.argv.index("--symbol")
        if idx + 1 < len(sys.argv):
            target_symbol = sys.argv[idx + 1].upper()

    # Dinh nghia cac workspace can quet
    all_workspace_configs = [
        # LTC V6
        {"dir": "CFG_LTC_ASIAN_V6", "name": "PHIEN CHAU A (LTC ASIAN V6)", "emoji": "🌏", "sniper": 60},
        {"dir": "CFG_LTC_LONDON_V6", "name": "PHIEN LONDON (LTC LONDON V6)", "emoji": "🇬🇧", "sniper": 60},
        {"dir": "CFG_LTC_NY_V6", "name": "PHIEN NEW YORK (LTC NY V6)", "emoji": "🇺🇸", "sniper": 60},
        {"dir": "CFG_LTC_WEEKEND_V6", "name": "PHIEN WEEKEND (LTC WEEKEND V6)", "emoji": "🏖️", "sniper": 60},
        # XAG V5
        {"dir": "CFG_XAG_ASIAN_V5", "name": "PHIEN CHAU A (XAG ASIAN V5)", "emoji": "🌏", "sniper": 80},
        {"dir": "CFG_XAG_LONDON_V5", "name": "PHIEN LONDON (XAG LONDON V5)", "emoji": "🇬🇧", "sniper": 80},
        {"dir": "CFG_XAG_NY_V5", "name": "PHIEN NEW YORK (XAG NY V5)", "emoji": "🇺🇸", "sniper": 80},
    ]

    workspace_configs = []
    for cfg in all_workspace_configs:
        if target_symbol:
            if f"_{target_symbol}_" in cfg["dir"]:
                workspace_configs.append(cfg)
        else:
            workspace_configs.append(cfg)

    today = datetime.now().strftime("%d/%m/%Y")
    report_title = f"🏆 BAO CAO THANH TICH DAO TAO TOAN HE THONG ({target_symbol}) — {today}" if target_symbol else f"🏆 BAO CAO THANH TICH DAO TAO TOAN HE THONG — {today}"
    report_lines = [report_title, ""]
    
    # Thu thap ket qua de lam bang so sanh
    summary_data = []
    
    for cfg in workspace_configs:
        ws_path = os.path.join(workspaces_dir, cfg["dir"])
        results = scan_workspace(ws_path)
        
        section = format_session_report(cfg["name"], cfg["emoji"], results, cfg["sniper"])
        report_lines.append(section)
        report_lines.append("")
        
        if results:
            summary_data.append({
                "name": cfg["name"].split("(")[1].rstrip(")") if "(" in cfg["name"] else cfg["name"],
                "best_wr": results[0]["wr_high"],
                "best_score": results[0]["score"],
                "total_runs": len(results),
                "sniper_runs": len([r for r in results if r["wr_high"] >= cfg["sniper"]]),
                "sniper_threshold": cfg["sniper"],
            })
    
    # Bang tong ket so sanh
    if summary_data:
        sep = "━" * 27
        report_lines.append(sep)
        report_lines.append("📊 TONG KET SO SANH TAT CA PHIEN")
        report_lines.append(sep)
        
        # Sort by best WR
        summary_data.sort(key=lambda x: x["best_wr"], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        
        header = f"{'Phien':<22} │ {'Best WR':>8} │ {'Best Score':>10} │ {'Runs':>5}"
        report_lines.append(header)
        for i, s in enumerate(summary_data):
            medal = medals[i] if i < 3 else "  "
            report_lines.append(f"{s['name']:<22} │ {s['best_wr']:>6.1f}% {medal} │ {s['best_score']:>9.4f} │ {s['total_runs']:>5}")
        
        report_lines.append("")
        report_lines.append("🏆 NHAN XET:")
        if summary_data:
            report_lines.append(f"• {summary_data[0]['name']} dang dan dau voi WR {summary_data[0]['best_wr']:.1f}%")
            sniper_total = sum(s["sniper_runs"] for s in summary_data)
            report_lines.append(f"• Tong so run dat nguong Sniper: {sniper_total}")
    
    report = "\n".join(report_lines)
    
    # --- GỌI GEMINI AI API ĐỂ PHÂN TÍCH CHIẾN LƯỢC ---
    try:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            # Fallback to config file just in case
            tg_cfg_path = os.path.join(base_dir, "tg_config.json")
            if os.path.exists(tg_cfg_path):
                with open(tg_cfg_path, "r", encoding="utf-8") as f:
                    tg_cfg = json.load(f)
                gemini_key = tg_cfg.get("gemini_api_key")
                
        if gemini_key:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            
            # Tham số linh động từ args
            prompt_template_path = os.path.join(base_dir, ".agent", "strategy_prompt.md")
            if "--prompt-file" in sys.argv:
                idx = sys.argv.index("--prompt-file")
                if idx + 1 < len(sys.argv):
                    prompt_template_path = sys.argv[idx + 1]
                    
            symbol = "LTC và XAG"
            if "--symbol" in sys.argv:
                idx = sys.argv.index("--symbol")
                if idx + 1 < len(sys.argv):
                    symbol = sys.argv[idx + 1]
                    
            if os.path.exists(prompt_template_path):
                with open(prompt_template_path, "r", encoding="utf-8") as pf:
                    prompt_template = pf.read()
            else:
                prompt_template = "Bạn là AI Điều Phối Toàn Cục V6 (Argo2). Dựa vào báo cáo hiệu suất đào tạo sau, hãy phân tích cực kỳ ngắn gọn (chỉ 2-3 câu) và đưa ra '🎯 QUYẾT ĐỊNH ĐÀO TẠO TIẾP THEO: [TÊN PHIÊN]' là nên tập trung đào tạo tiếp cho phiên nào ({sessions}) và vì sao. Đặc biệt chú ý tối ưu hóa cho mã {symbol}.\n\nBáo cáo:\n{report}"
            
            sessions = "Asian, London, hay NY"
            prompt_text = prompt_template.replace("{symbol}", symbol).replace("{sessions}", sessions).replace("{report}", report)
            
            import requests, time
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            
            max_retries = 5
            ai_text = None
            last_error = ""
            for attempt in range(max_retries):
                try:
                    res = requests.post(url, json=payload, timeout=90)
                    if res.status_code == 200:
                        ai_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        break
                    else:
                        last_error = f"HTTP {res.status_code}: {res.text}"
                except Exception as ex:
                    last_error = str(ex)
                
                if attempt < max_retries - 1:
                    wait_time = 3 * (attempt + 1)
                    print(f"[Retry] Gọi Gemini thất bại (lần {attempt+1}/{max_retries}). Thử lại sau {wait_time}s... Lỗi: {last_error}")
                    time.sleep(wait_time)
                    
            if ai_text:
                report += "\n\n🤖 Argo2 AI Phân Tích:\n" + ai_text
            else:
                report += f"\n\n[Lỗi API Gemini sau {max_retries} lần thử: {last_error}]"
    except Exception as e:
        report += f"\n\n[Lỗi kết nối Gemini: {e}]"
    
    # Gui qua Telegram
    channel = None
    if "--channel" in sys.argv:
        idx = sys.argv.index("--channel")
        if idx + 1 < len(sys.argv):
            channel = sys.argv[idx + 1]
    
    # Gui qua Telegram bang send_to_tele.py de ho tro headless server
    send_script = os.path.join(base_dir, ".agent", "send_to_tele.py")
    if os.path.exists(send_script):
        cmd = [sys.executable, send_script, report]
        if channel:
            cmd.extend(["--channel", str(channel)])
        try:
            subprocess.run(cmd, check=False)
            print("Bao cao da gui qua send_to_tele.py!")
            print(report)
        except Exception as e:
            print(f"Loi khi goi send_to_tele.py: {e}")
    else:
        print(report)

if __name__ == "__main__":
    main()
