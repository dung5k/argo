@echo off
title MOE TERMINATOR V2 - XAUUSD
cd /d "%~dp0"
echo ========================================================
echo Khá»Ÿi Ä‘á»™ng Trade Bot V2 (OOP) - Cáº¥u hÃ¬nh XAUUSD
echo MÃ´i trÆ°á»ng: venv
echo Target Script: src\bot_v2\bot_v2.py
echo ========================================================
echo.

venv\Scripts\python.exe src\bot_v2\bot_v2.py data\bot_config_xau_london_v2.json

echo.
echo ========================================================
echo Tiáº¿n trÃ¬nh Bot Ä‘Ã£ káº¿t thÃºc hoáº·c xáº£y ra lá»—i.
pause
