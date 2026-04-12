@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title [HOST] Trigger Train XAU NY V2.5

echo ==========================================================
echo   HOST CONTROLLER: YEU CAU 'clientV2' TRAIN XAU NY V2.5
echo ==========================================================
echo.

.\venv\Scripts\python.exe src\orchestration\host_controller.py train -c clientV2 -s xau_ny_v2 --script src\core\train_unified.py --mode MAX --session ny -t 60
pause
