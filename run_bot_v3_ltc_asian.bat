@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

TITLE MOE TERMINATOR V3 [LTCUSD - ASIAN]

cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG BOT LTC ASIAN V3.5
echo ===================================================
echo.

venv\Scripts\python.exe -u src\bot_v3\bot_v3.py workspaces\CFG_LTC_ASIAN_V3_5\bot_config_ltc_asian_v3_5.json workspaces\CFG_LTC_CRYPTO_V3_5\empty_schedule.json

pause
