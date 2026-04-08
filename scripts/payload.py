import os
import urllib.request
try:
    print('Downloading latest agent code from GitHub...')
    url = 'https://raw.githubusercontent.com/dung5k/forex_predictor/main/src/orchestration/client_tg_agent.py'
    data = urllib.request.urlopen(url).read().decode('utf-8')
    with open('src/orchestration/client_tg_agent.py', 'w', encoding='utf-8') as f:
        f.write(data)
    print('UPDATED CLIENT TG AGENT Bypassing GIT! Restarting...')
    os._exit(69)
except Exception as e:
    print('Error:', e)
