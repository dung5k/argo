import os, json

base_dir = r'd:\DungLA\client1\workspaces'
sessions = [
    ('ASIAN V6',  'CFG_LTC_ASIAN_V6',  'run_20260515_161352_v6_ASIAN_5m_DeepMicro_213',  'asian'),
    ('LONDON V6', 'CFG_LTC_LONDON_V6', 'run_20260515_181119_v6_LONDON_15m_BTC_ETH_Drop15_113', 'london'),
    ('NY V6',     'CFG_LTC_NY_V6',     'run_20260516_142815_v6_NY_Cross5m_Win180_016',    'ny'),
]

for name, ws, run, sess_key in sessions:
    cfg_path = os.path.join(base_dir, ws, 'runs', run, 'config.json')
    tm_path  = os.path.join(base_dir, ws, 'runs', run, 'results', 'training_metrics_v3.json')
    tp, sl, wr, be = None, None, None, None
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding='utf-8', errors='replace') as f:
            cfg = json.load(f)
        tp = cfg.get('FEATURE_ENGINEERING', {}).get('TP_PCT')
        sl = cfg.get('FEATURE_ENGINEERING', {}).get('SL_PCT')
        if tp and sl:
            be = sl / (tp + sl)
    if os.path.exists(tm_path):
        with open(tm_path, encoding='utf-8', errors='replace') as f:
            tm = json.load(f)
        bv = tm.get('sessions', {}).get(sess_key, {}).get('BEST_VLOSS', {})
        wrs = bv.get('win_rates', [])
        wr = max(wrs) if wrs else None
    if wr and be:
        print(f'{name}: TP={tp*100:.1f}% SL={sl*100:.1f}% BE={be*100:.1f}% WR={wr*100:.2f}% Margin={((wr-be)*100):.2f}%')
    else:
        print(f'{name}: missing data tp={tp} sl={sl} wr={wr} be={be}')
