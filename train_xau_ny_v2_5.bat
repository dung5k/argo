@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title [TRAIN] XAU NY V2.5 AI

echo ==========================================================
echo   TRAINING PIPELINE: XAU NY V2.5 (Config V2)
echo ==========================================================
echo.

echo 1. Thu thap data (Sync Historical)...
.\venv\Scripts\python.exe src\core\sync_historical_data.py data\bot_config_xau_ny_v2.json
echo.

echo 2. Xu ly ki thuat (Feature Engineering)...
.\venv\Scripts\python.exe src\core\feature_engineering.py data\bot_config_xau_ny_v2.json
echo.

echo 3. Bat dau Dao tao (Training)...
.\venv\Scripts\python.exe src\core\train_unified.py data\bot_config_xau_ny_v2.json
pause
