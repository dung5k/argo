import traceback, sys
sys.path.insert(0, '.')
import builtins
import time

log_file = open("local_log_bot_v2.txt", "w", encoding="utf-8")

old_print = builtins.print
def safe_print(*args, **kwargs):
    old_print(*args, **kwargs)
    try:
        msg = " ".join(str(a) for a in args)
        log_file.write(msg + "\n")
        log_file.flush()
    except:
        pass

builtins.print = safe_print

try:
    from src.bot_v2.bot_v2 import bot_background_loop
    # Run the loop forever until it crashes
    bot_background_loop()
except Exception as e:
    err = traceback.format_exc()
    log_file.write("\n=== CRASH TRACEBACK ===\n")
    log_file.write(err)
    log_file.flush()
    old_print("\nCRASH FOUND! See local_log_bot_v2.txt")
