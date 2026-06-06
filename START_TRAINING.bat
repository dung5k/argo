@echo off
<<<<<<< Updated upstream
echo TASK DISABLED BY USER
exit /b 0
=======
cd /d "%~dp0"
python autonomous_training_loop.py --symbol LTC --version v6 > training_debug.log 2>&1
pause
>>>>>>> Stashed changes
