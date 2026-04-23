@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

TITLE MOE TERMINATOR V3 [LTC LONDON]

cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG BOT LTC LONDON V3.5
echo ===================================================
echo.

venv\Scripts\python.exe src\bot_v3\bot_v3.py data\bot_config_ltc_london_v3_5.json data\bot_ltc_london_schedule.json
pause
