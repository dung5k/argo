@echo off
cd /d "%~dp0"
title V8 LIVE BOT - OPT-6_ROBUST
color 0A

echo ===================================================
echo   KHOI DONG HE THONG GIAO DICH V8 LIVE (TRANSFORMER)
echo   Model: best_model_ARGO3_OPT-6.pt
echo   Author: Antigravity AI
echo ===================================================
echo.

python src/bot_v8/bot_v8.py

pause
