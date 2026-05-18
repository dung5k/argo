@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "D:\DungLA\client1"

echo "Building dataset..."
"C:\argo\venv\Scripts\python.exe" scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_LONDON_V6/runs/run_20260518_101000_v6_LONDON_TripleAsset_Seed123/config.json --no-upload --weekly-split

echo "Training model..."
"C:\argo\venv\Scripts\python.exe" src/training_v6/train_v6.py workspaces/CFG_LTC_LONDON_V6/runs/run_20260518_101000_v6_LONDON_TripleAsset_Seed123/config.json

echo "Notifying completion..."
"C:\argo\venv\Scripts\python.exe" .agent/notify_done.py ltc_v6_training_done
