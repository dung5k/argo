def calculate(n_correct, n_signals, n_buy, n_sell, min_N):
    win_rate = n_correct / n_signals if n_signals > 0 else 0.0
    balance_ratio = min(n_buy, n_sell) / max(1, max(n_buy, n_sell))
    balance_factor = 0.6 + 0.4 * balance_ratio
    
    if n_signals < min_N:
        freq_factor = n_signals / min_N
    elif n_signals > 250:
        freq_factor = 250 / n_signals
    else:
        freq_factor = 1.0
        
    score = win_rate * balance_factor * freq_factor
    return score, win_rate, balance_factor, freq_factor

print("Testing N=45, WR=0.8, Score=0.511")
n_signals = 45
n_correct = int(45 * 0.8) # 36
for n_buy in range(0, 46):
    n_sell = 45 - n_buy
    for min_N in range(10, 200):
        score, wr, bf, ff = calculate(n_correct, n_signals, n_buy, n_sell, min_N)
        if abs(score - 0.511) < 0.005:
            print(f"FOUND: n_buy={n_buy}, n_sell={n_sell}, min_N={min_N} -> score={score:.3f}, bf={bf:.3f}, ff={ff:.3f}")
