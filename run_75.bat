@echo off
set PYTHONIOENCODING=utf8
chcp 65001
echo Dang tao lai Tensor nho hon...
python scripts/upload_v3_dataset.py --config workspaces/CFG_LTC_LONDON_V3_5/runs/run_75_v5_phase1/config.json --no-push
echo Bat dau huan luyen Run 75...
python src/training_v3/train_v3.py workspaces/CFG_LTC_LONDON_V3_5/runs/run_75_v5_phase1/config.json --session london --scratch --run-id run_75_v5_phase1
python .agent/send_to_tele.py "🚀 Run 75 (LTC London V5) hoàn tất quá trình huấn luyện!" --done
