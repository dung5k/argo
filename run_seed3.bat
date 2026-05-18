@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src/training_v6/train_v6.py workspaces\CFG_LTC_NY_V6\runs\run_20260515_235438_v6_NY_15m_BTC1H_Drop10_003\config.json --run-id run_20260515_235438_v6_NY_15m_BTC1H_Drop10_003 > train_v6_ny.log 2> train_v6_ny.err
