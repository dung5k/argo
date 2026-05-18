@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src/training_v6/train_v6.py workspaces\CFG_LTC_NY_V6\runs\run_20260516_012403_v6_NY_15m_MultiResLTC_Drop10_005\config.json --run-id run_20260516_012403_v6_NY_15m_MultiResLTC_Drop10_005 > train_v6_ny_seed5.log 2> train_v6_ny_seed5.err
