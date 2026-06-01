import subprocess
import sys
import os

def run_and_monitor():
    print("[MONITOR] Bat dau giam sat tien trinh V7 Batch Training...")
    
    # Xóa file crash cũ nếu có
    if os.path.exists("v7_crash.log"):
        os.remove("v7_crash.log")
        
    process = subprocess.Popen(
        [sys.executable, "-u", "scripts/run_v7_batch_training.py", "--loops", "10"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )
    
    log_file = open("v7_training_latest.log", "w", encoding="utf-8")
    
    crash_lines = []
    is_crashing = False
    
    try:
        for line in process.stdout:
            # Print to visible console
            sys.stdout.write(line)
            sys.stdout.flush()
            
            # Log to file
            log_file.write(line)
            log_file.flush()
            
            # Detect error
            if "Traceback (most recent call last):" in line or "[ERROR]" in line or "[FATAL]" in line or "Exception:" in line:
                is_crashing = True
                
            if is_crashing:
                crash_lines.append(line)
                
    except Exception as e:
        crash_lines.append(f"\n[MONITOR ERROR] Exception during reading stdout: {e}\n")
        
    process.wait()
    log_file.close()
    
    if process.returncode != 0 or len(crash_lines) > 0:
        print(f"\n[MONITOR] Phat hien crash! Ghi log ra v7_crash.log de AI Agent vao fix.")
        with open("v7_crash.log", "w", encoding="utf-8") as f:
            f.writelines(crash_lines[-50:]) # Luu 50 dong loi cuoi cung
            f.write(f"\n[MONITOR] Process exited with code {process.returncode}\n")

if __name__ == "__main__":
    run_and_monitor()
