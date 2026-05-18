@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src/training_v6/train_v6.py workspaces\CFG_LTC_NY_V6\runs\run_20260516_065544_v6_NY_Cross5m_Win120_012\config.json --run-id run_20260516_065544_v6_NY_Cross5m_Win120_012 > train_v6_ny_seed12.log 2> train_v6_ny_seed12.err
