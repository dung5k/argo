import os, pathlib
try:
    d = pathlib.Path(os.getcwd()) / 'client1' / 'logs'
    f = max(d.glob('tg_agent_*.log'), key=os.path.getctime)
    with open(f, 'r', encoding='utf-8') as fh:
        print('[LOG]\n' + ''.join(fh.readlines()[-30:]))
except Exception as e: print(e)
