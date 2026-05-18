@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src/training_v6/train_v6.py workspaces\CFG_LTC_NY_V6\runs\run_20260516_005140_v6_NY_15m_BTC15m_Drop10_004\config.json --run-id run_20260516_005140_v6_NY_15m_BTC15m_Drop10_004 > train_v6_ny.log 2> train_v6_ny.err
