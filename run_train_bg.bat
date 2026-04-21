
@echo off
cd /d "D:\DungLA\Argo"
echo [BG] Starting NY Train...
"C:\argo\venv\Scripts\python.exe" src/training_v3/train_v3.py data/bot_config_xau_ny_v3_5.json
echo [BG] Finished NY Train. Starting London Train...
"C:\argo\venv\Scripts\python.exe" src/training_v3/train_v3.py data/bot_config_xau_london_v3_5.json
echo [BG] ALL DONE!
