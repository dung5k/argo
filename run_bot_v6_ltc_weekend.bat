@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

TITLE MOE TERMINATOR V6 [LTCUSD - WEEKEND MTF]

cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG BOT LTC V6 MTF (WEEKEND)
echo ===================================================
echo.

C:\argo\venv\Scripts\python.exe -u src\bot_v6\bot_v6.py bot_config_v6_ltc_weekend.json

pause
