import os, shutil
os.makedirs('C:/argo/data', exist_ok=True)
for f in os.listdir('data'):
    if f.endswith('.json'):
        shutil.copy(os.path.join('data', f), os.path.join('C:/argo/data', f))
print('OK')
