@echo off
title MOE TERMINATOR V2 - XAUUSD
cd /d "%~dp0"
echo ========================================================
echo Khởi động Trade Bot V2 (OOP) - Cấu hình XAUUSD
echo Môi trường: venv
echo Target Script: src\bot_v2\bot_v2.py
echo ========================================================
echo.

venv\Scripts\python.exe src\bot_v2\bot_v2.py data\bot_config_xau.json

echo.
echo ========================================================
echo Tiến trình Bot đã kết thúc hoặc xảy ra lỗi.
pause
