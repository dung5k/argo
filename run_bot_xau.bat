@echo off
chcp 65001 >nul
title [TRADE] XAUUSD Bot
echo Khoi dong Bot Trade XAUUSD...
.\venv\Scripts\python.exe src\trade_mt5.py data\bot_config_xau.json
pause
