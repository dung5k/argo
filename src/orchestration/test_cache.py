
import os
import sys

print('TEST CACHE SCRIPT RUNNING')
print('ARGO_DATA_DIR:', os.environ.get('ARGO_DATA_DIR'))
data_path = 'C:/argo/data/final_features_CFG_XAU_LONDON_V2_1.parquet'
print('Exists data_path:', os.path.exists(data_path))
if not os.path.exists(data_path):
    print('Listing C:/argo/data:')
    try:
        print(os.listdir('C:/argo/data'))
    except Exception as e:
        print('Error listing:', e)
    
    print('Let us manually pull using hf_sync:')
    import importlib.util
    sys.path.insert(0, str('src/orchestration'))
    import hf_sync
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test')
    hf_sync.pull_data(logger, None)
    print('After HF API, Exists data_path:', os.path.exists(data_path))
