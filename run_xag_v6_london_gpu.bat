@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
set CUDA_VISIBLE_DEVICES=0
set FORCE_CPU=0
cd /d "D:\DungLA\Argo"
echo Starting XAG London V6 GPU Training (Scratch)...
"C:\argo\venv\Scripts\python.exe" -u src/training_v6/train_v6.py workspaces\CFG_XAG_LONDON_V6\runs\run_20260523_212500_v6_london_init\config.json --run-id run_20260523_212500_v6_london_init --scratch > train_v6_london.log 2>&1
echo Training finished with errorlevel %ERRORLEVEL%
pause
