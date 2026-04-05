@echo off
chcp 65001 >nul
title [TRAIN] LTCUSDm AI
echo 1. Thu thap data (Crawl)...
.\venv\Scripts\python.exe src\core\crawl_mt5_alt.py
echo.
echo 2. Xu ly ki thuat (Feature Engineering)...
.\venv\Scripts\python.exe src\core\feature_engineering.py data\bot_config_ltc.json
echo.
echo 3. Bat dau Dao tao (Training)...
.\venv\Scripts\python.exe src\core\train_unified.py data\bot_config_ltc.json
pause
