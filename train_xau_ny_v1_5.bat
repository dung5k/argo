@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title [HOST] Trigger Train XAU NY V1.5

echo ==========================================================
echo   HOST CONTROLLER: YEU CAU 'clientGH' TRAIN XAU NY V1.5
echo ==========================================================
echo.

.\venv\Scripts\python.exe src\orchestration\host_controller.py train -c clientGH -s xau_ny_v1_5 --script src\core\train_unified.py --mode MAX --session ny -t 60
pause
