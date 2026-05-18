@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "D:\DungLA\client1"

echo "Training model..."
"C:\argo\venv\Scripts\python.exe" src/training_v6/train_v6.py workspaces/CFG_LTC_LONDON_V6/runs/run_20260518_103900_v6_LONDON_TripleAsset_MicroBatch/config.json

echo "Notifying completion..."
"C:\argo\venv\Scripts\python.exe" .agent/notify_done.py ltc_v6_training_done
