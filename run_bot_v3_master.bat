@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

TITLE MOE TERMINATOR V3 [MASTER XAUUSD]

:: Chuyển đến thư mục gốc của project
cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG HE THONG AI GIAO DICH V3 (MASTER BOT)
echo ===================================================
echo.
echo Kiem tra moi truong Python (venv)...
if not exist "venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay 'venv\Scripts\python.exe'
    echo Vui long kiem tra lai duong dan hoac chay 'install_req.py'
    pause
    exit /b 1
)

echo.
echo Dang tiep nap Bo Nao V3 - Master Scheduler...
echo.

venv\Scripts\python.exe src\bot_v3\bot_v3.py data\bot_config_xau_ny_v3_5.json data\bot_v3_brain_schedule.json

pause
