@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

TITLE AAMT MASTER V6 [LTCUSD - 24H]

cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG BOT LTC V6 (ASIAN + LONDON + NY)
echo ===================================================
echo.

C:\argo\venv\Scripts\python.exe -u src\bot_v6\bot_v6.py bot_config_v6_ltc.json bot_schedule_v6_ltc.json

pause
