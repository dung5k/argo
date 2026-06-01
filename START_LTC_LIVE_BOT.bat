@echo off
cd /d "%~dp0"
title LTC_LIVE_BOT_V6
set PYTHONPATH=%~dp0huyen_thoai;%PYTHONPATH%
python -u src/bot_v6/bot_v6.py bot_config_v6_ltc.json bot_schedule_v6_ltc.json
pause
