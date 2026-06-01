import glob
import os

for bat_file in glob.glob("*.bat"):
    try:
        with open(bat_file, "r") as f:
            content = f.read()
        new_content = content.replace("python ", "C:\\argo\\venv\\Scripts\\python.exe ")
        if new_content != content:
            with open(bat_file, "w") as f:
                f.write(new_content)
            print(f"Fixed {bat_file}")
    except Exception as e:
        print(f"Error {bat_file}: {e}")
