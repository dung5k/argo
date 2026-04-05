@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title [TELEGRAM AGENT] Khoi Dong...

echo ============================================================
echo   ARGO SYSTEM - KHOI DONG TELEGRAM AGENT
echo ============================================================
echo.

:: =============================================================
:: DOC HOAC HOI TEN CLIENT (ID)
:: =============================================================
if exist ".client_id" (
    set /p CLIENT_ID=<".client_id"
    :: Xoa khoang trang du 
    for /f "tokens=*" %%a in ("!CLIENT_ID!") do set CLIENT_ID=%%a
) else (
    echo Lan dau khoi chay tren may nay!
    set /p CLIENT_ID="Vui long nhap ten Client (vd: clientGH, client1, clientCQ, ...): "
    echo !CLIENT_ID!>".client_id"
    attrib +h ".client_id"
)

title [!CLIENT_ID!] Telegram Agent

echo [OK] Client hien tai: !CLIENT_ID!
echo.

:: =============================================================
:: TIM PYTHON
:: =============================================================
set PYTHON_EXE=
python -c "import sys; print(sys.executable)" >"%TEMP%\py_path.txt" 2>nul
if %errorlevel% equ 0 (
    set /p PYTHON_EXE=<"%TEMP%\py_path.txt"
    goto :found_python
)
py -c "import sys; print(sys.executable)" >"%TEMP%\py_path.txt" 2>nul
if %errorlevel% equ 0 (
    set /p PYTHON_EXE=<"%TEMP%\py_path.txt"
    goto :found_python
)
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Program Files\Python314\python.exe"
) do (
    if exist %%P (
        set PYTHON_EXE=%%~P
        goto :found_python
    )
)
echo [LOI] Khong tim thay Python tren may nay! Vui long cai Python.
pause
exit /b 1

:found_python
echo [OK] Python phat hien: !PYTHON_EXE!
echo.

:: =============================================================
:: KIEM TRA GIT & CAP NHAT CODE (Chi khi chay tu repo cloned)
:: =============================================================
if exist ".git" (
    git --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo [GIT] Dang dong bo code moi nhat tu ARGO...
        git pull --rebase
    ) else (
        echo [CANH BAO] Khong the chay git pull (Chua cai Git).
    )
) else (
    echo [INFO] Dang chay che do thu muc (khong phai git clone).
)
echo.

:: =============================================================
:: TAO MOI TRUONG PYTHON (VENV)
:: =============================================================
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Moi truong VENV san sang.
        goto :install_deps
    ) else (
        echo [CANH BAO] Môi trường cu bi loi, dang xoa...
        rmdir /s /q venv
    )
)
echo [INFO] Dang cai dat moi truong (chi mat vai phut lan dau)...
"!PYTHON_EXE!" -m venv venv

:install_deps
echo [INFO] Dang cai dat cac thu vien can thiet...
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt 2>nul
if %errorlevel% neq 0 (
    "venv\Scripts\python.exe" -m pip install -q torch pandas numpy pyarrow scikit-learn
)
echo [OK] Thu vien san sang.
echo.

:: =============================================================
:: CHAY TRAM LANG NGHE TELEGRAM BOT LUU THONG TIN
:: =============================================================
if not exist "!CLIENT_ID!\logs" mkdir "!CLIENT_ID!\logs"
if not exist "!CLIENT_ID!\action_request" mkdir "!CLIENT_ID!\action_request"

echo ============================================================
echo   [!CLIENT_ID!] DANG KET NOI LEN SERVER ARGO...
echo   De dung hoat dong: Nhan Ctrl+C
echo ============================================================
echo.

set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
"venv\Scripts\python.exe" src\client_tg_agent.py --client-id !CLIENT_ID! --base-dir "%cd%"

echo.
echo [INFO] Ket noi da ngat.
pause
