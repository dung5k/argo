@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set CUDA_VISIBLE_DEVICES=-1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1

echo "Training..."
python src/training_v3/train_v3.py workspaces/CFG_XAG_LONDON_V5/runs/run_20260527_053500_v5_london_entropy_seeker/config.json --scratch > workspaces/CFG_XAG_LONDON_V5/runs/run_20260527_053500_v5_london_entropy_seeker/train_v3.log 2>&1

echo "Notifying done..."
python .agent/notify_done.py "xag_v5_training_done" "workspaces/CFG_XAG_LONDON_V5/runs/run_20260527_053500_v5_london_entropy_seeker/config.json"
