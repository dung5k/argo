import json
from huggingface_hub import list_repo_files, hf_hub_download

try:
    with open('tg_config.json') as f:
        tg = json.load(f)
        token = tg.get("hf_token")
        REPO_ID = tg.get("hf_repo_id", "dung5k/argo_data")
except:
    token = None
    REPO_ID = "dung5k/argo_data"

with open('tmp/hf_out3.txt', 'w', encoding='utf-8') as out_f:
    out_f.write(f"Repo: {REPO_ID}\n")
    try:
        all_files = list_repo_files(repo_id=REPO_ID, repo_type="dataset", token=token)
        # Find metrix files
        v2_files = [f for f in all_files if 'training_metrix_v2' in f]
        
        # Sort them basically to get latest
        v2_files.sort(reverse=True)
        
        found_data = False
        
        for filename in v2_files:
            try:
                path = hf_hub_download(repo_id=REPO_ID, repo_type='dataset', filename=filename, token=token)
                with open(path, 'r', encoding='utf-8') as fs:
                    data = json.load(fs)
                    
                    has_win_rate = False
                    output_cache = ""
                    
                    output_cache += f'\n========================================\n'
                    output_cache += f'=== FILE: {filename} ===\n'
                    output_cache += f'========================================\n'
                    
                    if 'top_configs_saved' in data:
                        for cfg in data['top_configs_saved']:
                            win_rates = cfg.get("win_rates", [])
                            if any(w > 0 for w in win_rates):
                                has_win_rate = True
                            output_cache += f' - Strategy: {cfg.get("strategy")}, Win rates: {[round(w, 2) for w in win_rates]}\n'
                    else:
                        for s_name, s_data in data.get('sessions', {}).items():
                            output_cache += f'\n[{s_name.upper()}]\n'
                            for key, val in s_data.items():
                                if 'L3' in key or 'L4' in key or 'L5' in key or 'TOP' in key:
                                    win_rates = val.get('win_rates', [])
                                    if any(w > 0 for w in win_rates):
                                        has_win_rate = True
                                    output_cache += f' - {key} | Win rates = {[round(w, 2) for w in win_rates]}\n'
                                    
                    if has_win_rate:
                        out_f.write(output_cache)
                        found_data = True
                        
            except Exception as e:
                pass
                
        if not found_data:
            out_f.write("Khong co file v2 nao co win rate ca.\n")
    except Exception as e:
        out_f.write(f"\nERROR: {e}\n")
