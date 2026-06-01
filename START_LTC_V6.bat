@echo off
cd /d "%~dp0"
C:\argo\venv\Scripts\python.exe autonomous_training_loop.py --symbol LTC --version v6
pause
