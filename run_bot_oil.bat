@echo off
chcp 65001 >nul
title [TRADE] USOILm Bot
echo Khoi dong Bot Trade Oil (USOILm)...
.\venv\Scripts\python.exe src\core\trade_mt5.py data\bot_config_oil.json
pause
