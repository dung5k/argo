@echo off
chcp 65001 >nul
title [TRADE] LTCUSDm Bot
echo Khoi dong Bot Trade Crypto (LTCUSDm)...
.\venv\Scripts\python.exe src\core\trade_mt5.py data\bot_config_ltc.json
pause
