@echo off
cd /d "%~dp0"
title V8 FULL TRAINING SEQUENCE
color 0E

echo ===================================================
echo   KHOI DONG TIEN TRINH HUAN LUYEN HOI TU TOAN BO DATSET
echo ===================================================
echo.

echo [1/3] Training OPT-1 (3 layers, M15) on full dataset...
python scripts/v8_train_full.py --model brain_OPT-1_S17_PnL+163.pt --epochs 5 --lr 1e-5 --batch_size 128
if %errorlevel% neq 0 (
    echo Error training OPT-1!
)
echo.

echo [2/3] Training OPT-217 (7 layers, M15) on full dataset...
python scripts/v8_train_full.py --model best_model_ARGO3_OPT-217.pt --epochs 5 --lr 1e-5 --batch_size 128
if %errorlevel% neq 0 (
    echo Error training OPT-217!
)
echo.

echo [3/3] Training OPT-V8C-8202 (6 layers, M5) on full dataset...
python scripts/v8_train_full.py --model brain_OPT-V8C-8202_S3_PnL+60_260611_0653.pt --epochs 5 --lr 1e-5 --batch_size 128
if %errorlevel% neq 0 (
    echo Error training OPT-V8C-8202!
)
echo.

echo ===================================================
echo   HOAN THANH TOAN BO TIEN TRINH HUAN LUYEN HOI TU!
echo ===================================================
pause
