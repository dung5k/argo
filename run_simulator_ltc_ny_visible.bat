@echo off
cd /d "%~dp0"
python scripts\simulate_ltc.py --session ny --start 2026-05-01 --end 2026-05-30 --notify
pause
