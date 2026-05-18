@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src/training_v6/train_v6.py workspaces\CFG_LTC_NY_V6\runs\run_20260516_142815_v6_NY_Cross5m_Win180_016\config.json --run-id run_20260516_142815_v6_NY_Cross5m_Win180_016 > train_v6_ny_seed16.log 2> train_v6_ny_seed16.err
