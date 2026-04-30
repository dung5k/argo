import subprocess
import sys
import os

CONFIG_PATH = r"workspaces\CFG_LTC_LONDON_V3_5\runs\run_20260501_032716_v4_ldn_auto_30\config.json"
RUN_ID = "run_20260501_032716_v4_ldn_auto_30"

def run_cmd(cmd, step_name):
    print(f"\n{'='*50}\n[STEP] {step_name}\n{'='*50}")
    result = subprocess.run(cmd, shell=True, env={**os.environ, "PYTHONIOENCODING": "utf8"})
    if result.returncode != 0:
        print(f"FAILED: {step_name}")
        msg = f"Lỗi {step_name} (LTC London). Vui lòng check logs hệ thống."
        subprocess.run(f'python .agent\\send_to_tele.py "{msg}"', shell=True)
        sys.exit(result.returncode)

run_cmd(f"python scripts\\crawl_crypto_v3.py {CONFIG_PATH}", "CRAWLING DATA")
run_cmd(f"python scripts\\upload_v3_dataset.py --config {CONFIG_PATH} --no-push", "UPLOADING DATASETS")
run_cmd(f"python src\\training_v3\\train_v3.py {CONFIG_PATH} --session london --scratch --run-id {RUN_ID}", "RUNNING BASE TRAINING")

subprocess.run("python .agent\\notify_done.py ltc_london_training_done", shell=True)
subprocess.run('python .agent\\send_to_tele.py "Đã hoàn thành lượt Training Auto-Tuning ngầm cho LTC London (Run 30: Trend Following R:R 2:1)! Hệ thống tiếp tục vào trạng thái chờ lượt tiếp theo." --done', shell=True, env={**os.environ, "PYTHONIOENCODING": "utf8"})
print("PIPELINE COMPLETED SUCCESSFULLY!")
