
import os
import sys

print('[VERIFY] Bắt đầu script kiểm tra')
p = 'C:/argo/data/CFG_XAU_LONDON_V2_1'
print('[VERIFY] Thư mục tồn tại:', os.path.exists(p))
if os.path.exists(p):
    print('[VERIFY] Files:', os.listdir(p))

import sys
sys.path.insert(0, 'src/orchestration')
try:
    import hf_sync
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test')
    class PrintLogger:
        def info(self, msg): print('[PULL INFO]', msg)
        def warning(self, msg): print('[PULL WARN]', msg)
        def error(self, msg): print('[PULL ERR]', msg)
    print('[VERIFY] Bắt đầu hf_sync.pull_data')
    cfg_p = 'C:/argo/data/bot_config_xau_london_v2_1.json'
    hf_sync.pull_data(PrintLogger(), config_path=cfg_p)
    print('[VERIFY] Kéo data thành công! Kiểm tra lại files:')
    if os.path.exists(p):
        print('[VERIFY] Files sau khi kéo:', os.listdir(p))
except Exception as e:
    print('[VERIFY] ERROR:', e)
