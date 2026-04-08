@echo off
setlocal

:: Cấu hình UTF-8 để hiển thị tiếng Việt trên Terminal
chcp 65001 >nul

echo ========================================================
echo KHOI DONG HIEU SUAT CAO: TRANSFORMER V1.5 MOE TRAINER
echo ========================================================

:: Bat dau tien trinh huan luyen
call venv\Scripts\activate
python src\training_v1_5\train_v1_5.py data\bot_config_xau_v1.json
pause
