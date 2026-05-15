import os
with open('setup_asian_v4.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '["python", "-u", "src/training_v6/train_v6.py", target_config, "--run-id", run_id]',
    '["python", "-u", "src/training_v6/train_v6.py", target_config, "--scratch", "--run-id", run_id]'
)

with open('setup_asian_v4.py', 'w', encoding='utf-8') as f:
    f.write(content)
