@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src\training_v6\train_v6.py workspaces\CFG_LTC_NY_V6\runs\run_20260521_033013_v6_NY_MicroSniper\config.json --run-id run_20260521_033013_v6_NY_MicroSniper > workspaces\CFG_LTC_NY_V6\runs\run_20260521_033013_v6_NY_MicroSniper\train.log 2>&1
