@echo off
setlocal
chcp 65001 >nul
title MASTER BOT AAMT (V2/V3 UNIFIED)
color 0b

echo ==============================================================
echo        AAMT FOREX PREDICTOR - MASTER UNIFIED BOT
echo        Tu dong nhan kich ban V2 hoac V3
echo ==============================================================

if "%~1"=="" (
    set ARGS=data\bot_config_xau_ny_v3_5.json
) else (
    set ARGS=%~1 %~2
)

echo Dang Load: %ARGS%
echo.

set PYTHONUTF8=1
call venv\Scripts\activate
python src\bot_master\bot_master.py %ARGS%

pause
