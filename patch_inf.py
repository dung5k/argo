import os

filepath = r'd:\DungLA\client1\src\bot_v6\inference_engine_v6.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if 'import numpy as np' not in content:
    content = 'import numpy as np\n' + content

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
