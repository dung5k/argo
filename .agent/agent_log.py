import os
import glob

# Check the telegram agent traceback if there's any
log_dir = r"C:\argo\logs\client1"
print("Files in", log_dir, ":", os.listdir(log_dir))

for f in glob.glob(os.path.join(log_dir, "*.log")):
    print("---", f, "---")
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as file:
            print(file.read()[-3000:])
    except Exception as e:
        print("Error reading:", e)
