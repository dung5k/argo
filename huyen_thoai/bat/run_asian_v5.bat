@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set CUDA_VISIBLE_DEVICES=-1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1

echo "Building dataset..."
python scripts/prepare_v3_dataset.py --config workspaces/CFG_XAG_ASIAN_V5/runs/run_20260527_070600_v5_asian_diverse_regularized/config.json --fast-hit-bars 5 --no-upload --monthly-split > workspaces/CFG_XAG_ASIAN_V5/runs/run_20260527_070600_v5_asian_diverse_regularized/prepare.log 2>&1

echo "Training..."
python src/training_v3/train_v3.py workspaces/CFG_XAG_ASIAN_V5/runs/run_20260527_070600_v5_asian_diverse_regularized/config.json --scratch > workspaces/CFG_XAG_ASIAN_V5/runs/run_20260527_070600_v5_asian_diverse_regularized/train_v3.log 2>&1

echo "Notifying done..."
python .agent/notify_done.py "xag_v5_training_done" "workspaces/CFG_XAG_ASIAN_V5/runs/run_20260527_070600_v5_asian_diverse_regularized/config.json"
