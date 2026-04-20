@echo off
set PYTHONUTF8=1
echo ========================================================
echo        AAMT BINANCE CRYPTO TERMINATOR V3.5
echo ========================================================
echo.
echo [1] Kich hoat moi truong Python...
call venv\Scripts\activate.bat

echo [2] Khoi dong Bot Binance V3.5...
python src\bot_v3_crypto.py data\bot_config_ltc_crypto_v3_5.json data\bot_v3_brain_schedule.json

pause
