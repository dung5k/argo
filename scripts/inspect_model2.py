import torch, glob, os, sys

runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
xau = sorted(glob.glob(os.path.join(runs_dir, '**', 'xauusd_unified_weights_BEST_VLOSS.pth'), recursive=True))
print('Found:', len(xau), file=sys.stderr)

if xau:
    st = torch.load(xau[-1], map_location='cpu', weights_only=True)
    for k,v in st.items():
        print(k, list(v.shape), file=sys.stderr)
