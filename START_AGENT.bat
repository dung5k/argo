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
:: TIM PYTHON HOAC YEU CAU NHAP DUONG DAN
:: =============================================================
set PYTHON_EXE=
if exist ".python_path" (
    set /p PYTHON_EXE=<".python_path"
    for /f "tokens=*" %%a in ("!PYTHON_EXE!") do set PYTHON_EXE=%%a
    if exist "!PYTHON_EXE!\python.exe" set PYTHON_EXE=!PYTHON_EXE!\python.exe
    if exist "!PYTHON_EXE!" goto :found_python
)

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

:: Quet cac path pho bien
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Program Files\Python314\python.exe"
) do (
    if exist "%%~P" (
        set PYTHON_EXE=%%~P
        goto :found_python
    )
)

:prompt_python
echo [LOI] Khong tim thay Python tu dong tren may nay!
echo Vui long mo thu muc cai dat Python tren may, copy duong dan file python.exe
echo ^(Vi du: C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe^)
set /p MANUAL_PY="Nhap duong dan python.exe (hoac Enter de thoat): "
if "!MANUAL_PY!"=="" exit /b 1

:: Giup user neu ho chi nhap thu muc thay vi file python.exe
if exist "!MANUAL_PY!\python.exe" set MANUAL_PY=!MANUAL_PY!\python.exe

if not exist "!MANUAL_PY!" (
    echo [LOI] Duong dan khong hop le hoac khong ton tai file python.exe!
    goto :prompt_python
)
set PYTHON_EXE=!MANUAL_PY!
attrib -h ".python_path" >nul 2>&1
echo !PYTHON_EXE!>".python_path"
attrib +h ".python_path" >nul 2>&1

:found_python
attrib -h ".python_path" >nul 2>&1
echo !PYTHON_EXE!>".python_path"
attrib +h ".python_path" >nul 2>&1
echo [OK] Python phat hien: !PYTHON_EXE!
echo.

:: =============================================================
:: KIEM TRA GIT & CAP NHAT CODE (Chi khi chay tu repo cloned)
:: =============================================================
if exist ".git" (
    git --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [GIT] Dang dong bo code moi nhat tu ARGO...
        git pull --rebase
    ) else (
        echo [CANH BAO] Khong the chay git pull. Chua cai Git
    )
) else (
    echo [INFO] Dang chay che do thu muc thuong, khong phai git clone
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
if !errorlevel! neq 0 (
    "venv\Scripts\python.exe" -m pip install -q torch pandas numpy pyarrow scikit-learn paho-mqtt huggingface_hub
)
echo [OK] Thu vien san sang.
echo.

:: =============================================================
:: CHAY TRAM LANG NGHE TELEGRAM BOT LUU THONG TIN
:: =============================================================
if not exist "!CLIENT_ID!\logs" mkdir "!CLIENT_ID!\logs"
if not exist "!CLIENT_ID!\action_request" mkdir "!CLIENT_ID!\action_request"

:run_agent
echo ============================================================
echo   [!CLIENT_ID!] DANG KET NOI LEN SERVER ARGO...
echo   De dung hoat dong: Nhan Ctrl+C
echo ============================================================
echo.

set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
"venv\Scripts\python.exe" src\client_tg_agent.py --client-id !CLIENT_ID! --base-dir "%cd%"

if !errorlevel! equ 69 (
    echo [AUTO-UPDATE] He thong dang tu dong khoi dong lai Agent sau khi cap nhat...
    timeout /t 3 /nobreak >nul
    goto run_agent
)

echo.
echo [INFO] Ket noi da ngat.
pause
