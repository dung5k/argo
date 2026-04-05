@echo off
chcp 65001 >nul
title [CLIENT 1] Telegram Agent
echo ========================================================
echo 🌐 KHOI DONG CLIENT 1 - TELEGRAM AGENT
echo ========================================================
echo.
echo Client se ket noi Telegram de lang nghe lenh tu Host.
echo.

:: Lùi ra thư mục gốc forex_predictor
cd ..

set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
.\venv\Scripts\python.exe src\client_tg_agent.py --client-id client1 --base-dir "%cd%"

pause
