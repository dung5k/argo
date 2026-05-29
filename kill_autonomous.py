import psutil
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = p.info['cmdline']
        if cmdline and ('autonomous_training_loop.py' in ' '.join(cmdline) or 'train_v6.py' in ' '.join(cmdline)):
            print(f"Killing {p.info['pid']}")
            p.kill()
    except Exception:
        pass
