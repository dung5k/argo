@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\argo\venv\Scripts\python.exe -u src\training_v6\train_v6.py workspaces\CFG_LTC_LONDON_V6\runs\run_20260521_043022_v6_LONDON_AsianAccumulation\config.json --run-id run_20260521_043022_v6_LONDON_AsianAccumulation > workspaces\CFG_LTC_LONDON_V6\runs\run_20260521_043022_v6_LONDON_AsianAccumulation\train.log 2>&1
