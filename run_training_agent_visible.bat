@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

TITLE AUTONOMOUS TRAINING AGENT (V6)

cd /d "%~dp0"

echo ===================================================
echo   KHOI DONG AUTONOMOUS TRAINING LOOP (AI-DRIVEN)
echo ===================================================
echo.

:: Load env vars from registry in case schtasks didn't inherit them
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v TELEGRAM_BOT_TOKEN ^| findstr TELEGRAM_BOT_TOKEN') do set "TELEGRAM_BOT_TOKEN=%%b"
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v TELEGRAM_CHAT_ID ^| findstr TELEGRAM_CHAT_ID') do set "TELEGRAM_CHAT_ID=%%b"
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v GEMINI_API_KEY ^| findstr GEMINI_API_KEY') do set "GEMINI_API_KEY=%%b"
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v HF_TOKEN ^| findstr HF_TOKEN') do set "HF_TOKEN=%%b"

powershell -Command "C:\argo\venv\Scripts\python.exe -u autonomous_training_loop.py | Tee-Object -FilePath training_agent_console.log"
pause
