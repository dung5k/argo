@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src/training_v6/train_v6.py workspaces\CFG_LTC_WEEKEND_V6\runs\run_20260516_081749_v6_WE_15m_Win60_Drop10_001\config.json --run-id run_20260516_081749_v6_WE_15m_Win60_Drop10_001 > train_v6_we_seed1.log 2> train_v6_we_seed1.err
