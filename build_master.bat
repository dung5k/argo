@echo off
REM build_master.bat - Build master.exe từ client_master.py bằng PyInstaller
REM Chạy trên máy HOST, sau đó copy master.exe sang client1/bin/

echo ============================================
echo  BUILD CLIENT MASTER EXE
echo ============================================

cd /d "%~dp0"

REM Kiểm tra PyInstaller
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller chua duoc cai. Dang cai...
    pip install pyinstaller
)

REM Build exe (--onefile = goi gon 1 file, --noconsole = an console window)
echo.
echo Building master.exe...
python -m PyInstaller ^
    --onefile ^
    --name master ^
    --console ^
    --clean ^
    --distpath "..\dist_master" ^
    --workpath "..\build_master" ^
    --specpath "..\build_master" ^
    src\orchestration\client_master.py

if errorlevel 1 (
    echo [ERROR] Build that bai!
    pause
    exit /b 1
)

echo.
echo [OK] Build thanh cong!
echo     Output: dist_master\master.exe

REM Copy vao client1/bin tu dong
if not exist "client1\bin" mkdir "client1\bin"
copy /Y "dist_master\master.exe" "client1\bin\master.exe"
echo [OK] Da copy -> client1\bin\master.exe

echo.
echo Huong dan:
echo   Chep client1\bin\master.exe sang may client1
echo   Chay: master.exe --client-id client1 --base-dir "C:\...\forex_predictor"
echo.
pause
