@echo off
title MOE TERMINATOR V2 - XAUUSD
cd /d "%~dp0"
echo ========================================================
echo Khoi dong Trade Bot V2 (OOP) - Cau hinh XAUUSD
echo Moi truong: venv
echo Target Script: src\bot_v2\bot_v2.py
echo ========================================================
echo.
echo Dang don dep cac Bot cu...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'bot_v2.py' } | Invoke-CimMethod -MethodName Terminate" >nul 2>&1
echo ========================================================
echo.

venv\Scripts\python.exe src\bot_v2\bot_v2.py data\bot_config_xau_london_v2.json

echo.
echo ========================================================
echo Tien trinh Bot da ket thuc hoac xay ra loi.
pause
