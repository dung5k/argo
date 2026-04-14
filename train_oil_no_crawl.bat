@echo off
chcp 65001 >nul
title [TRAIN] USOILm AI (No Crawl)
echo 2. Xu ly ki thuat (Feature Engineering)...
python src\feature_engineering.py data\bot_config_oil.json
echo.
echo 3. Bat dau Dao tao (Training)...
python src\train_unified.py data\bot_config_oil.json
pause
