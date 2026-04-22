@echo off
chcp 65001 >nul
title [TRAIN] USOILm AI
echo 1. Thu thap data (Crawl)...
.\venv\Scripts\python.exe src\crawl_mt5_alt.py
echo.
echo 2. Xu ly ki thuat (Feature Engineering)...
.\venv\Scripts\python.exe src\feature_engineering.py data\bot_config_oil.json
echo.
echo 3. Bat dau Dao tao (Training)...
.\venv\Scripts\python.exe src\train_unified.py data\bot_config_oil.json
pause
