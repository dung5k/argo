import subprocess
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("Testing git sync on client...")
print("PULL:")
r1 = subprocess.run(["git", "pull", "--rebase"], cwd=base_dir, capture_output=True, text=True)
print(r1.stdout)
print(r1.stderr)

print("ADD:")
r2 = subprocess.run(["git", "add", "runs/"], cwd=base_dir, capture_output=True, text=True)
print(r2.stdout)
print(r2.stderr)

print("COMMIT:")
r3 = subprocess.run(["git", "commit", "-m", "Test auto commit from client"], cwd=base_dir, capture_output=True, text=True)
print(r3.stdout)
print(r3.stderr)

print("PUSH:")
r4 = subprocess.run(["git", "push"], cwd=base_dir, capture_output=True, text=True)
print(r4.stdout)
print(r4.stderr)
