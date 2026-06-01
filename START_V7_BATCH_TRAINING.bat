@echo off
cd /d "%~dp0"
title QTS-V7 Production Batch Training Loop
echo ====================================================
echo   QTS-V7 PRODUCTION BATCH TRAINING RUNNER
echo ====================================================
echo.
python scripts/run_v7_batch_training.py --loops 10
pause
