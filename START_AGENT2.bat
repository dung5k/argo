@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title [TELEGRAM AGENT 2] Khoi Dong...

echo ============================================================
echo   ARGO SYSTEM - KHOI DONG TELEGRAM AGENT #2
echo ============================================================
echo.

:: =============================================================
:: CLIENT ID CO DINH CHO AGENT THU 2
:: File .client_id2 doc lap voi agent chinh (.client_id)
:: =============================================================
if exist ".client_id2" (
    set /p CLIENT_ID=<".client_id2"
    for /f "tokens=*" %%a in ("!CLIENT_ID!") do set CLIENT_ID=%%a
) else (
    echo Lan dau khoi chay Agent #2 tren may nay!
    set /p CLIENT_ID="Vui long nhap ten Client #2 (vd: clientGH2, clientLocal, ...): "
    echo !CLIENT_ID!>".client_id2"
    attrib +h ".client_id2"
)

title [!CLIENT_ID!] Telegram Agent #2

echo [OK] Client #2 hien tai: !CLIENT_ID!
echo [INFO] Agent nay chay doc lap voi Agent chinh (!CLIENT_ID! khac cua may)
echo.

:: =============================================================
:: TIM PYTHON (doc lai tu .python_path neu da co)
:: =============================================================
set PYTHON_EXE=
if exist ".python_path" (
    set /p PYTHON_EXE=<".python_path"
    for /f "tokens=*" %%a in ("!PYTHON_EXE!") do set PYTHON_EXE=%%a
    if exist "!PYTHON_EXE!\python.exe" set PYTHON_EXE=!PYTHON_EXE!\python.exe
    if exist "!PYTHON_EXE!" goto :found_python
)

python -c "import sys; print(sys.executable)" >"%TEMP%\py_path2.txt" 2>nul
if %errorlevel% equ 0 (
    set /p PYTHON_EXE=<"%TEMP%\py_path2.txt"
    goto :found_python
)

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
) do (
    if exist "%%~P" (
        set PYTHON_EXE=%%~P
        goto :found_python
    )
)

echo [LOI] Khong tim thay Python. Chay START_AGENT.bat truoc de cai dat.
pause
exit /b 1

:found_python
echo [OK] Python: !PYTHON_EXE!
echo.

:: =============================================================
:: CHON VENV DUNG CHUNG (C:\argo\venv) HOAC VENV LOCAL
:: =============================================================
set TARGET_VENV=venv
if exist "C:\argo\venv\Scripts\python.exe" (
    set TARGET_VENV=C:\argo\venv
    echo [INFO] Dung VENV chung: !TARGET_VENV!
)

if not exist "!TARGET_VENV!\Scripts\python.exe" (
    echo [LOI] Khong tim thay VENV tai !TARGET_VENV!
    echo       Hay chay START_AGENT.bat truoc de khoi tao moi truong.
    pause
    exit /b 1
)

echo [OK] VENV san sang.
echo.

:: =============================================================
:: GIT PULL (dong bo code)
:: =============================================================
if exist ".git" (
    git --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [GIT] Dang dong bo code moi nhat...
        git pull --rebase
    )
)
echo.

:: =============================================================
:: CHAY AGENT #2 VOI CLIENT-ID RIENG BIET
:: Bien ARGO_AGENT_INSTANCE=2 dung de debug nhanh neu can
:: =============================================================
if not exist "!CLIENT_ID!\logs" mkdir "!CLIENT_ID!\logs"
if not exist "!CLIENT_ID!\action_request" mkdir "!CLIENT_ID!\action_request"

:: =============================================================
:: BIEN MOI TRUONG ARGO
:: =============================================================
set ARGO_DATA_DIR=C:\argo\data
set ARGO_LOGS_DIR=C:\argo\logs
echo [INFO] ARGO_DATA_DIR = !ARGO_DATA_DIR!
echo.

:run_agent2
echo ============================================================
echo   [!CLIENT_ID!] AGENT #2 DANG KET NOI LEN SERVER ARGO...
echo   Ngrok se tu dong chon CONG TRONG (khac Agent chinh)
echo   De dung: Nhan Ctrl+C
echo ============================================================
echo.

set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
set ARGO_AGENT_INSTANCE=2
"!TARGET_VENV!\Scripts\python.exe" src\orchestration\client_tg_agent.py --client-id !CLIENT_ID! --base-dir "%cd%"

if !errorlevel! equ 69 (
    echo [AUTO-UPDATE] Dang tu dong khoi dong lai Agent #2 sau khi cap nhat...
    timeout /t 3 /nobreak >nul
    goto run_agent2
)

echo.
echo [INFO] Agent #2 da ngat ket noi.
pause
