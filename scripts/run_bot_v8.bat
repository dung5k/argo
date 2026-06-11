@echo off
cd /d "%~dp0"
cd ..
echo ========================================
echo   V8 LIVE BOT - OPT-238 (M15)
echo   Circuit Breaker: ENABLED
echo ========================================
python src/bot_v8/bot_v8.py
pause
