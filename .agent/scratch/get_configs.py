import json
from huggingface_hub import HfFileSystem
with open('tg_config.json') as f:
    cfg = json.load(f)
fs = HfFileSystem(token=cfg.get('hf_token'))

targets = [
    'datasets/dung5k/argo_data/runs/run_20260414_170529_xauusd_CFG_XAU_LONDON_V2_1_TRANSFORMER_V2/training_metrix_v2.json',
    'datasets/dung5k/argo_data/runs/run_20260414_000528_xauusd_CFG_XAU_NY_V2_1_TRANSFORMER_V2/training_metrix_v2.json',
    'datasets/dung5k/argo_data/runs/run_20260414_131632_xauusd_CFG_XAU_ASIAN_V2_1_TRANSFORMER_V2/training_metrix_v2.json'
]

configs = {}
for t in targets:
    try:
        with fs.open(t, 'r') as fp:
            data = json.load(fp)
            run_name = t.split('/')[-2]
            for sid, sdata in data.get('sessions', {}).items():
                if not sdata: continue
                best = sdata.get('BEST_VLOSS', {})
                if not best: continue
                
                ths = best.get('thresholds', [])
                target_th = 0.54
                # We want a threshold where WR is > 54% and we have some trades (e.g. >10)
                for idx, th in enumerate(ths):
                    if best['win_rates'][idx] >= 54.0 and best['totals'][idx] >= 15:
                        target_th = th
                        break
                
                configs[f'xau_{sid}_v2_1'] = {
                    'hf_node': f"dung5k/argo_data/runs/{run_name}/net_{sid}_BEST_VLOSS.pth",
                    'th': round(target_th, 3)
                }
    except Exception as e:
        print('err', t, e)

print(json.dumps(configs, indent=2))
