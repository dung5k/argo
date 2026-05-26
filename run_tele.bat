@echo off
title Lễ Tân Telegram - Antigravity IDE
color 0A

:LOOP
cls
echo.
echo ========================================================
echo   HE THONG LANG NGHE TELEGRAM CHO ANTIGRAVITY IDE
echo ========================================================
echo.
python tele_bridge\main.py

if errorlevel 99 (
    if not errorlevel 100 (
        echo.
        echo [SYSTEM] Dang khoi dong lai App Cau Noi theo yeu cau...
        timeout /t 2 >nul
        goto LOOP
    )
)

pause
