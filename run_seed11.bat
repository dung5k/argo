@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src/training_v6/train_v6.py workspaces\CFG_LTC_NY_V6\runs\run_20260516_062548_v6_NY_Triple5m_Win180_011\config.json --run-id run_20260516_062548_v6_NY_Triple5m_Win180_011 > train_v6_ny_seed11.log 2> train_v6_ny_seed11.err
