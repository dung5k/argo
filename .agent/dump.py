import os, glob
b = r'C:\argo\logs\runs'
runs = glob.glob(os.path.join(b, 'run_*'))
runs.sort(reverse=True)
for r in runs[:1]:
    log = os.path.join(r, 'train.log')
    if os.path.exists(log):
        with open(log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(''.join(lines[-30:]))
