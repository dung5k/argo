@echo off
cd /d "%~dp0"
C:\argo\venv\Scripts\python.exe -X utf8 autonomous_training_loop.py --symbol NEAR --version v6
pause
