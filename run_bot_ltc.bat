@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

TITLE MOE TERMINATOR V3 [LTCUSD - 24H]

cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG BOT LTC V3.5 (ASIAN + LONDON + NY)
echo ===================================================
echo.

C:\argo\venv\Scripts\python.exe -u src\bot_v3\bot_v3.py bot_config_ltc.json bot_schedule_ltc.json

pause
