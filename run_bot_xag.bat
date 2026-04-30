@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

TITLE MOE TERMINATOR V3 [XAGUSD - 24H]

cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG BOT XAG V3.5 (ASIAN + LONDON + NY)
echo ===================================================
echo.

C:\argo\venv\Scripts\python.exe -u src\bot_v3\bot_v3.py bot_config_xag.json bot_schedule_xag.json

pause
