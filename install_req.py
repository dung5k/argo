import subprocess, sys, pathlib

base_dir = pathlib.Path(__file__).resolve().parent
venv_py = base_dir / 'venv' / 'Scripts' / 'python.exe'
py = str(venv_py) if venv_py.exists() else sys.executable

print(f"Installing requests using {py}...")
try:
    r = subprocess.run([py, "-m", "pip", "install", "requests"], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr: print(r.stderr)
except Exception as e:
    print(f"Error: {e}")
