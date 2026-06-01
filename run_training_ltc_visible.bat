@echo off
cd /d "%~dp0"
python autonomous_training_loop.py --symbol LTC --version v6
pause
