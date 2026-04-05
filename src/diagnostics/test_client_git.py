import subprocess

print("Check git status on client:")
try:
    r = subprocess.run(["git", "status"], capture_output=True, text=True)
    print(r.stdout)
    
    print("Testing git push:")
    r2 = subprocess.run(["git", "push"], capture_output=True, text=True)
    print(f"returncode: {r2.returncode}")
    print(f"stdout: {r2.stdout}")
    print(f"stderr: {r2.stderr}")
except Exception as e:
    print(f"Lỗi: {e}")
