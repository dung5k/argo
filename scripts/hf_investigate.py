import json
from huggingface_hub import HfApi, hf_hub_download

api = HfApi(token='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')
files = api.list_repo_files('dung5k/argo_data', repo_type='dataset')
runs = sorted([f.split('/')[1] for f in files if f.startswith('runs/') and '_xauusd_' in f and 'training_metrix_v2.json' in f])

latest_run = runs[-1] if runs else None
print('Latest run:', latest_run)

if latest_run:
    path = hf_hub_download(repo_id='dung5k/argo_data', repo_type='dataset', filename=f'runs/{latest_run}/training_metrix_v2.json', token='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')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for session, info in data.get('sessions', {}).items():
            print(f'\n--- Session {session} ---')
            net_dict = info.get('top_networks', {})
            for name, net in net_dict.items():
                ev = net.get('ev_composite', -999)
                vloss = net.get('val_loss', 999)
                thrs = net.get('recommended_thresholds', {})
                print(f"  {name}: VLoss={vloss:.4f}, EV={ev}, Thresholds={thrs}")
