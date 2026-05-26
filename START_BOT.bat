@echo off
cd /d "%~dp0"
python -u src/bot_v6/bot_v6.py bot_config_v6_ltc.json bot_schedule_v6_ltc.json
pause
