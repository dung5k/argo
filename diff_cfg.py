import json

def diff(p1, p2):
    try:
        c1 = json.load(open(p1, encoding='utf8'))
        c2 = json.load(open(p2, encoding='utf8'))
        
        def flatten(d, prefix=""):
            res = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    res.update(flatten(v, prefix + k + "."))
                else:
                    res[prefix + k] = v
            return res
            
        f1 = flatten(c1)
        f2 = flatten(c2)
        
        print("Diffing:")
        for k in f1:
            if k in f2 and f1[k] != f2[k]:
                print(f"{k}:\n  base: {f1[k]}\n  run74: {f2[k]}")
            elif k not in f2:
                print(f"{k} only in base")
        for k in f2:
            if k not in f1:
                print(f"{k} only in run74")
                
    except Exception as e:
        print(e)

diff('workspaces/CFG_LTC_LONDON_V3_5/base_config.json', 'workspaces/CFG_LTC_LONDON_V3_5/runs/run_20260428_024500_v4_ldn_74/config.json')
