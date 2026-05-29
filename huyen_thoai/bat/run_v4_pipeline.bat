@echo off
set PYTHONIOENCODING=utf8

echo [1/3] CRAWLING DATA...
python scripts\crawl_crypto_v3.py workspaces\CFG_LTC_NY_V3_5\base_config.json
if %errorlevel% neq 0 (
    echo Crawl failed!
    python .agent\send_to_tele.py "Loi Crawler"
    exit /b %errorlevel%
)

echo [2/3] UPLOADING DATASETS...
python scripts\upload_v3_dataset.py --config workspaces\CFG_LTC_NY_V3_5\base_config.json --no-push
if %errorlevel% neq 0 (
    echo Dataset generation failed!
    python .agent\send_to_tele.py "Loi Tensor"
    exit /b %errorlevel%
)

echo [3/3] RUNNING BASE TRAINING...
python src\training_v3\train_v3.py workspaces\CFG_LTC_NY_V3_5\base_config.json --scratch
if %errorlevel% neq 0 (
    echo Training failed!
    python .agent\send_to_tele.py "Loi Training"
    exit /b %errorlevel%
)

python .agent\send_to_tele.py "Da chay xong Auto-Tuning V4 roi nhe sep!" --done
echo PIPELINE COMPLETED SUCCESSFULLY!
