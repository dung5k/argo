import os
import matplotlib.pyplot as plt
import matplotlib
# Use Agg to avoid Tkinter issues in headless modes
matplotlib.use('Agg')
from src.training_v2.evaluator_v2 import EpochEvalResult

def plot_and_notify_chart(
    eval_res: EpochEvalResult, 
    session_name: str, 
    cfg_name: str, 
    epoch: int,
    run_dir: str
):
    """
    Vẽ đồ thị WinRate và EV dựa trên ThresholdMetrics, lưu file PNG, 
    và in ra [CHART] <path> để Telegram Bot bắt và gửi tin.
    """
    if not eval_res.threshold_metrics:
        return
        
    thresholds = [m.threshold * 100 for m in eval_res.threshold_metrics]
    win_rates = [m.win_rate * 100 for m in eval_res.threshold_metrics]
    ev_scores = [m.ev_score * 10000 for m in eval_res.threshold_metrics] # In pips
    signals = [m.total_signals for m in eval_res.threshold_metrics]
    
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # X axis is Threshold
    color = 'tab:blue'
    ax1.set_xlabel('Model Output Threshold (%)', fontweight='bold')
    ax1.set_ylabel('Win Rate (%)', color=color, fontweight='bold')
    ax1.plot(thresholds, win_rates, color=color, marker='o', linewidth=2, label='Win Rate')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # 50% WinRate baseline
    ax1.axhline(50.0, color='blue', linestyle=':', alpha=0.5, label='50% WR')

    # EV axis
    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('Expected Value (Pips)', color=color, fontweight='bold')  
    ax2.plot(thresholds, ev_scores, color=color, marker='s', linewidth=2, label='EV (Pips)')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # 0 EV baseline
    ax2.axhline(0.0, color='red', linestyle=':', alpha=0.5, label='0 EV')

    # Title
    ep_str = f"Epoch {epoch}" if epoch >= 0 else "Epoch -1 (Kế thừa)"
    plt.title(f"[{session_name.upper()}] Phân tích Lợi nhuận ({cfg_name})\n{ep_str} | Max EV = {eval_res.best_ev*10000:.1f} pips | VLoss = {eval_res.val_loss:.4f}", pad=15)
    
    # Add number of signals as text annotation near points mapping WR
    for i, txt in enumerate(signals):
        ax1.annotate(f"N={txt}", (thresholds[i], win_rates[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)

    # Save
    chart_name = f"chart_{session_name}_{cfg_name}.png"
    chart_path = os.path.abspath(os.path.join(run_dir, chart_name))
    
    fig.tight_layout()
    plt.savefig(chart_path, dpi=120)
    plt.close(fig)
    
    # IMPORTANT: The magic string that client_tg_agent.py listens for
    print(f"\n[CHART] {chart_path}\n")

