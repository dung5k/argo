@echo off
set PYTHONIOENCODING=utf8
set CONFIG_PATH=workspaces\CFG_LTC_LONDON_V3_5\runs\run_20260429_083500_v4_ldn_auto_1\config.json
set RUN_ID=run_20260429_083500_v4_ldn_auto_1

echo [1/3] CRAWLING DATA...
python scripts\crawl_crypto_v3.py %CONFIG_PATH%
if %errorlevel% neq 0 (
    echo Crawl failed!
    python .agent\send_to_tele.py "Lỗi Crawler LTC London. Cần check lại Rate Limit Binance!"
    exit /b %errorlevel%
)

echo [2/3] UPLOADING DATASETS...
python scripts\upload_v3_dataset.py --config %CONFIG_PATH% --no-push
if %errorlevel% neq 0 (
    echo Dataset generation failed!
    python .agent\send_to_tele.py "Lỗi Tensor LTC London!"
    exit /b %errorlevel%
)

echo [3/3] RUNNING BASE TRAINING...
python src\training_v3\train_v3.py --config %CONFIG_PATH% --session london --scratch --run-id %RUN_ID%
if %errorlevel% neq 0 (
    echo Training failed!
    python .agent\send_to_tele.py "Lỗi Training LTC London!"
    exit /b %errorlevel%
)

python .agent\notify_done.py ltc_london_training_done
python .agent\send_to_tele.py "Đã hoàn thành lượt Training Auto-Tuning ngầm cho LTC London (Run 1, Tăng Window_Size=30)! Hệ thống tiếp tục vào trạng thái chờ lượt tiếp theo." --done
echo PIPELINE COMPLETED SUCCESSFULLY!
