@echo off
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title QTS-V7 Production Batch Training Loop
echo ====================================================
echo   QTS-V7 PRODUCTION BATCH TRAINING RUNNER
echo ====================================================
echo.
python scripts/monitor_v7.py
timeout /t 5
