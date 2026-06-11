import os
import subprocess
import glob
import re

print("Running 2026 OOS Backtest on all Hall of Fame models...")
models = glob.glob("d:/DungLA/client1/v8_configs/hall_of_fame/*.pt")

results = []
for m in models:
    name = os.path.basename(m)
    res = subprocess.run(['python', 'scripts/v8_backtest.py', '--model', m, '--data', 'data/v8_test_2026.parquet'], capture_output=True, text=True)
    out = res.stdout
    
    pnl = re.search(r'Total PnL\s*:\s*([+\-]?[\d.]+)', out)
    pnl = float(pnl.group(1)) if pnl else -999.0
    
    pf = re.search(r'Profit Factor\s*:\s*([\d.]+)', out)
    pf = float(pf.group(1)) if pf else 0.0
    
    wr = re.search(r'Wins\s*:\s*\d+\s*\(([\d.]+)%\)', out)
    wr = float(wr.group(1)) if wr else 0.0
    
    dd = re.search(r'Max Drawdown\s*:\s*([\d.]+)', out)
    dd = float(dd.group(1)) if dd else 0.0
    
    trades = re.search(r'Total Trades\s*:\s*(\d+)', out)
    trades = int(trades.group(1)) if trades else 0
    
    results.append({
        'name': name,
        'pnl': pnl,
        'pf': pf,
        'wr': wr,
        'dd': dd,
        'trades': trades
    })

results.sort(key=lambda x: x['pnl'], reverse=True)

print(f"{'Model':<35} | {'PnL':>8} | {'PF':>5} | {'WR':>6} | {'DD':>6} | {'Trds':>4}")
print("-" * 75)
for r in results:
    print(f"{r['name']:<35} | {r['pnl']:+8.1f} | {r['pf']:5.2f} | {r['wr']:5.1f}% | {r['dd']:6.1f} | {r['trades']:4d}")

