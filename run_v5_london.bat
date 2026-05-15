@echo off
chcp 65001 > nul
python scripts/prepare_v6_dataset.py --config bot_config_v6_ltc_london.json
python src/training_v6/train_v6.py --scratch bot_config_v6_ltc_london.json
